"""An abstract base class for console-type widgets."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from functools import partial
import os
import os.path
import re
import sys
from textwrap import dedent
import time
from unicodedata import category
import webbrowser

from qtpy import QT6
from qtpy import QtCore, QtGui, QtPrintSupport, QtWidgets

from qtconsole.rich_text import HtmlExporter
from qtconsole.util import MetaQObjectHasTraits, get_font, superQ

from traitlets.config.configurable import LoggingConfigurable
from traitlets import Bool, Enum, Integer, Unicode

from .ansi_code_processor import QtAnsiCodeProcessor
from .completion_widget import CompletionWidget
from .completion_html import CompletionHtml
from .completion_plain import CompletionPlain
from .kill_ring import QtKillRing
from .util import columnize


def is_letter_or_number(char):
    """ Returns whether the specified unicode character is a letter or a number.
    """
    cat = category(char)
    return cat.startswith('L') or cat.startswith('N')

def is_whitespace(char):
    """Check whether a given char counts as white space."""
    return category(char).startswith('Z')

#-----------------------------------------------------------------------------
# Classes
#-----------------------------------------------------------------------------

class ConsoleWidget(MetaQObjectHasTraits('NewBase', (LoggingConfigurable, superQ(QtWidgets.QWidget)), {})):
    """ An abstract base class for console-type widgets. This class has
        functionality for:

            * Maintaining a prompt and editing region
            * Providing the traditional Unix-style console keyboard shortcuts
            * Performing tab completion
            * Paging text
            * Handling ANSI escape codes

        ConsoleWidget also provides a number of utility methods that will be
        convenient to implementors of a console-style widget.
    """

    #------ Configuration ------------------------------------------------------

    ansi_codes = Bool(True, config=True,
        help="Whether to process ANSI escape codes."
    )
    buffer_size = Integer(500, config=True,
        help="""
        The maximum number of lines of text before truncation. Specifying a
        non-positive number disables text truncation (not recommended).
        """
    )
    execute_on_complete_input = Bool(True, config=True,
        help="""Whether to automatically execute on syntactically complete input.

        If False, Shift-Enter is required to submit each execution.
        Disabling this is mainly useful for non-Python kernels,
        where the completion check would be wrong.
        """
    )
    gui_completion = Enum(['plain', 'droplist', 'ncurses'], config=True,
                    default_value = 'ncurses',
                    help="""
                    The type of completer to use. Valid values are:

                    'plain'   : Show the available completion as a text list
                                Below the editing area.
                    'droplist': Show the completion in a drop down list navigable
                                by the arrow keys, and from which you can select
                                completion by pressing Return.
                    'ncurses' : Show the completion as a text list which is navigable by
                                `tab` and arrow keys.
                    """
    )
    gui_completion_height = Integer(0, config=True,
        help="""
        Set Height for completion.

        'droplist'
            Height in pixels.
        'ncurses'
            Maximum number of rows.
        """
    )
    # NOTE: this value can only be specified during initialization.
    kind = Enum(['plain', 'rich'], default_value='plain', config=True,
        help="""
        The type of underlying text widget to use. Valid values are 'plain',
        which specifies a QPlainTextEdit, and 'rich', which specifies a
        QTextEdit.
        """
    )
    # NOTE: this value can only be specified during initialization.
    paging = Enum(['inside', 'hsplit', 'vsplit', 'custom', 'none'],
                  default_value='inside', config=True,
        help="""
        The type of paging to use. Valid values are:

        'inside'
           The widget pages like a traditional terminal.
        'hsplit'
           When paging is requested, the widget is split horizontally. The top
           pane contains the console, and the bottom pane contains the paged text.
        'vsplit'
           Similar to 'hsplit', except that a vertical splitter is used.
        'custom'
           No action is taken by the widget beyond emitting a
           'custom_page_requested(str)' signal.
        'none'
           The text is written directly to the console.
        """)

    scrollbar_visibility = Bool(True, config=True,
        help="""The visibility of the scrollar. If False then the scrollbar will be
        invisible."""
    )

    font_family = Unicode(config=True,
        help="""The font family to use for the console.
        On OSX this defaults to Monaco, on Windows the default is
        Consolas with fallback of Courier, and on other platforms
        the default is Monospace.
        """)
    def _font_family_default(self):
        if sys.platform == 'win32':
            # Consolas ships with Vista/Win7, fallback to Courier if needed
            return 'Consolas'
        elif sys.platform == 'darwin':
            # OSX always has Monaco, no need for a fallback
            return 'Monaco'
        else:
            # Monospace should always exist, no need for a fallback
            return 'Monospace'

    font_size = Integer(config=True,
        help="""The font size. If unconfigured, Qt will be entrusted
        with the size of the font.
        """)

    console_width = Integer(81, config=True,
        help="""The width of the console at start time in number
        of characters (will double with `hsplit` paging)
        """)

    console_height = Integer(25, config=True,
        help="""The height of the console at start time in number
        of characters (will double with `vsplit` paging)
        """)

    # Whether to override ShortcutEvents for the keybindings defined by this
    # widget (Ctrl+n, Ctrl+a, etc). Enable this if you want this widget to take
    # priority (when it has focus) over, e.g., window-level menu shortcuts.
    override_shortcuts = Bool(False)

    # ------ Custom Qt Widgets -------------------------------------------------

    # For other projects to easily override the Qt widgets used by the console
    # (e.g. Griffin)
    custom_control = None
    custom_page_control = None

    #------ Signals ------------------------------------------------------------

    # Signals that indicate ConsoleWidget state.
    copy_available = QtCore.Signal(bool)
    redo_available = QtCore.Signal(bool)
    undo_available = QtCore.Signal(bool)

    # Signal emitted when paging is needed and the paging style has been
    # specified as 'custom'.
    custom_page_requested = QtCore.Signal(object)

    # Signal emitted when the font is changed.
    font_changed = QtCore.Signal(QtGui.QFont)

    #------ Protected class variables ------------------------------------------

    # control handles
    _control = None
    _page_control = None
    _splitter = None

    # When the control key is down, these keys are mapped.
    _ctrl_down_remap = { QtCore.Qt.Key_B : QtCore.Qt.Key_Left,
                         QtCore.Qt.Key_F : QtCore.Qt.Key_Right,
                         QtCore.Qt.Key_A : QtCore.Qt.Key_Home,
                         QtCore.Qt.Key_P : QtCore.Qt.Key_Up,
                         QtCore.Qt.Key_N : QtCore.Qt.Key_Down,
                         QtCore.Qt.Key_H : QtCore.Qt.Key_Backspace, }
    if not sys.platform == 'darwin':
        # On OS X, Ctrl-E already does the right thing, whereas End moves the
        # cursor to the bottom of the buffer.
        _ctrl_down_remap[QtCore.Qt.Key_E] = QtCore.Qt.Key_End

    # The shortcuts defined by this widget. We need to keep track of these to
    # support 'override_shortcuts' above.
    _shortcuts = set(_ctrl_down_remap.keys()) | \
                     { QtCore.Qt.Key_C, QtCore.Qt.Key_G, QtCore.Qt.Key_O,
                       QtCore.Qt.Key_V }

    _temp_buffer_filled = False

    #---------------------------------------------------------------------------
    # 'QObject' interface
    #---------------------------------------------------------------------------

    def __init__(self, parent=None, **kw):
        """ Create a ConsoleWidget.

        Parameters
        ----------
        parent : QWidget, optional [default None]
            The parent for this widget.
        """
        super().__init__(**kw)
        if parent:
            self.setParent(parent)

        self._is_complete_msg_id = None
        self._is_complete_timeout = 0.1
        self._is_complete_max_time = None

        # While scrolling the pager on Mac OS X, it tears badly.  The
        # NativeGesture is platform and perhaps build-specific hence
        # we take adequate precautions here.
        self._pager_scroll_events = [QtCore.QEvent.Wheel]
        if hasattr(QtCore.QEvent, 'NativeGesture'):
            self._pager_scroll_events.append(QtCore.QEvent.NativeGesture)

        # Create the layout and underlying text widget.
        layout = QtWidgets.QStackedLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._control = self._create_control()
        if self.paging in ('hsplit', 'vsplit'):
            self._splitter = QtWidgets.QSplitter()
            if self.paging == 'hsplit':
                self._splitter.setOrientation(QtCore.Qt.Horizontal)
            else:
                self._splitter.setOrientation(QtCore.Qt.Vertical)
            self._splitter.addWidget(self._control)
            layout.addWidget(self._splitter)
        else:
            layout.addWidget(self._control)

        # Create the paging widget, if necessary.
        if self.paging in ('inside', 'hsplit', 'vsplit'):
            self._page_control = self._create_page_control()
            if self._splitter:
                self._page_control.hide()
                self._splitter.addWidget(self._page_control)
            else:
                layout.addWidget(self._page_control)

        # Initialize protected variables. Some variables contain useful state
        # information for subclasses; they should be considered read-only.
        self._append_before_prompt_cursor = self._control.textCursor()
        self._ansi_processor = QtAnsiCodeProcessor()
        if self.gui_completion == 'ncurses':
            self._completion_widget = CompletionHtml(self, self.gui_completion_height)
        elif self.gui_completion == 'droplist':
            self._completion_widget = CompletionWidget(self, self.gui_completion_height)
        elif self.gui_completion == 'plain':
            self._completion_widget = CompletionPlain(self)

        self._continuation_prompt = '> '
        self._continuation_prompt_html = None
        self._executing = False
        self._filter_resize = False
        self._html_exporter = HtmlExporter(self._control)
        self._input_buffer_executing = ''
        self._input_buffer_pending = ''
        self._kill_ring = QtKillRing(self._control)
        self._prompt = ''
        self._prompt_html = None
        self._prompt_cursor = self._control.textCursor()
        self._prompt_sep = ''
        self._reading = False
        self._reading_callback = None
        self._tab_width = 4

        # Cursor position of where to insert text.
        # Control characters allow this to move around on the current line.
        self._insert_text_cursor = self._control.textCursor()

        # List of strings pending to be appended as plain text in the widget.
        # The text is not immediately inserted when available to not
        # choke the Qt event loop with paint events for the widget in
        # case of lots of output from kernel.
        self._pending_insert_text = []

        # Timer to flush the pending stream messages. The interval is adjusted
        # later based on actual time taken for flushing a screen (buffer_size)
        # of output text.
        self._pending_text_flush_interval = QtCore.QTimer(self._control)
        self._pending_text_flush_interval.setInterval(100)
        self._pending_text_flush_interval.setSingleShot(True)
        self._pending_text_flush_interval.timeout.connect(
                                            self._on_flush_pending_stream_timer)

        # Set a monospaced font.
        self.reset_font()

        # Configure actions.
        action = QtWidgets.QAction('Print', None)
        action.setEnabled(True)
        printkey = QtGui.QKeySequence(QtGui.QKeySequence.Print)
        if printkey.matches("Ctrl+P") and sys.platform != 'darwin':
            # Only override the default if there is a collision.
            # Qt ctrl = cmd on OSX, so the match gets a false positive on OSX.
            printkey = "Ctrl+Shift+P"
        action.setShortcut(printkey)
        action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
        action.triggered.connect(self.print_)
        self.addAction(action)
        self.print_action = action

        action = QtWidgets.QAction('Save as HTML/XML', None)
        action.setShortcut(QtGui.QKeySequence.Save)
        action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
        action.triggered.connect(self.export_html)
        self.addAction(action)
        self.export_action = action

        action = QtWidgets.QAction('Select All', None)
        action.setEnabled(True)
        selectall = QtGui.QKeySequence(QtGui.QKeySequence.SelectAll)
        if selectall.matches("Ctrl+A") and sys.platform != 'darwin':
            # Only override the default if there is a collision.
            # Qt ctrl = cmd on OSX, so the match gets a false positive on OSX.
            selectall = "Ctrl+Shift+A"
        action.setShortcut(selectall)
        action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
        action.triggered.connect(self.select_all_smart)
        self.addAction(action)
        self.select_all_action = action

        self.increase_font_size = QtWidgets.QAction("Bigger Font",
                self,
                shortcut=QtGui.QKeySequence.ZoomIn,
                shortcutContext=QtCore.Qt.WidgetWithChildrenShortcut,
                statusTip="Increase the font size by one point",
                triggered=self._increase_font_size)
        self.addAction(self.increase_font_size)

        self.decrease_font_size = QtWidgets.QAction("Smaller Font",
                self,
                shortcut=QtGui.QKeySequence.ZoomOut,
                shortcutContext=QtCore.Qt.WidgetWithChildrenShortcut,
                statusTip="Decrease the font size by one point",
                triggered=self._decrease_font_size)
        self.addAction(self.decrease_font_size)

        self.reset_font_size = QtWidgets.QAction("Normal Font",
                self,
                shortcut="Ctrl+0",
                shortcutContext=QtCore.Qt.WidgetWithChildrenShortcut,
                statusTip="Restore the Normal font size",
                triggered=self.reset_font)
        self.addAction(self.reset_font_size)

        # Accept drag and drop events here. Drops were already turned off
        # in self._control when that widget was created.
        self.setAcceptDrops(True)

    #---------------------------------------------------------------------------
    # Drag and drop support
    #---------------------------------------------------------------------------

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            # The link action should indicate to that the drop will insert
            # the file anme.
            e.setDropAction(QtCore.Qt.LinkAction)
            e.accept()
        elif e.mimeData().hasText():
            # By changing the action to copy we don't need to worry about
            # the user accidentally moving text around in the widget.
            e.setDropAction(QtCore.Qt.CopyAction)
            e.accept()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            pass
        elif e.mimeData().hasText():
            cursor = self._control.cursorForPosition(e.pos())
            if self._in_buffer(cursor.position()):
                e.setDropAction(QtCore.Qt.CopyAction)
                self._control.setTextCursor(cursor)
            else:
                e.setDropAction(QtCore.Qt.IgnoreAction)
            e.accept()

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            self._keep_cursor_in_buffer()
            cursor = self._control.textCursor()
            filenames = [url.toLocalFile() for url in e.mimeData().urls()]
            text = ', '.join("'" + f.replace("'", "'\"'\"'") + "'"
                             for f in filenames)
            self._insert_plain_text_into_buffer(cursor, text)
        elif e.mimeData().hasText():
            cursor = self._control.cursorForPosition(e.pos())
            if self._in_buffer(cursor.position()):
                text = e.mimeData().text()
                self._insert_plain_text_into_buffer(cursor, text)

    def eventFilter(self, obj, event):
        """ Reimplemented to ensure a console-like behavior in the underlying
            text widgets.
        """
        etype = event.type()
        if etype == QtCore.QEvent.KeyPress:

            # Re-map keys for all filtered widgets.
            key = event.key()
            if self._control_key_down(event.modifiers()) and \
                    key in self._ctrl_down_remap:
                new_event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                            self._ctrl_down_remap[key],
                                            QtCore.Qt.NoModifier)
                QtWidgets.QApplication.instance().sendEvent(obj, new_event)
                return True

            elif obj == self._control:
                return self._event_filter_console_keypress(event)

            elif obj == self._page_control:
                return self._event_filter_page_keypress(event)

        # Make middle-click paste safe.
        elif getattr(event, 'button', False) and \
                etype == QtCore.QEvent.MouseButtonRelease and \
                event.button() == QtCore.Qt.MiddleButton and \
                obj == self._control.viewport():
            cursor = self._control.cursorForPosition(event.pos())
            self._control.setTextCursor(cursor)
            self.paste(QtGui.QClipboard.Selection)
            return True

        # Manually adjust the scrollbars *after* a resize event is dispatched.
        elif etype == QtCore.QEvent.Resize and not self._filter_resize:
            self._filter_resize = True
            QtWidgets.QApplication.instance().sendEvent(obj, event)
            self._adjust_scrollbars()
            self._filter_resize = False
            return True

        # Override shortcuts for all filtered widgets.
        elif etype == QtCore.QEvent.ShortcutOverride and \
                self.override_shortcuts and \
                self._control_key_down(event.modifiers()) and \
                event.key() in self._shortcuts:
            event.accept()

        # Handle scrolling of the vsplit pager. This hack attempts to solve
        # problems with tearing of the help text inside the pager window.  This
        # happens only on Mac OS X with both PySide and PyQt. This fix isn't
        # perfect but makes the pager more usable.
        elif etype in self._pager_scroll_events and \
                obj == self._page_control:
            self._page_control.repaint()
            return True

        elif etype == QtCore.QEvent.MouseMove:
            anchor = self._control.anchorAt(event.pos())
            if QT6:
                pos = event.globalPosition().toPoint()
            else:
                pos = event.globalPos()
            QtWidgets.QToolTip.showText(pos, anchor)

        return super().eventFilter(obj, event)

    #---------------------------------------------------------------------------
    # 'QWidget' interface
    #---------------------------------------------------------------------------

    def sizeHint(self):
        """ Reimplemented to suggest a size that is 80 characters wide and
            25 lines high.
        """
        font_metrics = QtGui.QFontMetrics(self.font)
        margin = (self._control.frameWidth() +
                  self._control.document().documentMargin()) * 2
        style = self.style()
        splitwidth = style.pixelMetric(QtWidgets.QStyle.PM_SplitterWidth)

        # Note 1: Despite my best efforts to take the various margins into
        # account, the width is still coming out a bit too small, so we include
        # a fudge factor of one character here.
        # Note 2: QFontMetrics.maxWidth is not used here or anywhere else due
        # to a Qt bug on certain Mac OS systems where it returns 0.
        width = self._get_font_width() * self.console_width + margin
        width += style.pixelMetric(QtWidgets.QStyle.PM_ScrollBarExtent)

        if self.paging == 'hsplit':
            width = width * 2 + splitwidth

        height = font_metrics.height() * self.console_height + margin
        if self.paging == 'vsplit':
            height = height * 2 + splitwidth

        return QtCore.QSize(int(width), int(height))

    #---------------------------------------------------------------------------
    # 'ConsoleWidget' public interface
    #---------------------------------------------------------------------------

    include_other_output = Bool(False, config=True,
        help="""Whether to include output from clients
        other than this one sharing the same kernel.

        Outputs are not displayed until enter is pressed.
        """
    )

    other_output_prefix = Unicode('[remote] ', config=True,
        help="""Prefix to add to outputs coming from clients other than this one.

        Only relevant if include_other_output is True.
        """
    )

    def can_copy(self):
        """ Returns whether text can be copied to the clipboard.
        """
        return self._control.textCursor().hasSelection()

    def can_cut(self):
        """ Returns whether text can be cut to the clipboard.
        """
        cursor = self._control.textCursor()
        return (cursor.hasSelection() and
                self._in_buffer(cursor.anchor()) and
                self._in_buffer(cursor.position()))

    def can_paste(self):
        """ Returns whether text can be pasted from the clipboard.
        """
        if self._control.textInteractionFlags() & QtCore.Qt.TextEditable:
            return bool(QtWidgets.QApplication.clipboard().text())
        return False

    def clear(self, keep_input=True):
        """ Clear the console.

        Parameters
        ----------
        keep_input : bool, optional (default True)
            If set, restores the old input buffer if a new prompt is written.
        """
        if self._executing:
            self._control.clear()
        else:
            if keep_input:
                input_buffer = self.input_buffer
            self._control.clear()
            self._show_prompt()
            if keep_input:
                self.input_buffer = input_buffer

    def copy(self):
        """ Copy the currently selected text to the clipboard.
        """
        self.layout().currentWidget().copy()

    def copy_anchor(self, anchor):
        """ Copy anchor text to the clipboard
        """
        QtWidgets.QApplication.clipboard().setText(anchor)

    def cut(self):
        """ Copy the currently selected text to the clipboard and delete it
            if it's inside the input buffer.
        """
        self.copy()
        if self.can_cut():
            self._control.textCursor().removeSelectedText()

    def _handle_is_complete_reply(self, msg):
        if msg['parent_header'].get('msg_id', 0) != self._is_complete_msg_id:
            return
        status = msg['content'].get('status', 'complete')
        indent = msg['content'].get('indent', '')
        self._trigger_is_complete_callback(status != 'incomplete', indent)

    def _trigger_is_complete_callback(self, complete=False, indent=''):
        if self._is_complete_msg_id is not None:
            self._is_complete_msg_id = None
            self._is_complete_callback(complete, indent)

    def _register_is_complete_callback(self, source, callback):
        if self._is_complete_msg_id is not None:
            if self._is_complete_max_time < time.time():
                # Second return while waiting for is_complete
                return
            else:
                # request timed out
                self._trigger_is_complete_callback()
        self._is_complete_max_time = time.time() + self._is_complete_timeout
        self._is_complete_callback = callback
        self._is_complete_msg_id = self.kernel_client.is_complete(source)

    def execute(self, source=None, hidden=False, interactive=False):
        """ Executes source or the input buffer, possibly prompting for more
        input.

        Parameters
        ----------
        source : str, optional

            The source to execute. If not specified, the input buffer will be
            used. If specified and 'hidden' is False, the input buffer will be
            replaced with the source before execution.

        hidden : bool, optional (default False)

            If set, no output will be shown and the prompt will not be modified.
            In other words, it will be completely invisible to the user that
            an execution has occurred.

        interactive : bool, optional (default False)

            Whether the console is to treat the source as having been manually
            entered by the user. The effect of this parameter depends on the
            subclass implementation.

        Raises
        ------
        RuntimeError
            If incomplete input is given and 'hidden' is True. In this case,
            it is not possible to prompt for more input.

        Returns
        -------
        A boolean indicating whether the source was executed.
        """
        # WARNING: The order in which things happen here is very particular, in
        # large part because our syntax highlighting is fragile. If you change
        # something, test carefully!

        # Decide what to execute.
        if source is None:
            source = self.input_buffer
        elif not hidden:
            self.input_buffer = source

        if hidden:
            self._execute(source, hidden)
        # Execute the source or show a continuation prompt if it is incomplete.
        elif interactive and self.execute_on_complete_input:
            self._register_is_complete_callback(
                source, partial(self.do_execute, source))
        else:
            self.do_execute(source, True, '')

    def do_execute(self, source, complete, indent):
        if complete:
            self._append_plain_text('\n')
            self._input_buffer_executing = self.input_buffer
            self._executing = True
            self._finalize_input_request()

            # Perform actual execution.
            self._execute(source, False)

        else:
            # Do this inside an edit block so continuation prompts are
            # removed seamlessly via undo/redo.
            cursor = self._get_end_cursor()
            cursor.beginEditBlock()
            try:
                cursor.insertText('\n')
                self._insert_continuation_prompt(cursor, indent)
            finally:
                cursor.endEditBlock()

            # Do not do this inside the edit block. It works as expected
            # when using a QPlainTextEdit control, but does not have an
            # effect when using a QTextEdit. I believe this is a Qt bug.
            self._control.moveCursor(QtGui.QTextCursor.End)

            # Advance where text is inserted
            self._insert_text_cursor.movePosition(QtGui.QTextCursor.End)

    def export_html(self):
        """ Shows a dialog to export HTML/XML in various formats.
        """
        self._html_exporter.export()

    def _finalize_input_request(self):
        """
        Set the widget to a non-reading state.
        """
        # Must set _reading to False before calling _prompt_finished
        self._reading = False
        self._prompt_finished()

        # There is no prompt now, so before_prompt_position is eof
        self._append_before_prompt_cursor.setPosition(
            self._get_end_cursor().position())

        self._insert_text_cursor.setPosition(
            self._get_end_cursor().position())

        # The maximum block count is only in effect during execution.
        # This ensures that _prompt_pos does not become invalid due to
        # text truncation.
        self._control.document().setMaximumBlockCount(self.buffer_size)

        # Setting a positive maximum block count will automatically
        # disable the undo/redo history, but just to be safe:
        self._control.setUndoRedoEnabled(False)

    def _get_input_buffer(self, force=False):
        """ The text that the user has entered entered at the current prompt.

        If the console is currently executing, the text that is executing will
        always be returned.
        """
        # If we're executing, the input buffer may not even exist anymore due to
        # the limit imposed by 'buffer_size'. Therefore, we store it.
        if self._executing and not force:
            return self._input_buffer_executing

        cursor = self._get_end_cursor()
        cursor.setPosition(self._prompt_pos, QtGui.QTextCursor.KeepAnchor)
        input_buffer = cursor.selection().toPlainText()

        # Strip out continuation prompts.
        return input_buffer.replace('\n' + self._continuation_prompt, '\n')

    def _set_input_buffer(self, string):
        """ Sets the text in the input buffer.

        If the console is currently executing, this call has no *immediate*
        effect. When the execution is finished, the input buffer will be updated
        appropriately.
        """
        # If we're executing, store the text for later.
        if self._executing:
            self._input_buffer_pending = string
            return

        # Remove old text.
        cursor = self._get_end_cursor()
        cursor.beginEditBlock()
        cursor.setPosition(self._prompt_pos, QtGui.QTextCursor.KeepAnchor)
        cursor.removeSelectedText()

        # Insert new text with continuation prompts.
        self._insert_plain_text_into_buffer(self._get_prompt_cursor(), string)
        cursor.endEditBlock()
        self._control.moveCursor(QtGui.QTextCursor.End)

    input_buffer = property(_get_input_buffer, _set_input_buffer)

    def _get_font(self):
        """ The base font being used by the ConsoleWidget.
        """
        return self._control.document().defaultFont()

    def _get_font_width(self, font=None):
        if font is None:
            font = self.font
        font_metrics = QtGui.QFontMetrics(font)
        if hasattr(font_metrics, 'horizontalAdvance'):
            return font_metrics.horizontalAdvance(' ')
        else:
            return font_metrics.width(' ')

    def _set_font(self, font):
        """ Sets the base font for the ConsoleWidget to the specified QFont.
        """
        self._control.setTabStopWidth(
            self.tab_width * self._get_font_width(font)
        )

        self._completion_widget.setFont(font)
        self._control.document().setDefaultFont(font)
        if self._page_control:
            self._page_control.document().setDefaultFont(font)

        self.font_changed.emit(font)

    font = property(_get_font, _set_font)

    def _set_completion_widget(self, gui_completion):
        """ Set gui completion widget.
        """
        if gui_completion == 'ncurses':
            self._completion_widget = CompletionHtml(self)
        elif gui_completion == 'droplist':
            self._completion_widget = CompletionWidget(self)
        elif gui_completion == 'plain':
            self._completion_widget = CompletionPlain(self)

        self.gui_completion = gui_completion

    def open_anchor(self, anchor):
        """ Open selected anchor in the default webbrowser
        """
        webbrowser.open( anchor )

    def paste(self, mode=QtGui.QClipboard.Clipboard):
        """ Paste the contents of the clipboard into the input region.

        Parameters
        ----------
        mode : QClipboard::Mode, optional [default QClipboard::Clipboard]

            Controls which part of the system clipboard is used. This can be
            used to access the selection clipboard in X11 and the Find buffer
            in Mac OS. By default, the regular clipboard is used.
        """
        if self._control.textInteractionFlags() & QtCore.Qt.TextEditable:
            # Make sure the paste is safe.
            self._keep_cursor_in_buffer()
            cursor = self._control.textCursor()

            # Remove any trailing newline, which confuses the GUI and forces the
            # user to backspace.
            text = QtWidgets.QApplication.clipboard().text(mode).rstrip()

            # dedent removes "common leading whitespace" but to preserve relative
            # indent of multiline code, we have to compensate for any
            # leading space on the first line, if we're pasting into
            # an indented position.
            cursor_offset = cursor.position() - self._get_line_start_pos()
            if text.startswith(' ' * cursor_offset):
                text = text[cursor_offset:]

            self._insert_plain_text_into_buffer(cursor, dedent(text))

    def print_(self, printer=None):
        """ Print the contents of the ConsoleWidget to the specified QPrinter.
        """
        if not printer:
            printer = QtPrintSupport.QPrinter()
            if QtPrintSupport.QPrintDialog(printer).exec_() != QtPrintSupport.QPrintDialog.Accepted:
                return
        self._control.print_(printer)

    def prompt_to_top(self):
        """ Moves the prompt to the top of the viewport.
        """
        if not self._executing:
            prompt_cursor = self._get_prompt_cursor()
            if self._get_cursor().blockNumber() < prompt_cursor.blockNumber():
                self._set_cursor(prompt_cursor)
            self._set_top_cursor(prompt_cursor)

    def redo(self):
        """ Redo the last operation. If there is no operation to redo, nothing
            happens.
        """
        self._control.redo()

    def reset_font(self):
        """ Sets the font to the default fixed-width font for this platform.
        """
        if sys.platform == 'win32':
            # Consolas ships with Vista/Win7, fallback to Courier if needed
            fallback = 'Courier'
        elif sys.platform == 'darwin':
            # OSX always has Monaco
            fallback = 'Monaco'
        else:
            # Monospace should always exist
            fallback = 'Monospace'
        font = get_font(self.font_family, fallback)
        if self.font_size:
            font.setPointSize(self.font_size)
        else:
            font.setPointSize(QtWidgets.QApplication.instance().font().pointSize())
        font.setStyleHint(QtGui.QFont.TypeWriter)
        self._set_font(font)

    def change_font_size(self, delta):
        """Change the font size by the specified amount (in points).
        """
        font = self.font
        size = max(font.pointSize() + delta, 1) # minimum 1 point
        font.setPointSize(size)
        self._set_font(font)

    def _increase_font_size(self):
        self.change_font_size(1)

    def _decrease_font_size(self):
        self.change_font_size(-1)

    def select_all_smart(self):
        """ Select current cell, or, if already selected, the whole document.
        """
        c = self._get_cursor()
        sel_range = c.selectionStart(), c.selectionEnd()

        c.clearSelection()
        c.setPosition(self._get_prompt_cursor().position())
        c.setPosition(self._get_end_pos(),
                      mode=QtGui.QTextCursor.KeepAnchor)
        new_sel_range = c.selectionStart(), c.selectionEnd()
        if sel_range == new_sel_range:
            # cell already selected, expand selection to whole document
            self.select_document()
        else:
            # set cell selection as active selection
            self._control.setTextCursor(c)

    def select_document(self):
        """ Selects all the text in the buffer.
        """
        self._control.selectAll()

    def _get_tab_width(self):
        """ The width (in terms of space characters) for tab characters.
        """
        return self._tab_width

    def _set_tab_width(self, tab_width):
        """ Sets the width (in terms of space characters) for tab characters.
        """
        self._control.setTabStopWidth(tab_width * self._get_font_width())

        self._tab_width = tab_width

    tab_width = property(_get_tab_width, _set_tab_width)

    def undo(self):
        """ Undo the last operation. If there is no operation to undo, nothing
            happens.
        """
        self._control.undo()

    #---------------------------------------------------------------------------
    # 'ConsoleWidget' abstract interface
    #---------------------------------------------------------------------------

    def _is_complete(self, source, interactive):
        """ Returns whether 'source' can be executed. When triggered by an
            Enter/Return key press, 'interactive' is True; otherwise, it is
            False.
        """
        raise NotImplementedError

    def _execute(self, source, hidden):
        """ Execute 'source'. If 'hidden', do not show any output.
        """
        raise NotImplementedError

    def _prompt_started_hook(self):
        """ Called immediately after a new prompt is displayed.
        """
        pass

    def _prompt_finished_hook(self):
        """ Called immediately after a prompt is finished, i.e. when some input
            will be processed and a new prompt displayed.
        """
        pass

    def _up_pressed(self, shift_modifier):
        """ Called when the up key is pressed. Returns whether to continue
            processing the event.
        """
        return True

    def _down_pressed(self, shift_modifier):
        """ Called when the down key is pressed. Returns whether to continue
            processing the event.
        """
        return True

    def _tab_pressed(self):
        """ Called when the tab key is pressed. Returns whether to continue
            processing the event.
        """
        return True

    #--------------------------------------------------------------------------
    # 'ConsoleWidget' protected interface
    #--------------------------------------------------------------------------

    def _append_custom(self, insert, input, before_prompt=False, *args, **kwargs):
        """ A low-level method for appending content to the end of the buffer.

        If 'before_prompt' is enabled, the content will be inserted before the
        current prompt, if there is one.
        """
        # Determine where to insert the content.
        cursor = self._insert_text_cursor
        if before_prompt and (self._reading or not self._executing):
            self._flush_pending_stream()

            # Jump to before prompt, if there is one
            if cursor.position() >= self._append_before_prompt_pos \
                    and self._append_before_prompt_pos != self._get_end_pos():
                cursor.setPosition(self._append_before_prompt_pos)

                # If we're appending on the same line as the prompt, use insert mode.
                # If so, the character at self._append_before_prompt_pos will not be a newline
                cursor.movePosition(QtGui.QTextCursor.Right,
                                    QtGui.QTextCursor.KeepAnchor)
                if cursor.selection().toPlainText() != '\n':
                    cursor._insert_mode = True
                cursor.movePosition(QtGui.QTextCursor.Left)
        else:
            # Insert at current printing point.
            # If cursor is before prompt jump to end, but only if there
            # is a prompt (before_prompt_pos != end)
            if cursor.position() <= self._append_before_prompt_pos \
                    and self._append_before_prompt_pos != self._get_end_pos():
                cursor.movePosition(QtGui.QTextCursor.End)

            if insert != self._insert_plain_text:
                self._flush_pending_stream()

        # Perform the insertion.
        result = insert(cursor, input, *args, **kwargs)

        # Remove insert mode tag
        if hasattr(cursor, '_insert_mode'):
            del cursor._insert_mode

        return result

    def _append_block(self, block_format=None, before_prompt=False):
        """ Appends an new QTextBlock to the end of the console buffer.
        """
        self._append_custom(self._insert_block, block_format, before_prompt)

    def _append_html(self, html, before_prompt=False):
        """ Appends HTML at the end of the console buffer.
        """
        self._append_custom(self._insert_html, html, before_prompt)

    def _append_html_fetching_plain_text(self, html, before_prompt=False):
        """ Appends HTML, then returns the plain text version of it.
        """
        return self._append_custom(self._insert_html_fetching_plain_text,
                                   html, before_prompt)

    def _append_plain_text(self, text, before_prompt=False):
        """ Appends plain text, processing ANSI codes if enabled.
        """
        self._append_custom(self._insert_plain_text, text, before_prompt)

    def _cancel_completion(self):
        """ If text completion is progress, cancel it.
        """
        self._completion_widget.cancel_completion()

    def _clear_temporary_buffer(self):
        """ Clears the "temporary text" buffer, i.e. all the text following
            the prompt region.
        """
        # Select and remove all text below the input buffer.
        cursor = self._get_prompt_cursor()
        prompt = self._continuation_prompt.lstrip()
        if self._temp_buffer_filled:
            self._temp_buffer_filled = False
            while cursor.movePosition(QtGui.QTextCursor.NextBlock):
                temp_cursor = QtGui.QTextCursor(cursor)
                temp_cursor.select(QtGui.QTextCursor.BlockUnderCursor)
                text = temp_cursor.selection().toPlainText().lstrip()
                if not text.startswith(prompt):
                    break
        else:
            # We've reached the end of the input buffer and no text follows.
            return
        cursor.movePosition(QtGui.QTextCursor.Left) # Grab the newline.
        cursor.movePosition(QtGui.QTextCursor.End,
                            QtGui.QTextCursor.KeepAnchor)
        cursor.removeSelectedText()

        # After doing this, we have no choice but to clear the undo/redo
        # history. Otherwise, the text is not "temporary" at all, because it
        # can be recalled with undo/redo. Unfortunately, Qt does not expose
        # fine-grained control to the undo/redo system.
        if self._control.isUndoRedoEnabled():
            self._control.setUndoRedoEnabled(False)
            self._control.setUndoRedoEnabled(True)

    def _complete_with_items(self, cursor, items):
        """ Performs completion with 'items' at the specified cursor location.
        """
        self._cancel_completion()

        if len(items) == 1:
            cursor.setPosition(self._control.textCursor().position(),
                               QtGui.QTextCursor.KeepAnchor)
            cursor.insertText(items[0])

        elif len(items) > 1:
            current_pos = self._control.textCursor().position()
            prefix = os.path.commonprefix(items)
            if prefix:
                cursor.setPosition(current_pos, QtGui.QTextCursor.KeepAnchor)
                cursor.insertText(prefix)
                current_pos = cursor.position()

            self._completion_widget.show_items(cursor, items,
                                               prefix_length=len(prefix))

    def _fill_temporary_buffer(self, cursor, text, html=False):
        """fill the area below the active editting zone with text"""

        current_pos = self._control.textCursor().position()

        cursor.beginEditBlock()
        self._append_plain_text('\n')
        self._page(text, html=html)
        cursor.endEditBlock()

        cursor.setPosition(current_pos)
        self._control.moveCursor(QtGui.QTextCursor.End)
        self._control.setTextCursor(cursor)

        self._temp_buffer_filled = True


    def _context_menu_make(self, pos):
        """ Creates a context menu for the given QPoint (in widget coordinates).
        """
        menu = QtWidgets.QMenu(self)

        self.cut_action = menu.addAction('Cut', self.cut)
        self.cut_action.setEnabled(self.can_cut())
        self.cut_action.setShortcut(QtGui.QKeySequence.Cut)

        self.copy_action = menu.addAction('Copy', self.copy)
        self.copy_action.setEnabled(self.can_copy())
        self.copy_action.setShortcut(QtGui.QKeySequence.Copy)

        self.paste_action = menu.addAction('Paste', self.paste)
        self.paste_action.setEnabled(self.can_paste())
        self.paste_action.setShortcut(QtGui.QKeySequence.Paste)

        anchor = self._control.anchorAt(pos)
        if anchor:
            menu.addSeparator()
            self.copy_link_action = menu.addAction(
                'Copy Link Address', lambda: self.copy_anchor(anchor=anchor))
            self.open_link_action = menu.addAction(
                'Open Link', lambda: self.open_anchor(anchor=anchor))

        menu.addSeparator()
        menu.addAction(self.select_all_action)

        menu.addSeparator()
        menu.addAction(self.export_action)
        menu.addAction(self.print_action)

        return menu

    def _control_key_down(self, modifiers, include_command=False):
        """ Given a KeyboardModifiers flags object, return whether the Control
        key is down.

        Parameters
        ----------
        include_command : bool, optional (default True)
            Whether to treat the Command key as a (mutually exclusive) synonym
            for Control when in Mac OS.
        """
        # Note that on Mac OS, ControlModifier corresponds to the Command key
        # while MetaModifier corresponds to the Control key.
        if sys.platform == 'darwin':
            down = include_command and (modifiers & QtCore.Qt.ControlModifier)
            return bool(down) ^ bool(modifiers & QtCore.Qt.MetaModifier)
        else:
            return bool(modifiers & QtCore.Qt.ControlModifier)

    def _create_control(self):
        """ Creates and connects the underlying text widget.
        """
        # Create the underlying control.
        if self.custom_control:
            control = self.custom_control()
        elif self.kind == 'plain':
            control = QtWidgets.QPlainTextEdit()
        elif self.kind == 'rich':
            control = QtWidgets.QTextEdit()
            control.setAcceptRichText(False)
            control.setMouseTracking(True)

        # Prevent the widget from handling drops, as we already provide
        # the logic in this class.
        control.setAcceptDrops(False)

        # Install event filters. The filter on the viewport is needed for
        # mouse events.
        control.installEventFilter(self)
        control.viewport().installEventFilter(self)

        # Connect signals.
        control.customContextMenuRequested.connect(
            self._custom_context_menu_requested)
        control.copyAvailable.connect(self.copy_available)
        control.redoAvailable.connect(self.redo_available)
        control.undoAvailable.connect(self.undo_available)

        # Hijack the document size change signal to prevent Qt from adjusting
        # the viewport's scrollbar. We are relying on an implementation detail
        # of Q(Plain)TextEdit here, which is potentially dangerous, but without
        # this functionality we cannot create a nice terminal interface.
        layout = control.document().documentLayout()
        layout.documentSizeChanged.disconnect()
        layout.documentSizeChanged.connect(self._adjust_scrollbars)

        # Configure the scrollbar policy
        if self.scrollbar_visibility:
            scrollbar_policy = QtCore.Qt.ScrollBarAlwaysOn
        else :
            scrollbar_policy = QtCore.Qt.ScrollBarAlwaysOff

        # Configure the control.
        control.setAttribute(QtCore.Qt.WA_InputMethodEnabled, True)
        control.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        control.setReadOnly(True)
        control.setUndoRedoEnabled(False)
        control.setVerticalScrollBarPolicy(scrollbar_policy)
        return control

    def _create_page_control(self):
        """ Creates and connects the underlying paging widget.
        """
        if self.custom_page_control:
            control = self.custom_page_control()
        elif self.kind == 'plain':
            control = QtWidgets.QPlainTextEdit()
        elif self.kind == 'rich':
            control = QtWidgets.QTextEdit()
        control.installEventFilter(self)
        viewport = control.viewport()
        viewport.installEventFilter(self)
        control.setReadOnly(True)
        control.setUndoRedoEnabled(False)

        # Configure the scrollbar policy
        if self.scrollbar_visibility:
            scrollbar_policy = QtCore.Qt.ScrollBarAlwaysOn
        else :
            scrollbar_policy = QtCore.Qt.ScrollBarAlwaysOff

        control.setVerticalScrollBarPolicy(scrollbar_policy)
        return control

    def _event_filter_console_keypress(self, event):
        """ Filter key events for the underlying text widget to create a
            console-like interface.
        """
        intercepted = False
        cursor = self._control.textCursor()
        position = cursor.position()
        key = event.key()
        ctrl_down = self._control_key_down(event.modifiers())
        alt_down = event.modifiers() & QtCore.Qt.AltModifier
        shift_down = event.modifiers() & QtCore.Qt.ShiftModifier

        cmd_down = (
            sys.platform == "darwin" and
            self._control_key_down(event.modifiers(), include_command=True)
        )
        if cmd_down:
            if key == QtCore.Qt.Key_Left:
                key = QtCore.Qt.Key_Home
            elif key == QtCore.Qt.Key_Right:
                key = QtCore.Qt.Key_End
            elif key == QtCore.Qt.Key_Up:
                ctrl_down = True
                key = QtCore.Qt.Key_Home
            elif key == QtCore.Qt.Key_Down:
                ctrl_down = True
                key = QtCore.Qt.Key_End
        #------ Special modifier logic -----------------------------------------

        if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            intercepted = True

            # Special handling when tab completing in text mode.
            self._cancel_completion()

            if self._in_buffer(position):
                # Special handling when a reading a line of raw input.
                if self._reading:
                    self._append_plain_text('\n')
                    self._reading = False
                    if self._reading_callback:
                        self._reading_callback()

                # If the input buffer is a single line or there is only
                # whitespace after the cursor, execute. Otherwise, split the
                # line with a continuation prompt.
                elif not self._executing:
                    cursor.movePosition(QtGui.QTextCursor.End,
                                        QtGui.QTextCursor.KeepAnchor)
                    at_end = len(cursor.selectedText().strip()) == 0
                    single_line = (self._get_end_cursor().blockNumber() ==
                                   self._get_prompt_cursor().blockNumber())
                    if (at_end or shift_down or single_line) and not ctrl_down:
                        self.execute(interactive = not shift_down)
                    else:
                        # Do this inside an edit block for clean undo/redo.
                        pos = self._get_input_buffer_cursor_pos()
                        def callback(complete, indent):
                            try:
                                cursor.beginEditBlock()
                                cursor.setPosition(position)
                                cursor.insertText('\n')
                                self._insert_continuation_prompt(cursor)
                                if indent:
                                    cursor.insertText(indent)
                            finally:
                                cursor.endEditBlock()

                            # Ensure that the whole input buffer is visible.
                            # FIXME: This will not be usable if the input buffer is
                            # taller than the console widget.
                            self._control.moveCursor(QtGui.QTextCursor.End)
                            self._control.setTextCursor(cursor)
                        self._register_is_complete_callback(
                            self._get_input_buffer()[:pos], callback)

        #------ Control/Cmd modifier -------------------------------------------

        elif ctrl_down:
            if key == QtCore.Qt.Key_G:
                self._keyboard_quit()
                intercepted = True

            elif key == QtCore.Qt.Key_K:
                if self._in_buffer(position):
                    cursor.clearSelection()
                    cursor.movePosition(QtGui.QTextCursor.EndOfLine,
                                        QtGui.QTextCursor.KeepAnchor)
                    if not cursor.hasSelection():
                        # Line deletion (remove continuation prompt)
                        cursor.movePosition(QtGui.QTextCursor.NextBlock,
                                            QtGui.QTextCursor.KeepAnchor)
                        cursor.movePosition(QtGui.QTextCursor.Right,
                                            QtGui.QTextCursor.KeepAnchor,
                                            len(self._continuation_prompt))
                    self._kill_ring.kill_cursor(cursor)
                    self._set_cursor(cursor)
                intercepted = True

            elif key == QtCore.Qt.Key_L:
                self.prompt_to_top()
                intercepted = True

            elif key == QtCore.Qt.Key_O:
                if self._page_control and self._page_control.isVisible():
                    self._page_control.setFocus()
                intercepted = True

            elif key == QtCore.Qt.Key_U:
                if self._in_buffer(position):
                    cursor.clearSelection()
                    start_line = cursor.blockNumber()
                    if start_line == self._get_prompt_cursor().blockNumber():
                        offset = len(self._prompt)
                    else:
                        offset = len(self._continuation_prompt)
                    cursor.movePosition(QtGui.QTextCursor.StartOfBlock,
                                        QtGui.QTextCursor.KeepAnchor)
                    cursor.movePosition(QtGui.QTextCursor.Right,
                                        QtGui.QTextCursor.KeepAnchor, offset)
                    self._kill_ring.kill_cursor(cursor)
                    self._set_cursor(cursor)
                intercepted = True

            elif key == QtCore.Qt.Key_Y:
                self._keep_cursor_in_buffer()
                self._kill_ring.yank()
                intercepted = True

            elif key in (QtCore.Qt.Key_Backspace, QtCore.Qt.Key_Delete):
                if key == QtCore.Qt.Key_Backspace:
                    cursor = self._get_word_start_cursor(position)
                else: # key == QtCore.Qt.Key_Delete
                    cursor = self._get_word_end_cursor(position)
                cursor.setPosition(position, QtGui.QTextCursor.KeepAnchor)
                self._kill_ring.kill_cursor(cursor)
                intercepted = True

            elif key == QtCore.Qt.Key_D:
                if len(self.input_buffer) == 0 and not self._executing:
                    self.exit_requested.emit(self)
                # if executing and input buffer empty
                elif len(self._get_input_buffer(force=True)) == 0:
                    # input a EOT ansi control character
                    self._control.textCursor().insertText(chr(4))
                    new_event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                                QtCore.Qt.Key_Return,
                                                QtCore.Qt.NoModifier)
                    QtWidgets.QApplication.instance().sendEvent(self._control, new_event)
                    intercepted = True
                else:
                    new_event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                                QtCore.Qt.Key_Delete,
                                                QtCore.Qt.NoModifier)
                    QtWidgets.QApplication.instance().sendEvent(self._control, new_event)
                    intercepted = True

            elif key == QtCore.Qt.Key_Down:
                self._scroll_to_end()

            elif key == QtCore.Qt.Key_Up:
                self._control.verticalScrollBar().setValue(0)
        #------ Alt modifier ---------------------------------------------------

        elif alt_down:
            if key == QtCore.Qt.Key_B:
                self._set_cursor(self._get_word_start_cursor(position))
                intercepted = True

            elif key == QtCore.Qt.Key_F:
                self._set_cursor(self._get_word_end_cursor(position))
                intercepted = True

            elif key == QtCore.Qt.Key_Y:
                self._kill_ring.rotate()
                intercepted = True

            elif key == QtCore.Qt.Key_Backspace:
                cursor = self._get_word_start_cursor(position)
                cursor.setPosition(position, QtGui.QTextCursor.KeepAnchor)
                self._kill_ring.kill_cursor(cursor)
                intercepted = True

            elif key == QtCore.Qt.Key_D:
                cursor = self._get_word_end_cursor(position)
                cursor.setPosition(position, QtGui.QTextCursor.KeepAnchor)
                self._kill_ring.kill_cursor(cursor)
                intercepted = True

            elif key == QtCore.Qt.Key_Delete:
                intercepted = True

            elif key == QtCore.Qt.Key_Greater:
                self._control.moveCursor(QtGui.QTextCursor.End)
                intercepted = True

            elif key == QtCore.Qt.Key_Less:
                self._control.setTextCursor(self._get_prompt_cursor())
                intercepted = True

        #------ No modifiers ---------------------------------------------------

        else:
            self._trigger_is_complete_callback()
            if shift_down:
                anchormode = QtGui.QTextCursor.KeepAnchor
            else:
                anchormode = QtGui.QTextCursor.MoveAnchor

            if key == QtCore.Qt.Key_Escape:
                self._keyboard_quit()
                intercepted = True

            elif key == QtCore.Qt.Key_Up and not shift_down:
                if self._reading or not self._up_pressed(shift_down):
                    intercepted = True
                else:
                    prompt_line = self._get_prompt_cursor().blockNumber()
                    intercepted = cursor.blockNumber() <= prompt_line

            elif key == QtCore.Qt.Key_Down and not shift_down:
                if self._reading or not self._down_pressed(shift_down):
                    intercepted = True
                else:
                    end_line = self._get_end_cursor().blockNumber()
                    intercepted = cursor.blockNumber() == end_line

            elif key == QtCore.Qt.Key_Tab:
                if not self._reading:
                    if self._tab_pressed():
                        self._indent(dedent=False)
                    intercepted = True

            elif key == QtCore.Qt.Key_Backtab:
                self._indent(dedent=True)
                intercepted = True

            elif key == QtCore.Qt.Key_Left and not shift_down:

                # Move to the previous line
                line, col = cursor.blockNumber(), cursor.columnNumber()
                if line > self._get_prompt_cursor().blockNumber() and \
                        col == len(self._continuation_prompt):
                    self._control.moveCursor(QtGui.QTextCursor.PreviousBlock,
                                             mode=anchormode)
                    self._control.moveCursor(QtGui.QTextCursor.EndOfBlock,
                                             mode=anchormode)
                    intercepted = True

                # Regular left movement
                else:
                    intercepted = not self._in_buffer(position - 1)

            elif key == QtCore.Qt.Key_Right and not shift_down:
                #original_block_number = cursor.blockNumber()
                if position == self._get_line_end_pos():
                    cursor.movePosition(QtGui.QTextCursor.NextBlock, mode=anchormode)
                    cursor.movePosition(QtGui.QTextCursor.Right,
                                        mode=anchormode,
                                        n=len(self._continuation_prompt))
                    self._control.setTextCursor(cursor)
                else:
                    self._control.moveCursor(QtGui.QTextCursor.Right,
                                             mode=anchormode)
                intercepted = True

            elif key == QtCore.Qt.Key_Home:
                start_pos = self._get_line_start_pos()

                c = self._get_cursor()
                spaces = self._get_leading_spaces()
                if (c.position() > start_pos + spaces or
                        c.columnNumber() == len(self._continuation_prompt)):
                    start_pos += spaces     # Beginning of text

                if shift_down and self._in_buffer(position):
                    if c.selectedText():
                        sel_max = max(c.selectionStart(), c.selectionEnd())
                        cursor.setPosition(sel_max,
                                           QtGui.QTextCursor.MoveAnchor)
                    cursor.setPosition(start_pos, QtGui.QTextCursor.KeepAnchor)
                else:
                    cursor.setPosition(start_pos)
                self._set_cursor(cursor)
                intercepted = True

            elif key == QtCore.Qt.Key_Backspace:

                # Line deletion (remove continuation prompt)
                line, col = cursor.blockNumber(), cursor.columnNumber()
                if not self._reading and \
                        col == len(self._continuation_prompt) and \
                        line > self._get_prompt_cursor().blockNumber():
                    cursor.beginEditBlock()
                    cursor.movePosition(QtGui.QTextCursor.StartOfBlock,
                                        QtGui.QTextCursor.KeepAnchor)
                    cursor.removeSelectedText()
                    cursor.deletePreviousChar()
                    cursor.endEditBlock()
                    intercepted = True

                # Regular backwards deletion
                else:
                    anchor = cursor.anchor()
                    if anchor == position:
                        intercepted = not self._in_buffer(position - 1)
                    else:
                        intercepted = not self._in_buffer(min(anchor, position))

            elif key == QtCore.Qt.Key_Delete:

                # Line deletion (remove continuation prompt)
                if not self._reading and self._in_buffer(position) and \
                        cursor.atBlockEnd() and not cursor.hasSelection():
                    cursor.movePosition(QtGui.QTextCursor.NextBlock,
                                        QtGui.QTextCursor.KeepAnchor)
                    cursor.movePosition(QtGui.QTextCursor.Right,
                                        QtGui.QTextCursor.KeepAnchor,
                                        len(self._continuation_prompt))
                    cursor.removeSelectedText()
                    intercepted = True

                # Regular forwards deletion:
                else:
                    anchor = cursor.anchor()
                    intercepted = (not self._in_buffer(anchor) or
                                   not self._in_buffer(position))

        #------ Special sequences ----------------------------------------------

        if not intercepted:
            if event.matches(QtGui.QKeySequence.Copy):
                self.copy()
                intercepted = True

            elif event.matches(QtGui.QKeySequence.Cut):
                self.cut()
                intercepted = True

            elif event.matches(QtGui.QKeySequence.Paste):
                self.paste()
                intercepted = True

        # Don't move the cursor if Control/Cmd is pressed to allow copy-paste
        # using the keyboard in any part of the buffer. Also, permit scrolling
        # with Page Up/Down keys. Finally, if we're executing, don't move the
        # cursor (if even this made sense, we can't guarantee that the prompt
        # position is still valid due to text truncation).
        if not (self._control_key_down(event.modifiers(), include_command=True)
                or key in (QtCore.Qt.Key_PageUp, QtCore.Qt.Key_PageDown)
                or (self._executing and not self._reading)
                or (event.text() == "" and not
                    (not shift_down and key in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down)))):
            self._keep_cursor_in_buffer()

        return intercepted

    def _event_filter_page_keypress(self, event):
        """ Filter key events for the paging widget to create console-like
            interface.
        """
        key = event.key()
        ctrl_down = self._control_key_down(event.modifiers())
        alt_down = event.modifiers() & QtCore.Qt.AltModifier

        if ctrl_down:
            if key == QtCore.Qt.Key_O:
                self._control.setFocus()
                return True

        elif alt_down:
            if key == QtCore.Qt.Key_Greater:
                self._page_control.moveCursor(QtGui.QTextCursor.End)
                return True

            elif key == QtCore.Qt.Key_Less:
                self._page_control.moveCursor(QtGui.QTextCursor.Start)
                return True

        elif key in (QtCore.Qt.Key_Q, QtCore.Qt.Key_Escape):
            if self._splitter:
                self._page_control.hide()
                self._control.setFocus()
            else:
                self.layout().setCurrentWidget(self._control)
                # re-enable buffer truncation after paging
                self._control.document().setMaximumBlockCount(self.buffer_size)
            return True

        elif key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return,
                     QtCore.Qt.Key_Tab):
            new_event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                        QtCore.Qt.Key_PageDown,
                                        QtCore.Qt.NoModifier)
            QtWidgets.QApplication.instance().sendEvent(self._page_control, new_event)
            return True

        elif key == QtCore.Qt.Key_Backspace:
            new_event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                        QtCore.Qt.Key_PageUp,
                                        QtCore.Qt.NoModifier)
            QtWidgets.QApplication.instance().sendEvent(self._page_control, new_event)
            return True

        # vi/less -like key bindings
        elif key == QtCore.Qt.Key_J:
            new_event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                        QtCore.Qt.Key_Down,
                                        QtCore.Qt.NoModifier)
            QtWidgets.QApplication.instance().sendEvent(self._page_control, new_event)
            return True

        # vi/less -like key bindings
        elif key == QtCore.Qt.Key_K:
            new_event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress,
                                        QtCore.Qt.Key_Up,
                                        QtCore.Qt.NoModifier)
            QtWidgets.QApplication.instance().sendEvent(self._page_control, new_event)
            return True

        return False

    def _on_flush_pending_stream_timer(self):
        """ Flush pending text into the widget on console timer trigger.
        """
        self._flush_pending_stream()

    def _flush_pending_stream(self):
        """
        Flush pending text into the widget.

        It only applies to text that is pending when the console is in the
        running state. Text printed when console is not running is shown
        immediately, and does not wait to be flushed.
        """
        text = self._pending_insert_text
        self._pending_insert_text = []
        buffer_size = self._control.document().maximumBlockCount()
        if buffer_size > 0:
            text = self._get_last_lines_from_list(text, buffer_size)
        text = ''.join(text)
        t = time.time()
        self._insert_plain_text(self._insert_text_cursor, text, flush=True)
        # Set the flush interval to equal the maximum time to update text.
        self._pending_text_flush_interval.setInterval(
            int(max(100, (time.time() - t) * 1000))
        )

    def _get_cursor(self):
        """ Get a cursor at the current insert position.
        """
        return self._control.textCursor()

    def _get_end_cursor(self):
        """ Get a cursor at the last character of the current cell.
        """
        cursor = self._control.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        return cursor

    def _get_end_pos(self):
        """ Get the position of the last character of the current cell.
        """
        return self._get_end_cursor().position()

    def _get_line_start_cursor(self):
        """ Get a cursor at the first character of the current line.
        """
        cursor = self._control.textCursor()
        start_line = cursor.blockNumber()
        if start_line == self._get_prompt_cursor().blockNumber():
            cursor.setPosition(self._prompt_pos)
        else:
            cursor.movePosition(QtGui.QTextCursor.StartOfLine)
            cursor.setPosition(cursor.position() +
                               len(self._continuation_prompt))
        return cursor

    def _get_line_start_pos(self):
        """ Get the position of the first character of the current line.
        """
        return self._get_line_start_cursor().position()

    def _get_line_end_cursor(self):
        """ Get a cursor at the last character of the current line.
        """
        cursor = self._control.textCursor()
        cursor.movePosition(QtGui.QTextCursor.EndOfLine)
        return cursor

    def _get_line_end_pos(self):
        """ Get the position of the last character of the current line.
        """
        return self._get_line_end_cursor().position()

    def _get_input_buffer_cursor_column(self):
        """ Get the column of the cursor in the input buffer, excluding the
            contribution by the prompt, or -1 if there is no such column.
        """
        prompt = self._get_input_buffer_cursor_prompt()
        if prompt is None:
            return -1
        else:
            cursor = self._control.textCursor()
            return cursor.columnNumber() - len(prompt)

    def _get_input_buffer_cursor_line(self):
        """ Get the text of the line of the input buffer that contains the
            cursor, or None if there is no such line.
        """
        prompt = self._get_input_buffer_cursor_prompt()
        if prompt is None:
            return None
        else:
            cursor = self._control.textCursor()
            text = cursor.block().text()
            return text[len(prompt):]

    def _get_input_buffer_cursor_pos(self):
        """Get the cursor position within the input buffer."""
        cursor = self._control.textCursor()
        cursor.setPosition(self._prompt_pos, QtGui.QTextCursor.KeepAnchor)
        input_buffer = cursor.selection().toPlainText()

        # Don't count continuation prompts
        return len(input_buffer.replace('\n' + self._continuation_prompt, '\n'))

    def _get_input_buffer_cursor_prompt(self):
        """ Returns the (plain text) prompt for line of the input buffer that
            contains the cursor, or None if there is no such line.
        """
        if self._executing:
            return None
        cursor = self._control.textCursor()
        if cursor.position() >= self._prompt_pos:
            if cursor.blockNumber() == self._get_prompt_cursor().blockNumber():
                return self._prompt
            else:
                return self._continuation_prompt
        else:
            return None

    def _get_last_lines(self, text, num_lines, return_count=False):
        """ Get the last specified number of lines of text (like `tail -n`).
        If return_count is True, returns a tuple of clipped text and the
        number of lines in the clipped text.
        """
        pos = len(text)
        if pos < num_lines:
            if return_count:
                return text, text.count('\n') if return_count else text
            else:
                return text
        i = 0
        while i < num_lines:
            pos = text.rfind('\n', None, pos)
            if pos == -1:
                pos = None
                break
            i += 1
        if return_count:
            return text[pos:], i
        else:
            return text[pos:]

    def _get_last_lines_from_list(self, text_list, num_lines):
        """ Get the list of text clipped to last specified lines.
        """
        ret = []
        lines_pending = num_lines
        for text in reversed(text_list):
            text, lines_added = self._get_last_lines(text, lines_pending,
                                                     return_count=True)
            ret.append(text)
            lines_pending -= lines_added
            if lines_pending <= 0:
                break
        return ret[::-1]

    def _get_leading_spaces(self):
        """ Get the number of leading spaces of the current line.
        """

        cursor = self._get_cursor()
        start_line = cursor.blockNumber()
        if start_line == self._get_prompt_cursor().blockNumber():
            # first line
            offset = len(self._prompt)
        else:
            # continuation
            offset = len(self._continuation_prompt)
        cursor.select(QtGui.QTextCursor.LineUnderCursor)
        text = cursor.selectedText()[offset:]
        return len(text) - len(text.lstrip())

    @property
    def _prompt_pos(self):
        """ Find the position in the text right after the prompt.
        """
        return min(self._prompt_cursor.position() + 1, self._get_end_pos())

    @property
    def _append_before_prompt_pos(self):
        """ Find the position in the text right before the prompt.
        """
        return min(self._append_before_prompt_cursor.position(),
                   self._get_end_pos())

    def _get_prompt_cursor(self):
        """ Get a cursor at the prompt position of the current cell.
        """
        cursor = self._control.textCursor()
        cursor.setPosition(self._prompt_pos)
        return cursor

    def _get_selection_cursor(self, start, end):
        """ Get a cursor with text selected between the positions 'start' and
            'end'.
        """
        cursor = self._control.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QtGui.QTextCursor.KeepAnchor)
        return cursor

    def _get_word_start_cursor(self, position):
        """ Find the start of the word to the left the given position. If a
            sequence of non-word characters precedes the first word, skip over
            them. (This emulates the behavior of bash, emacs, etc.)
        """
        document = self._control.document()
        cursor = self._control.textCursor()
        line_start_pos = self._get_line_start_pos()

        if position == self._prompt_pos:
            return cursor
        elif position == line_start_pos:
            # Cursor is at the beginning of a line, move to the last
            # non-whitespace character of the previous line
            cursor = self._control.textCursor()
            cursor.setPosition(position)
            cursor.movePosition(QtGui.QTextCursor.PreviousBlock)
            cursor.movePosition(QtGui.QTextCursor.EndOfBlock)
            position = cursor.position()
            while (
                position >= self._prompt_pos and
                is_whitespace(document.characterAt(position))
            ):
                position -= 1
            cursor.setPosition(position + 1)
        else:
            position -= 1

            # Find the last alphanumeric char, but don't move across lines
            while (
                position >= self._prompt_pos and
                position >= line_start_pos and
                not is_letter_or_number(document.characterAt(position))
            ):
                position -= 1

            # Find the first alphanumeric char, but don't move across lines
            while (
                position >= self._prompt_pos and
                position >= line_start_pos and
                is_letter_or_number(document.characterAt(position))
            ):
                position -= 1

            cursor.setPosition(position + 1)

        return cursor

    def _get_word_end_cursor(self, position):
        """ Find the end of the word to the right the given position. If a
            sequence of non-word characters precedes the first word, skip over
            them. (This emulates the behavior of bash, emacs, etc.)
        """
        document = self._control.document()
        cursor = self._control.textCursor()
        end_pos = self._get_end_pos()
        line_end_pos = self._get_line_end_pos()

        if position == end_pos:
            # Cursor is at the very end of the buffer
            return cursor
        elif position == line_end_pos:
            # Cursor is at the end of a line, move to the first
            # non-whitespace character of the next line
            cursor = self._control.textCursor()
            cursor.setPosition(position)
            cursor.movePosition(QtGui.QTextCursor.NextBlock)
            position = cursor.position() + len(self._continuation_prompt)
            while (
                position < end_pos and
                is_whitespace(document.characterAt(position))
            ):
                position += 1
            cursor.setPosition(position)
        else:
            if is_whitespace(document.characterAt(position)):
                # The next character is whitespace. If this is part of
                # indentation whitespace, skip to the first non-whitespace
                # character.
                is_indentation_whitespace = True
                back_pos = position - 1
                line_start_pos = self._get_line_start_pos()
                while back_pos >= line_start_pos:
                    if not is_whitespace(document.characterAt(back_pos)):
                        is_indentation_whitespace = False
                        break
                    back_pos -= 1
                if is_indentation_whitespace:
                    # Skip to the first non-whitespace character
                    while (
                        position < end_pos and
                        position < line_end_pos and
                        is_whitespace(document.characterAt(position))
                    ):
                        position += 1
                    cursor.setPosition(position)
                    return cursor

            while (
                position < end_pos and
                position < line_end_pos and
                not is_letter_or_number(document.characterAt(position))
            ):
                position += 1

            while (
                position < end_pos and
                position < line_end_pos and
                is_letter_or_number(document.characterAt(position))
            ):
                position += 1

            cursor.setPosition(position)
        return cursor

    def _indent(self, dedent=True):
        """ Indent/Dedent current line or current text selection.
        """
        num_newlines = self._get_cursor().selectedText().count("\u2029")
        save_cur = self._get_cursor()
        cur = self._get_cursor()

        # move to first line of selection, if present
        cur.setPosition(cur.selectionStart())
        self._control.setTextCursor(cur)
        spaces = self._get_leading_spaces()
        # calculate number of spaces neded to align/indent to 4-space multiple
        step = self._tab_width - (spaces % self._tab_width)

        # insertText shouldn't replace if selection is active
        cur.clearSelection()

        # indent all lines in selection (ir just current) by `step`
        for _ in range(num_newlines+1):
            # update underlying cursor for _get_line_start_pos
            self._control.setTextCursor(cur)
            # move to first non-ws char on line
            cur.setPosition(self._get_line_start_pos())
            if dedent:
                spaces = min(step, self._get_leading_spaces())
                safe_step = spaces % self._tab_width
                cur.movePosition(QtGui.QTextCursor.Right,
                                 QtGui.QTextCursor.KeepAnchor,
                                 min(spaces, safe_step if safe_step != 0
                                    else self._tab_width))
                cur.removeSelectedText()
            else:
                cur.insertText(' '*step)
            cur.movePosition(QtGui.QTextCursor.Down)

        # restore cursor
        self._control.setTextCursor(save_cur)

    def _insert_continuation_prompt(self, cursor, indent=''):
        """ Inserts new continuation prompt using the specified cursor.
        """
        if self._continuation_prompt_html is None:
            self._insert_plain_text(cursor, self._continuation_prompt)
        else:
            self._continuation_prompt = self._insert_html_fetching_plain_text(
                cursor, self._continuation_prompt_html)
        if indent:
            cursor.insertText(indent)

    def _insert_block(self, cursor, block_format=None):
        """ Inserts an empty QTextBlock using the specified cursor.
        """
        if block_format is None:
            block_format = QtGui.QTextBlockFormat()
        cursor.insertBlock(block_format)

    def _insert_html(self, cursor, html):
        """ Inserts HTML using the specified cursor in such a way that future
            formatting is unaffected.
        """
        cursor.beginEditBlock()
        cursor.insertHtml(html)

        # After inserting HTML, the text document "remembers" it's in "html
        # mode", which means that subsequent calls adding plain text will result
        # in unwanted formatting, lost tab characters, etc. The following code
        # hacks around this behavior, which I consider to be a bug in Qt, by
        # (crudely) resetting the document's style state.
        cursor.movePosition(QtGui.QTextCursor.Left,
                            QtGui.QTextCursor.KeepAnchor)
        if cursor.selection().toPlainText() == ' ':
            cursor.removeSelectedText()
        else:
            cursor.movePosition(QtGui.QTextCursor.Right)
        cursor.insertText(' ', QtGui.QTextCharFormat())
        cursor.endEditBlock()

    def _insert_html_fetching_plain_text(self, cursor, html):
        """ Inserts HTML using the specified cursor, then returns its plain text
            version.
        """
        cursor.beginEditBlock()
        cursor.removeSelectedText()

        start = cursor.position()
        self._insert_html(cursor, html)
        end = cursor.position()
        cursor.setPosition(start, QtGui.QTextCursor.KeepAnchor)
        text = cursor.selection().toPlainText()

        cursor.setPosition(end)
        cursor.endEditBlock()
        return text

    def _viewport_at_end(self):
        """Check if the viewport is at the end of the document."""
        viewport = self._control.viewport()
        end_scroll_pos = self._control.cursorForPosition(
            QtCore.QPoint(viewport.width() - 1, viewport.height() - 1)
            ).position()
        end_doc_pos = self._get_end_pos()
        return end_doc_pos - end_scroll_pos <= 1

    def _scroll_to_end(self):
        """Scroll to the end of the document."""
        end_scroll = (self._control.verticalScrollBar().maximum()
                      - self._control.verticalScrollBar().pageStep())
        # Only scroll down
        if end_scroll > self._control.verticalScrollBar().value():
            self._control.verticalScrollBar().setValue(end_scroll)

    def _insert_plain_text(self, cursor, text, flush=False):
        """ Inserts plain text using the specified cursor, processing ANSI codes
            if enabled.
        """
        should_autoscroll = self._viewport_at_end()
        # maximumBlockCount() can be different from self.buffer_size in
        # case input prompt is active.
        buffer_size = self._control.document().maximumBlockCount()

        if (self._executing and not flush and
                self._pending_text_flush_interval.isActive() and
                cursor.position() == self._insert_text_cursor.position()):
            # Queue the text to insert in case it is being inserted at end
            self._pending_insert_text.append(text)
            if buffer_size > 0:
                self._pending_insert_text = self._get_last_lines_from_list(
                    self._pending_insert_text, buffer_size)
            return

        if self._executing and not self._pending_text_flush_interval.isActive():
            self._pending_text_flush_interval.start()

        # Clip the text to last `buffer_size` lines.
        if buffer_size > 0:
            text = self._get_last_lines(text, buffer_size)

        cursor.beginEditBlock()
        if self.ansi_codes:
            for substring in self._ansi_processor.split_string(text):
                for act in self._ansi_processor.actions:

                    # Unlike real terminal emulators, we don't distinguish
                    # between the screen and the scrollback buffer. A screen
                    # erase request clears everything.
                    if act.action == 'erase':
                        remove = False
                        fill = False
                        if act.area == 'screen':
                            cursor.select(QtGui.QTextCursor.Document)
                            remove = True
                        if act.area == 'line':
                            if act.erase_to == 'all':
                                cursor.select(QtGui.QTextCursor.LineUnderCursor)
                                remove = True
                            elif act.erase_to == 'start':
                                cursor.movePosition(
                                    QtGui.QTextCursor.StartOfLine,
                                    QtGui.QTextCursor.KeepAnchor)
                                remove = True
                                fill = True
                            elif act.erase_to == 'end':
                                cursor.movePosition(
                                    QtGui.QTextCursor.EndOfLine,
                                    QtGui.QTextCursor.KeepAnchor)
                                remove = True
                        if remove:
                            nspace=cursor.selectionEnd()-cursor.selectionStart() if fill else 0
                            cursor.removeSelectedText()
                            if nspace>0: cursor.insertText(' '*nspace) # replace text by space, to keep cursor position as specified

                    # Simulate a form feed by scrolling just past the last line.
                    elif act.action == 'scroll' and act.unit == 'page':
                        cursor.insertText('\n')
                        cursor.endEditBlock()
                        self._set_top_cursor(cursor)
                        cursor.joinPreviousEditBlock()
                        cursor.deletePreviousChar()

                        if os.name == 'nt':
                            cursor.select(QtGui.QTextCursor.Document)
                            cursor.removeSelectedText()

                    elif act.action == 'move' and act.unit == 'line':
                        if act.dir == 'up':
                            for i in range(act.count):
                                cursor.movePosition(
                                    QtGui.QTextCursor.Up
                                )
                        elif act.dir == 'down':
                            for i in range(act.count):
                                cursor.movePosition(
                                    QtGui.QTextCursor.Down
                                )
                        elif act.dir == 'leftup':
                            for i in range(act.count):
                                cursor.movePosition(
                                    QtGui.QTextCursor.Up
                                )
                            cursor.movePosition(
                                QtGui.QTextCursor.StartOfLine,
                                QtGui.QTextCursor.MoveAnchor
                            )

                    elif act.action == 'carriage-return':
                        cursor.movePosition(
                            QtGui.QTextCursor.StartOfLine,
                            QtGui.QTextCursor.MoveAnchor)

                    elif act.action == 'beep':
                        QtWidgets.QApplication.instance().beep()

                    elif act.action == 'backspace':
                        if not cursor.atBlockStart():
                            cursor.movePosition(
                                QtGui.QTextCursor.PreviousCharacter,
                                QtGui.QTextCursor.MoveAnchor)

                    elif act.action == 'newline':
                        if (
                            cursor.block() != cursor.document().lastBlock()
                            and not cursor.document()
                            .toPlainText()
                            .endswith(self._prompt)
                        ):
                            cursor.movePosition(QtGui.QTextCursor.NextBlock)
                        else:
                            cursor.movePosition(
                                QtGui.QTextCursor.EndOfLine,
                                QtGui.QTextCursor.MoveAnchor,
                            )
                            cursor.insertText("\n")

                # simulate replacement mode
                if substring is not None:
                    format = self._ansi_processor.get_format()

                    # Note that using _insert_mode means the \r ANSI sequence will not swallow characters.
                    if not (hasattr(cursor, '_insert_mode') and cursor._insert_mode):
                        pos = cursor.position()
                        cursor2 = QtGui.QTextCursor(cursor)  # self._get_line_end_pos() is the previous line, don't use it
                        cursor2.movePosition(QtGui.QTextCursor.EndOfLine)
                        remain = cursor2.position() - pos    # number of characters until end of line
                        n=len(substring)
                        swallow = min(n, remain)             # number of character to swallow
                        cursor.setPosition(pos + swallow, QtGui.QTextCursor.KeepAnchor)
                    cursor.insertText(substring, format)
        else:
            cursor.insertText(text)
        cursor.endEditBlock()

        if should_autoscroll:
            self._scroll_to_end()

    def _insert_plain_text_into_buffer(self, cursor, text):
        """ Inserts text into the input buffer using the specified cursor (which
            must be in the input buffer), ensuring that continuation prompts are
            inserted as necessary.
        """
        lines = text.splitlines(True)
        if lines:
            if lines[-1].endswith('\n'):
                # If the text ends with a newline, add a blank line so a new
                # continuation prompt is produced.
                lines.append('')
            cursor.beginEditBlock()
            cursor.insertText(lines[0])
            for line in lines[1:]:
                if self._continuation_prompt_html is None:
                    cursor.insertText(self._continuation_prompt)
                else:
                    self._continuation_prompt = \
                        self._insert_html_fetching_plain_text(
                            cursor, self._continuation_prompt_html)
                cursor.insertText(line)
            cursor.endEditBlock()

    def _in_buffer(self, position):
        """
        Returns whether the specified position is inside the editing region.
        """
        return position == self._move_position_in_buffer(position)

    def _move_position_in_buffer(self, position):
        """
        Return the next position in buffer.
        """
        cursor = self._control.textCursor()
        cursor.setPosition(position)
        line = cursor.blockNumber()
        prompt_line = self._get_prompt_cursor().blockNumber()
        if line == prompt_line:
            if position >= self._prompt_pos:
                return position
            return self._prompt_pos
        if line > prompt_line:
            cursor.movePosition(QtGui.QTextCursor.StartOfBlock)
            prompt_pos = cursor.position() + len(self._continuation_prompt)
            if position >= prompt_pos:
                return position
            return prompt_pos
        return self._prompt_pos

    def _keep_cursor_in_buffer(self):
        """ Ensures that the cursor is inside the editing region. Returns
            whether the cursor was moved.
        """
        cursor = self._control.textCursor()
        endpos = cursor.selectionEnd()

        if endpos < self._prompt_pos:
            cursor.setPosition(endpos)
            line = cursor.blockNumber()
            prompt_line = self._get_prompt_cursor().blockNumber()
            if line == prompt_line:
                # Cursor is on prompt line, move to start of buffer
                cursor.setPosition(self._prompt_pos)
            else:
                # Cursor is not in buffer, move to the end
                cursor.movePosition(QtGui.QTextCursor.End)
            self._control.setTextCursor(cursor)
            return True

        startpos = cursor.selectionStart()

        new_endpos = self._move_position_in_buffer(endpos)
        new_startpos = self._move_position_in_buffer(startpos)
        if new_endpos == endpos and new_startpos == startpos:
            return False

        cursor.setPosition(new_startpos)
        cursor.setPosition(new_endpos, QtGui.QTextCursor.KeepAnchor)
        self._control.setTextCursor(cursor)
        return True

    def _keyboard_quit(self):
        """ Cancels the current editing task ala Ctrl-G in Emacs.
        """
        if self._temp_buffer_filled :
            self._cancel_completion()
            self._clear_temporary_buffer()
        else:
            self.input_buffer = ''

    def _page(self, text, html=False):
        """ Displays text using the pager if it exceeds the height of the
        viewport.

        Parameters
        ----------
        html : bool, optional (default False)
            If set, the text will be interpreted as HTML instead of plain text.
        """
        line_height = QtGui.QFontMetrics(self.font).height()
        minlines = self._control.viewport().height() / line_height
        if self.paging != 'none' and \
                re.match("(?:[^\n]*\n){%i}" % minlines, text):
            if self.paging == 'custom':
                self.custom_page_requested.emit(text)
            else:
                # disable buffer truncation during paging
                self._control.document().setMaximumBlockCount(0)
                self._page_control.clear()
                cursor = self._page_control.textCursor()
                if html:
                    self._insert_html(cursor, text)
                else:
                    self._insert_plain_text(cursor, text)
                self._page_control.moveCursor(QtGui.QTextCursor.Start)

                self._page_control.viewport().resize(self._control.size())
                if self._splitter:
                    self._page_control.show()
                    self._page_control.setFocus()
                else:
                    self.layout().setCurrentWidget(self._page_control)
        elif html:
            self._append_html(text)
        else:
            self._append_plain_text(text)

    def _set_paging(self, paging):
        """
        Change the pager to `paging` style.

        Parameters
        ----------
        paging : string
            Either "hsplit", "vsplit", or "inside"
        """
        if self._splitter is None:
            raise NotImplementedError("""can only switch if --paging=hsplit or
                    --paging=vsplit is used.""")
        if paging == 'hsplit':
            self._splitter.setOrientation(QtCore.Qt.Horizontal)
        elif paging == 'vsplit':
            self._splitter.setOrientation(QtCore.Qt.Vertical)
        elif paging == 'inside':
            raise NotImplementedError("""switching to 'inside' paging not
                    supported yet.""")
        else:
            raise ValueError("unknown paging method '%s'" % paging)
        self.paging = paging

    def _prompt_finished(self):
        """ Called immediately after a prompt is finished, i.e. when some input
            will be processed and a new prompt displayed.
        """
        self._control.setReadOnly(True)
        self._prompt_finished_hook()

    def _prompt_started(self):
        """ Called immediately after a new prompt is displayed.
        """
        # Temporarily disable the maximum block count to permit undo/redo and
        # to ensure that the prompt position does not change due to truncation.
        self._control.document().setMaximumBlockCount(0)
        self._control.setUndoRedoEnabled(True)

        # Work around bug in QPlainTextEdit: input method is not re-enabled
        # when read-only is disabled.
        self._control.setReadOnly(False)
        self._control.setAttribute(QtCore.Qt.WA_InputMethodEnabled, True)

        if not self._reading:
            self._executing = False
        self._prompt_started_hook()

        # If the input buffer has changed while executing, load it.
        if self._input_buffer_pending:
            self.input_buffer = self._input_buffer_pending
            self._input_buffer_pending = ''

        self._control.moveCursor(QtGui.QTextCursor.End)

    def _readline(self, prompt='', callback=None, password=False):
        """ Reads one line of input from the user.

        Parameters
        ----------
        prompt : str, optional
            The prompt to print before reading the line.

        callback : callable, optional
            A callback to execute with the read line. If not specified, input is
            read *synchronously* and this method does not return until it has
            been read.

        Returns
        -------
        If a callback is specified, returns nothing. Otherwise, returns the
        input string with the trailing newline stripped.
        """
        if self._reading:
            raise RuntimeError('Cannot read a line. Widget is already reading.')

        if not callback and not self.isVisible():
            # If the user cannot see the widget, this function cannot return.
            raise RuntimeError('Cannot synchronously read a line if the widget '
                               'is not visible!')

        self._reading = True
        if password:
            self._show_prompt('Warning: QtConsole does not support password mode, '
                              'the text you type will be visible.', newline=True)

        if 'ipdb' not in prompt.lower():
            # This is a prompt that asks for input from the user.
            self._show_prompt(prompt, newline=False, separator=False)
        else:
            self._show_prompt(prompt, newline=False)

        if callback is None:
            self._reading_callback = None
            while self._reading:
                QtCore.QCoreApplication.processEvents()
            return self._get_input_buffer(force=True).rstrip('\n')
        else:
            self._reading_callback = lambda: \
                callback(self._get_input_buffer(force=True).rstrip('\n'))

    def _set_continuation_prompt(self, prompt, html=False):
        """ Sets the continuation prompt.

        Parameters
        ----------
        prompt : str
            The prompt to show when more input is needed.

        html : bool, optional (default False)
            If set, the prompt will be inserted as formatted HTML. Otherwise,
            the prompt will be treated as plain text, though ANSI color codes
            will be handled.
        """
        if html:
            self._continuation_prompt_html = prompt
        else:
            self._continuation_prompt = prompt
            self._continuation_prompt_html = None

    def _set_cursor(self, cursor):
        """ Convenience method to set the current cursor.
        """
        self._control.setTextCursor(cursor)

    def _set_top_cursor(self, cursor):
        """ Scrolls the viewport so that the specified cursor is at the top.
        """
        scrollbar = self._control.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        original_cursor = self._control.textCursor()
        self._control.setTextCursor(cursor)
        self._control.ensureCursorVisible()
        self._control.setTextCursor(original_cursor)

    def _show_prompt(self, prompt=None, html=False, newline=True,
                     separator=True):
        """ Writes a new prompt at the end of the buffer.

        Parameters
        ----------
        prompt : str, optional
            The prompt to show. If not specified, the previous prompt is used.

        html : bool, optional (default False)
            Only relevant when a prompt is specified. If set, the prompt will
            be inserted as formatted HTML. Otherwise, the prompt will be treated
            as plain text, though ANSI color codes will be handled.

        newline : bool, optional (default True)
            If set, a new line will be written before showing the prompt if
            there is not already a newline at the end of the buffer.

        separator : bool, optional (default True)
            If set, a separator will be written before the prompt.
        """
        self._flush_pending_stream()

        # This is necessary to solve out-of-order insertion of mixed stdin and
        # stdout stream texts.
        # Fixes griffin-ide/griffin#17710
        if sys.platform == 'darwin':
            # Although this makes our tests hang on Mac, users confirmed that
            # it's needed on that platform too.
            # Fixes griffin-ide/griffin#19888
            if not os.environ.get('QTCONSOLE_TESTING'):
                QtCore.QCoreApplication.processEvents()
        else:
            QtCore.QCoreApplication.processEvents()

        cursor = self._get_end_cursor()

        # Save the current position to support _append*(before_prompt=True).
        # We can't leave the cursor at the end of the document though, because
        # that would cause any further additions to move the cursor. Therefore,
        # we move it back one place and move it forward again at the end of
        # this method. However, we only do this if the cursor isn't already
        # at the start of the text.
        if cursor.position() == 0:
            move_forward = False
        else:
            move_forward = True
            self._append_before_prompt_cursor.setPosition(cursor.position() - 1)

        # Insert a preliminary newline, if necessary.
        if newline and cursor.position() > 0:
            cursor.movePosition(QtGui.QTextCursor.Left,
                                QtGui.QTextCursor.KeepAnchor)
            if cursor.selection().toPlainText() != '\n':
                self._append_block()

        # Write the prompt.
        if separator:
            self._append_plain_text(self._prompt_sep)

        if prompt is None:
            if self._prompt_html is None:
                self._append_plain_text(self._prompt)
            else:
                self._append_html(self._prompt_html)
        else:
            if html:
                self._prompt = self._append_html_fetching_plain_text(prompt)
                self._prompt_html = prompt
            else:
                self._append_plain_text(prompt)
                self._prompt = prompt
                self._prompt_html = None

        self._flush_pending_stream()
        self._prompt_cursor.setPosition(self._get_end_pos() - 1)

        if move_forward:
            self._append_before_prompt_cursor.setPosition(
                self._append_before_prompt_cursor.position() + 1)
        else:
            # cursor position was 0, set before prompt cursor
            self._append_before_prompt_cursor.setPosition(0)
        self._prompt_started()

    #------ Signal handlers ----------------------------------------------------

    def _adjust_scrollbars(self):
        """ Expands the vertical scrollbar beyond the range set by Qt.
        """
        # This code is adapted from _q_adjustScrollbars in qplaintextedit.cpp
        # and qtextedit.cpp.
        document = self._control.document()
        scrollbar = self._control.verticalScrollBar()
        viewport_height = self._control.viewport().height()
        if isinstance(self._control, QtWidgets.QPlainTextEdit):
            maximum = max(0, document.lineCount() - 1)
            step = viewport_height / self._control.fontMetrics().lineSpacing()
        else:
            # QTextEdit does not do line-based layout and blocks will not in
            # general have the same height. Therefore it does not make sense to
            # attempt to scroll in line height increments.
            maximum = document.size().height()
            step = viewport_height
        diff = maximum - scrollbar.maximum()
        scrollbar.setRange(0, round(maximum))
        scrollbar.setPageStep(round(step))

        # Compensate for undesirable scrolling that occurs automatically due to
        # maximumBlockCount() text truncation.
        if diff < 0 and document.blockCount() == document.maximumBlockCount():
            scrollbar.setValue(round(scrollbar.value() + diff))

    def _custom_context_menu_requested(self, pos):
        """ Shows a context menu at the given QPoint (in widget coordinates).
        """
        menu = self._context_menu_make(pos)
        menu.exec_(self._control.mapToGlobal(pos))
