# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
#

"""
Tests for EditorStack keyboard shortcuts.
"""

# Standard library imports
import os
import sys
from unittest.mock import Mock

# Third party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication

# Local imports
from griffin.config.base import running_in_ci
from griffin.config.manager import CONF
from griffin.plugins.editor.widgets.gotoline import GoToLineDialog
from griffin.plugins.editor.widgets.editorstack import EditorStack


# ---- Qt Test Fixtures
@pytest.fixture
def editorstack(qtbot):
    """
    Set up EditorStack with CodeEditors containing some Python code.
    The cursor is at the empty line below the code.
    """
    editorstack = EditorStack(None, [], False)
    editorstack.set_find_widget(Mock())
    editorstack.set_io_actions(Mock(), Mock(), Mock(), Mock())
    editorstack.close_split_action.setEnabled(False)
    editorstack.new('foo.py', 'utf-8', 'Line1\nLine2\nLine3\nLine4')

    qtbot.addWidget(editorstack)
    editorstack.show()
    editorstack.go_to_line(1)

    # We need to wait for a bit so shortcuts are registered correctly
    qtbot.wait(300)

    return editorstack


# ---- Tests
def test_default_keybinding_values():
    """
    Assert that the default Griffin keybindings for the keyboard shortcuts
    are as expected. This is required because we do not use the keybindings
    saved in Griffin's config to simulate the user keyboard action, due to
    the fact that it is complicated to convert and pass reliably a sequence
    of key strings to qtbot.keyClicks.
    """
    # Assert default keybindings.
    assert CONF.get_shortcut('editor', 'start of document') == 'Ctrl+Home'
    assert CONF.get_shortcut('editor', 'end of document') == 'Ctrl+End'
    assert CONF.get_shortcut('editor', 'delete') == 'Del'
    assert CONF.get_shortcut('editor', 'undo') == 'Ctrl+Z'
    assert CONF.get_shortcut('editor', 'redo') == 'Ctrl+Shift+Z'
    assert CONF.get_shortcut('editor', 'copy') == 'Ctrl+C'
    assert CONF.get_shortcut('editor', 'paste') == 'Ctrl+V'
    assert CONF.get_shortcut('editor', 'cut') == 'Ctrl+X'
    assert CONF.get_shortcut('editor', 'select all') == 'Ctrl+A'
    assert CONF.get_shortcut('editor', 'delete line') == 'Ctrl+D'
    assert CONF.get_shortcut('editor', 'transform to lowercase') == 'Ctrl+U'
    assert CONF.get_shortcut('editor',
                             'transform to uppercase') == 'Ctrl+Shift+U'
    assert CONF.get_shortcut('editor', 'go to line') == 'Ctrl+L'
    assert CONF.get_shortcut('editor', 'next word') == 'Ctrl+Right'
    assert CONF.get_shortcut('editor', 'previous word') == 'Ctrl+Left'


@pytest.mark.skipif(
    sys.platform.startswith('linux') and running_in_ci(),
    reason="It fails on Linux due to the lack of a proper X server.")
def test_start_and_end_of_document_shortcuts(editorstack, qtbot):
    """
    Test that the start of document and end of document shortcut are working
    as expected.
    """
    editor = editorstack.get_current_editor()

    # Assert initial state.
    assert editor.get_cursor_line_column() == (0, 0)

    # Go to the end of the document.
    qtbot.keyClick(editor, Qt.Key_End, modifier=Qt.ControlModifier)
    assert editor.get_cursor_line_column() == (4, 0)

    # Go to the start of the document.
    qtbot.keyClick(editor, Qt.Key_Home, modifier=Qt.ControlModifier)
    assert editor.get_cursor_line_column() == (0, 0)


@pytest.mark.skipif(
    sys.platform.startswith('linux') and running_in_ci(),
    reason="It fails on Linux due to the lack of a proper X server.")
def test_del_undo_redo_shortcuts(editorstack, qtbot):
    """
    Test that the undo and redo keyboard shortcuts are working as expected
    with the default Griffin keybindings.

    Regression test for griffin-ide/griffin#7743.
    """
    editor = editorstack.get_current_editor()

    # Delete the first character of the first line.
    qtbot.keyClick(editor, Qt.Key_Delete)
    assert editor.toPlainText() == 'ine1\nLine2\nLine3\nLine4\n'

    # Undo the last action with Ctrl+Z.
    qtbot.keyClick(editor, Qt.Key_Z, modifier=Qt.ControlModifier)
    assert editor.toPlainText() == 'Line1\nLine2\nLine3\nLine4\n'

    # Redo the last action with Ctrl+Shift+Z .
    qtbot.keyClick(editor, Qt.Key_Z,
                   modifier=Qt.ControlModifier | Qt.ShiftModifier)
    assert editor.toPlainText() == 'ine1\nLine2\nLine3\nLine4\n'

    # Undo the last action again with Ctrl+Z.
    qtbot.keyClick(editor, Qt.Key_Z, modifier=Qt.ControlModifier)
    assert editor.toPlainText() == 'Line1\nLine2\nLine3\nLine4\n'


@pytest.mark.skipif(
    sys.platform.startswith('linux') and running_in_ci(),
    reason="It fails on Linux due to the lack of a proper X server.")
def test_copy_cut_paste_shortcuts(editorstack, qtbot):
    """
    Test that the copy, cut, and paste keyboard shortcuts are working as
    expected with the default Griffin keybindings.
    """
    editor = editorstack.get_current_editor()
    QApplication.clipboard().clear()

    # Select and Copy the first line in the editor.
    qtbot.keyClick(editor, Qt.Key_End, modifier=Qt.ShiftModifier)
    assert editor.get_selected_text() == 'Line1'

    qtbot.keyClick(editor, Qt.Key_C, modifier=Qt.ControlModifier)
    assert QApplication.clipboard().text() == 'Line1'

    # Paste the selected text.
    qtbot.keyClick(editor, Qt.Key_Home)
    qtbot.keyClick(editor, Qt.Key_V, modifier=Qt.ControlModifier)
    assert editor.toPlainText() == 'Line1Line1\nLine2\nLine3\nLine4\n'

    # Select and Cut the first line in the editor.
    qtbot.keyClick(editor, Qt.Key_Home)
    qtbot.keyClick(editor, Qt.Key_End, modifier=Qt.ShiftModifier)
    assert editor.get_selected_text() == 'Line1Line1'

    qtbot.keyClick(editor, Qt.Key_X, modifier=Qt.ControlModifier)
    assert QApplication.clipboard().text() == 'Line1Line1'
    assert editor.toPlainText() == '\nLine2\nLine3\nLine4\n'


@pytest.mark.skipif(
    sys.platform.startswith('linux') and running_in_ci(),
    reason="It fails on Linux due to the lack of a proper X server.")
def test_select_all_shortcut(editorstack, qtbot):
    """
    Test that the select all keyboard shortcut is working as
    expected with the default Griffin keybindings.
    """
    editor = editorstack.get_current_editor()

    # Select all the text in the editor.
    qtbot.keyClick(editor, Qt.Key_A, modifier=Qt.ControlModifier)
    assert editor.get_selected_text() == 'Line1\nLine2\nLine3\nLine4\n'


@pytest.mark.skipif(
    sys.platform.startswith('linux') and running_in_ci(),
    reason="It fails on Linux due to the lack of a proper X server.")
@pytest.mark.no_xvfb
def test_delete_line_shortcut(editorstack, qtbot):
    """
    Test that the delete line keyboard shortcut is working as
    expected with the default Griffin keybindings.
    """
    editor = editorstack.get_current_editor()

    # Delete the second line in the editor.
    editor.go_to_line(2)
    qtbot.keyClick(editor, Qt.Key_D, modifier=Qt.ControlModifier)
    assert editor.toPlainText() == 'Line1\nLine3\nLine4\n'


@pytest.mark.skipif(
    sys.platform.startswith('linux') and running_in_ci(),
    reason="It fails on Linux due to the lack of a proper X server.")
@pytest.mark.no_xvfb
def test_go_to_line_shortcut(editorstack, qtbot, mocker):
    """
    Test that the go to line keyboard shortcut is working
    as expected with the default Griffin keybindings.
    """
    editor = editorstack.get_current_editor()
    qtbot.keyClick(editor, Qt.Key_Home, modifier=Qt.ControlModifier)

    # Go to line 3.
    mocker.patch.object(GoToLineDialog, 'exec_', return_value=True)
    mocker.patch.object(GoToLineDialog, 'get_line_number', return_value=3)
    qtbot.keyClick(editor, Qt.Key_L, modifier=Qt.ControlModifier)
    assert editor.get_cursor_line_column() == (2, 0)


@pytest.mark.skipif(
    sys.platform.startswith('linux') and running_in_ci(),
    reason="It fails on Linux due to the lack of a proper X server.")
@pytest.mark.no_xvfb
def test_transform_to_lowercase_shortcut(editorstack, qtbot):
    """
    Test that the transform to lowercase shorcut is working as expected with
    the default Griffin keybindings.
    """
    editor = editorstack.get_current_editor()

    # Transform all the text to lowercase.
    qtbot.keyClick(editor, Qt.Key_A, modifier=Qt.ControlModifier)
    qtbot.keyClick(editor, Qt.Key_U, modifier=Qt.ControlModifier)
    assert editor.toPlainText() == 'line1\nline2\nline3\nline4\n'


@pytest.mark.skipif(
    sys.platform.startswith('linux') and running_in_ci(),
    reason="It fails on Linux due to the lack of a proper X server.")
@pytest.mark.no_xvfb
def test_transform_to_uppercase_shortcut(editorstack, qtbot):
    """
    Test that the transform to uppercase shortcuts is working as expected with
    the default Griffin keybindings.
    """
    editor = editorstack.get_current_editor()

    # Transform all the text to uppercase.
    qtbot.keyClick(editor, Qt.Key_A, modifier=Qt.ControlModifier)
    qtbot.keyClick(editor, Qt.Key_U,
                   modifier=Qt.ControlModifier | Qt.ShiftModifier)
    assert editor.toPlainText() == 'LINE1\nLINE2\nLINE3\nLINE4\n'


@pytest.mark.skipif(
    sys.platform.startswith('linux') and running_in_ci(),
    reason="It fails on Linux due to the lack of a proper X server.")
@pytest.mark.no_xvfb
def test_next_and_previous_word_shortcuts(editorstack, qtbot):
    """
    Test that the next word and previous word shortcuts are working as
    expected with the default Griffin keybindings.
    """
    editor = editorstack.get_current_editor()

    # Go to the next word 3 times.
    assert editor.get_cursor_line_column() == (0, 0)
    qtbot.keyClick(editor, Qt.Key_Right, modifier=Qt.ControlModifier)
    assert editor.get_cursor_line_column() == (0, 5)
    qtbot.keyClick(editor, Qt.Key_Right, modifier=Qt.ControlModifier)
    assert editor.get_cursor_line_column() == (1, 0)
    qtbot.keyClick(editor, Qt.Key_Right, modifier=Qt.ControlModifier)
    assert editor.get_cursor_line_column() == (1, 5)

    # Go to the previous word 3 times.
    qtbot.keyClick(editor, Qt.Key_Left, modifier=Qt.ControlModifier)
    assert editor.get_cursor_line_column() == (1, 0)
    qtbot.keyClick(editor, Qt.Key_Left, modifier=Qt.ControlModifier)
    assert editor.get_cursor_line_column() == (0, 5)
    qtbot.keyClick(editor, Qt.Key_Left, modifier=Qt.ControlModifier)
    assert editor.get_cursor_line_column() == (0, 0)


@pytest.mark.skipif(sys.platform == 'darwin', reason="Not valid in macOS")
def test_builtin_shift_del_and_ins(editorstack, qtbot):
    """
    Test that the builtin key sequences Ctrl+Ins, Shit+Del and Shift+Ins result
    in copy, cut and paste actions in Windows and Linux.

    Regression test for griffin-ide/griffin#5035, griffin-ide/griffin#4947, and
    griffin-ide/griffin#5973.
    """
    editor = editorstack.get_current_editor()
    QApplication.clipboard().clear()

    # Select the first line of the editor.
    qtbot.keyClick(editor, Qt.Key_End, modifier=Qt.ShiftModifier)
    assert editor.get_selected_text() == 'Line1'

    # Copy the selection with Ctrl+Ins.
    qtbot.keyClick(editor, Qt.Key_Insert, modifier=Qt.ControlModifier)
    assert QApplication.clipboard().text() == 'Line1'

    # Paste the copied text at the end of the line with Shift+Ins.
    qtbot.keyClick(editor, Qt.Key_End)
    qtbot.keyClick(editor, Qt.Key_Insert, modifier=Qt.ShiftModifier)
    assert editor.toPlainText() == 'Line1Line1\nLine2\nLine3\nLine4\n'

    # Select the second line in the editor again.
    qtbot.keyClick(editor, Qt.Key_Home, modifier=Qt.ShiftModifier)
    assert editor.get_selected_text() == 'Line1Line1'

    # Cut the selection with Shift+Del.
    qtbot.keyClick(editor, Qt.Key_Delete, modifier=Qt.ShiftModifier)
    assert QApplication.clipboard().text() == 'Line1Line1'
    assert editor.toPlainText() == '\nLine2\nLine3\nLine4\n'


@pytest.mark.skipif(os.name != 'nt', reason='Only valid in Windows system')
def test_builtin_undo_redo(editorstack, qtbot):
    """
    Test that the builtin key sequence Alt+Backspace, Ctrl+Y and
    Alt+Shift+Backspace result in, respectively, an undo, redo and redo action
    in Windows.
    """
    editor = editorstack.get_current_editor()

    # Write something on a new line.
    qtbot.keyClicks(editor, 'Something')
    qtbot.keyClick(editor, Qt.Key_Return)
    assert editor.toPlainText() == 'Something\nLine1\nLine2\nLine3\nLine4\n'

    # Undo the last action with Alt+Backspace.
    qtbot.keyClick(editor, Qt.Key_Backspace, modifier=Qt.AltModifier)
    assert editor.toPlainText() == 'SomethingLine1\nLine2\nLine3\nLine4\n'

    # Undo the second to last action with Alt+Backspace.
    qtbot.keyClick(editor, Qt.Key_Backspace, modifier=Qt.AltModifier)
    assert editor.toPlainText() == 'Line1\nLine2\nLine3\nLine4\n'

    # Redo the second to last action with Alt+Shift+Backspace.
    qtbot.keyClick(editor, Qt.Key_Backspace,
                   modifier=Qt.AltModifier | Qt.ShiftModifier)
    assert editor.toPlainText() == 'SomethingLine1\nLine2\nLine3\nLine4\n'

    # Redo the last action with Ctrl+Y.
    qtbot.keyClick(editor, Qt.Key_Y, modifier=Qt.ControlModifier)
    assert editor.toPlainText() == 'Something\nLine1\nLine2\nLine3\nLine4\n'


@pytest.mark.skipif(
    sys.platform.startswith("linux") and running_in_ci(),
    reason='Fails on Linux and CI'
)
def test_shortcuts_for_new_editors(editorstack, qtbot):
    """
    Test that widget shortcuts are working for new editors.

    This is a regression test for griffin-ide/griffin#23151.
    """
    # Create new file and give it focus
    editorstack.new('bar.py', 'utf-8', 'Line5\nLine6\nLine7\nLine8')
    editorstack.tabs.setCurrentIndex(1)

    # Go to its first line, click the shortcut to comment it and check it was
    editorstack.go_to_line(1)
    editor = editorstack.get_current_editor()
    qtbot.keyClick(editor, Qt.Key_1, modifier=Qt.ControlModifier)
    assert editor.toPlainText() == '# Line5\nLine6\nLine7\nLine8\n'


if __name__ == "__main__":
    import os
    pytest.main(['-x', os.path.basename(__file__), '-vv', '-rw'])
