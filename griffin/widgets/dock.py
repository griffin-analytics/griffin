# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""
Dock widgets for plugins
"""

import qstylizer.style
from qtpy.QtCore import QEvent, QObject, Qt, QSize, Signal
from qtpy.QtWidgets import (QDockWidget, QHBoxLayout, QSizePolicy, QTabBar,
                            QToolButton, QWidget)

from griffin.api.translations import _
from griffin.api.config.mixins import GriffinConfigurationAccessor
from griffin.utils.icon_manager import ima
from griffin.utils.palette import GriffinPalette
from griffin.utils.stylesheet import (
    PanesToolbarStyleSheet, HORIZONTAL_DOCK_TABBAR_STYLESHEET,
    VERTICAL_DOCK_TABBAR_STYLESHEET)


# =============================================================================
# Tab filter
# =============================================================================
class TabFilter(QObject, GriffinConfigurationAccessor):
    """Filter event attached to each DockWidget QTabBar."""

    CONF_SECTION = 'main'

    def __init__(self, dock_tabbar, main):
        QObject.__init__(self)
        self.dock_tabbar: QTabBar = dock_tabbar
        self.main = main
        self.from_index = None

        self._set_tabbar_stylesheet()
        self.dock_tabbar.setElideMode(Qt.ElideNone)
        self.dock_tabbar.setUsesScrollButtons(True)

    def eventFilter(self, obj, event):
        """Filter mouse press events.

        Events that are captured and not propagated return True. Events that
        are not captured and are propagated return False.
        """
        event_type = event.type()
        if event_type == QEvent.MouseButtonPress:
            self.tab_pressed(event)
            return False
        return False

    def tab_pressed(self, event):
        """Method called when a tab from a QTabBar has been pressed."""
        self.from_index = self.dock_tabbar.tabAt(event.pos())
        self.dock_tabbar.setCurrentIndex(self.from_index)

        try:
            if event.button() == Qt.RightButton:
                if self.from_index == -1:
                    self.show_nontab_menu(event)
                else:
                    self.show_tab_menu(event)
        except AttributeError:
            # Needed to avoid an error when generating the
            # context menu on top of the tab.
            # See griffin-ide/griffin#11226
            pass

    def show_tab_menu(self, event):
        """Show the context menu assigned to tabs."""
        self.show_nontab_menu(event)

    def show_nontab_menu(self, event):
        """Show the context menu assigned to nontabs section."""
        menu = self.main.createPopupMenu()
        menu.exec_(self.dock_tabbar.mapToGlobal(event.pos()))

    def _set_tabbar_stylesheet(self):
        if self.get_conf('vertical_tabs'):
            self.dock_tabbar.setStyleSheet(
                str(VERTICAL_DOCK_TABBAR_STYLESHEET))
        else:
            self.dock_tabbar.setStyleSheet(
                str(HORIZONTAL_DOCK_TABBAR_STYLESHEET))


# =============================================================================
# Title bar
# =============================================================================
class DragButton(QToolButton):
    """
    Drag button for the title bar.

    This button pass all its mouse events to its parent.
    """

    def __init__(self, parent, button_size):
        super().__init__(parent)
        self.parent = parent

        # Style
        self.setIconSize(button_size)
        self.setAutoRaise(True)
        self.setIcon(ima.icon('drag_dock_widget'))
        self.setToolTip(_("Drag and drop pane to a different position"))
        self.setStyleSheet(self._stylesheet)

    def mouseReleaseEvent(self, event):
        self.parent.mouseReleaseEvent(event)

    def mousePressEvent(self, event):
        self.parent.mousePressEvent(event)

    @property
    def _stylesheet(self):
        css = qstylizer.style.StyleSheet()
        css.QToolButton.setValues(
            borderRadius='0px',
            border='0px'
        )
        return css.toString()


class CloseButton(QToolButton):
    """Close button for the title bar."""

    def __init__(self, parent, button_size):
        super().__init__(parent)
        self.parent = parent

        # Style
        self.setIconSize(button_size)
        self.setAutoRaise(True)
        self.setIcon(ima.icon('lock_open'))
        self.setToolTip(_("Lock pane"))
        self._apply_stylesheet(GriffinPalette.COLOR_BACKGROUND_3, 0)

    def _apply_stylesheet(self, bgcolor, bradius):
        css = qstylizer.style.StyleSheet()
        css.QToolButton.setValues(
            width=PanesToolbarStyleSheet.BUTTON_WIDTH,
            borderRadius=f'{bradius}px',
            border='0px',
            backgroundColor=bgcolor,
        )

        self.setStyleSheet(css.toString())

    def enterEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        self._apply_stylesheet(GriffinPalette.COLOR_BACKGROUND_5, 3)
        self.parent._apply_stylesheet(GriffinPalette.COLOR_BACKGROUND_3)
        self.setIcon(ima.icon('lock'))
        super().enterEvent(event)

    def mousePressEvent(self, event):
        self._apply_stylesheet(GriffinPalette.COLOR_BACKGROUND_6, 3)
        super().mousePressEvent(event)

    def leaveEvent(self, event):
        self._apply_stylesheet(GriffinPalette.COLOR_BACKGROUND_3, 0)
        self.parent._apply_stylesheet(GriffinPalette.COLOR_BACKGROUND_5)
        self.setIcon(ima.icon('lock_open'))
        super().leaveEvent(event)


class DockTitleBar(QWidget):
    """
    Custom title bar for our dock widgets.

    Inspired from
    https://stackoverflow.com/a/40894225/438386
    """

    def __init__(self, parent):
        super(DockTitleBar, self).__init__(parent)

        button_size = QSize(20, 20)

        drag_button = DragButton(self, button_size)

        left_spacer = QWidget(self)
        left_spacer.setToolTip(drag_button.toolTip())
        left_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        right_spacer = QWidget(self)
        right_spacer.setToolTip(drag_button.toolTip())
        right_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        close_button = CloseButton(self, button_size)
        close_button.clicked.connect(parent.remove_title_bar)

        hlayout = QHBoxLayout(self)
        hlayout.setSpacing(0)
        hlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.addWidget(left_spacer)
        hlayout.addWidget(drag_button)
        hlayout.addWidget(right_spacer)
        hlayout.addWidget(close_button)

        self._apply_stylesheet(GriffinPalette.COLOR_BACKGROUND_3)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        self._apply_stylesheet(GriffinPalette.COLOR_BACKGROUND_5)
        QWidget.mouseReleaseEvent(self, event)

    def mousePressEvent(self, event):
        self.setCursor(Qt.ClosedHandCursor)
        self._apply_stylesheet(GriffinPalette.COLOR_BACKGROUND_6)
        QWidget.mousePressEvent(self, event)

    def enterEvent(self, event):
        # To signal that dock widgets can be dragged from here
        self.setCursor(Qt.OpenHandCursor)
        self._apply_stylesheet(GriffinPalette.COLOR_BACKGROUND_5)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Remove customizations when leaving widget."""
        self.unsetCursor()
        self._apply_stylesheet(GriffinPalette.COLOR_BACKGROUND_3)
        super().leaveEvent(event)

    def _apply_stylesheet(self, bgcolor):
        css = qstylizer.style.StyleSheet()
        css.QWidget.setValues(
            height=PanesToolbarStyleSheet.BUTTON_HEIGHT,
            backgroundColor=bgcolor
        )
        self.setStyleSheet(css.toString())


class GriffinDockWidget(QDockWidget):
    """Subclass to override needed methods"""

    # Attributes
    ALLOWED_AREAS = Qt.AllDockWidgetAreas
    LOCATION = Qt.LeftDockWidgetArea
    FEATURES = QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable

    # Signals
    sig_plugin_closed = Signal()
    sig_title_bar_shown = Signal(bool)

    def __init__(self, title, parent):
        super().__init__(title, parent)

        # Attributes
        self.title = title
        self.is_shown = False

        # Set features
        self.setFeatures(self.FEATURES)

        # Widgets
        self.main = parent
        self.empty_titlebar = QWidget(self)
        self.titlebar = DockTitleBar(self)
        self.dock_tabbar = None  # Needed for event filter

        # Layout
        # Prevent message on internal console
        # See: https://bugreports.qt.io/browse/QTBUG-42986
        layout = QHBoxLayout(self.empty_titlebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.empty_titlebar.setLayout(layout)
        self.empty_titlebar.setMinimumSize(0, 0)
        self.empty_titlebar.setMaximumSize(0, 0)

        # Setup
        self.set_title_bar()
        self.remove_title_bar()

        # Signals
        # This installs the tab filter when dockwidgets are undocked and then
        # docked to a new location.
        self.dockLocationChanged.connect(
            lambda area: self.install_tab_event_filter()
        )

    def closeEvent(self, event):
        """Send a signal on close so that the "Panes" menu can be updated."""
        self.sig_plugin_closed.emit()

    def install_tab_event_filter(self):
        """
        Install an event filter to capture mouse events in the tabs of a
        QTabBar holding tabified dockwidgets.
        """
        # Avoid to run this before the dockwidget is visible
        if not self.is_shown:
            return

        dock_tabbar = None

        # This is necessary to catch an error when closing the app on macOS
        # with PyQt 5.15
        try:
            tabbars = self.main.findChildren(QTabBar)
        except RuntimeError:
            tabbars = []

        for tabbar in tabbars:
            for tab in range(tabbar.count()):
                title = tabbar.tabText(tab)
                if title == self.title:
                    dock_tabbar = tabbar
                    break

        if dock_tabbar is not None:
            self.dock_tabbar = dock_tabbar
            # Install filter only once per QTabBar
            if getattr(self.dock_tabbar, 'filter', None) is None:
                self.dock_tabbar.filter = TabFilter(self.dock_tabbar,
                                                    self.main)
                self.dock_tabbar.installEventFilter(self.dock_tabbar.filter)

    def remove_title_bar(self):
        """Set empty qwidget on title bar."""
        self.sig_title_bar_shown.emit(False)
        self.setTitleBarWidget(self.empty_titlebar)

    def set_title_bar(self):
        """Set custom title bar."""
        self.sig_title_bar_shown.emit(True)
        self.setTitleBarWidget(self.titlebar)
