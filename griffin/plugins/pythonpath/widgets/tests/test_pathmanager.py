# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
#

"""
Tests for pathmanager.py
"""
# Standard library imports
from collections import OrderedDict
import sys
import os

# Test library imports
import pytest
from qtpy.QtCore import Qt, QTimer
from qtpy.QtWidgets import QMessageBox, QPushButton

# Local imports
from griffin.utils.environ import get_user_env, set_user_env
from griffin.utils.programs import is_module_installed
from griffin.utils.tests.conftest import restore_user_env
from griffin.plugins.pythonpath.utils import check_path
from griffin.plugins.pythonpath.widgets import pathmanager as pathmanager_mod


@pytest.fixture
def pathmanager(qtbot, request):
    """Set up PathManager."""
    user_paths, project_path, system_paths = request.param

    widget = pathmanager_mod.PathManager(None)
    widget.update_paths(
        user_paths=OrderedDict({p: True for p in user_paths}),
        project_path=OrderedDict({p: True for p in project_path}),
        system_paths=OrderedDict({p: True for p in system_paths}),
        prioritize=False
    )
    widget.show()
    qtbot.addWidget(widget)
    return widget


@pytest.mark.parametrize(
    'pathmanager', [(sys.path[:-10], sys.path[-10:], ())], indirect=True
)
def test_pathmanager(qtbot, pathmanager):
    """Run PathManager test"""
    pathmanager.show()
    assert pathmanager


@pytest.mark.parametrize('pathmanager', [((), (), ())], indirect=True)
def test_import_PYTHONPATH(qtbot, pathmanager, tmp_path, restore_user_env):
    """
    Test that PYTHONPATH is imported.
    """

    # Add a directory to PYTHONPATH environment variable
    sys_dir = tmp_path / 'sys_dir'
    sys_dir.mkdir()
    set_user_env({"PYTHONPATH": str(sys_dir)})

    # Open Pythonpath dialog
    pathmanager.show()
    qtbot.wait(500)

    assert len(pathmanager.headers) == 0
    assert pathmanager.get_system_paths() == OrderedDict()

    # Import PYTHONPATH from environment
    pathmanager.import_pythonpath()
    assert len(pathmanager.headers) == 1

    assert pathmanager.get_system_paths() == OrderedDict({str(sys_dir): True})


@pytest.mark.parametrize(
    'pathmanager', [(sys.path[:-10], sys.path[-10:], ())], indirect=True
)
def test_check_uncheck_path(pathmanager):
    """
    Test that checking and unchecking a path in the PathManager correctly
    update the not active path list.
    """
    # Assert that all paths are checked.
    for row in range(1, pathmanager.listwidget.count()):
        item = pathmanager.listwidget.item(row)
        if item not in pathmanager.headers:
            assert item.checkState() == Qt.Checked


@pytest.mark.skipif(
    os.name != 'nt' or not is_module_installed('win32con'),
    reason=("This feature is not applicable for Unix "
            "systems and pywin32 is needed")
)
@pytest.mark.parametrize(
    'pathmanager', [(['p1', 'p2', 'p3'], ['p4', 'p5', 'p6'], [])],
    indirect=True
)
def test_export_to_PYTHONPATH(pathmanager, mocker, restore_user_env):

    # Mock the dialog window and answer "Yes" to clear contents of PYTHONPATH
    # before adding Griffin's path list
    mocker.patch.object(pathmanager_mod.QMessageBox, 'question',
                        return_value=pathmanager_mod.QMessageBox.Yes)

    # Assert that PYTHONPATH is synchronized correctly with Griffin's path list
    pathmanager.export_pythonpath()
    expected_pathlist = ['p1', 'p2', 'p3']
    env = get_user_env()
    assert env['PYTHONPATH'] == expected_pathlist

    # Uncheck 'path2' and assert that it is removed from PYTHONPATH when it
    # is synchronized with Griffin's path list
    pathmanager.listwidget.item(6).setCheckState(Qt.Unchecked)
    pathmanager.export_pythonpath()
    expected_pathlist = ['p1', 'p3']
    env = get_user_env()
    assert env['PYTHONPATH'] == expected_pathlist

    # Mock the dialog window and answer "No" to clear contents of PYTHONPATH
    # before adding Griffin's path list
    mocker.patch.object(pathmanager_mod.QMessageBox, 'question',
                        return_value=pathmanager_mod.QMessageBox.No)

    # Uncheck 'path3' and assert that it is kept in PYTHONPATH when it
    # is synchronized with Griffin's path list
    pathmanager.listwidget.item(6).setCheckState(Qt.Unchecked)
    pathmanager.export_pythonpath()
    expected_pathlist = ['p3', 'p1']
    env = get_user_env()
    assert env['PYTHONPATH'] == expected_pathlist


@pytest.mark.parametrize(
    'pathmanager', [(sys.path[:-10], sys.path[-10:], ())], indirect=True
)
def test_invalid_directories(qtbot, pathmanager):
    """Check [site/dist]-packages are invalid paths."""
    if os.name == 'nt':
        paths = ['/lib/site-packages/foo',
                 '/lib/dist-packages/foo']
    else:
        paths = ['/lib/python3.6/site-packages/foo',
                 '/lib/python3.6/dist-packages/foo']

    def interact_message_box():
        child = pathmanager.findChild(QMessageBox)
        qtbot.keyPress(child, Qt.Key_Enter)

    for path in paths:
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(interact_message_box)
        timer.start(300)
        assert not check_path(path)
        pathmanager.add_path(path)


@pytest.mark.parametrize(
    'pathmanager', [(('/spam', '/bar'), ('/foo', ), ())], indirect=True
)
def test_remove_item_and_reply_no(qtbot, pathmanager):
    """Check that the item is not removed after answering 'No'."""
    pathmanager.show()
    count = pathmanager.count()

    def interact_message_box():
        messagebox = pathmanager.findChild(QMessageBox)
        buttons = messagebox.findChildren(QPushButton)
        for button in buttons:
            if 'no' in button.text().lower():
                qtbot.mouseClick(button, Qt.LeftButton)
                break

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(interact_message_box)
    timer.start(100)
    qtbot.mouseClick(pathmanager.remove_button, Qt.LeftButton)

    # Back to main thread
    assert pathmanager.count() == count


@pytest.mark.parametrize(
    'pathmanager', [(('/spam', '/bar'), ('/foo', ), ())], indirect=True
)
def test_remove_item_and_reply_yes(qtbot, pathmanager):
    """Check that the item is indeed removed after answering 'Yes'."""
    pathmanager.show()
    count = pathmanager.count()

    def interact_message_box():
        messagebox = pathmanager.findChild(QMessageBox)
        buttons = messagebox.findChildren(QPushButton)
        for button in buttons:
            if 'yes' in button.text().lower():
                qtbot.mouseClick(button, Qt.LeftButton)
                break

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(interact_message_box)
    timer.start(100)
    pathmanager.listwidget.setCurrentRow(4)
    qtbot.mouseClick(pathmanager.remove_button, Qt.LeftButton)

    # Back to main thread
    assert pathmanager.count() == (count - 1)


@pytest.mark.parametrize('pathmanager', [((), (), ())], indirect=True)
def test_add_repeated_item(qtbot, pathmanager, tmpdir):
    """
    Check behavior when an unchecked item that is already on the list is added.
    The checkbox should then be checked and if replying 'yes' to the question,
    then the item should be moved to the top.
    """
    pathmanager.show()
    dir1 = str(tmpdir.mkdir("foo"))
    dir2 = str(tmpdir.mkdir("bar"))
    dir3 = str(tmpdir.mkdir("spam"))
    pathmanager.add_path(dir1)
    pathmanager.add_path(dir2)
    pathmanager.add_path(dir3)
    pathmanager.set_row_check_state(2, Qt.Unchecked)
    assert not all(pathmanager.get_user_paths().values())

    def interact_message_box():
        messagebox = pathmanager.findChild(QMessageBox)
        buttons = messagebox.findChildren(QPushButton)
        for button in buttons:
            if 'yes' in button.text().lower():
                qtbot.mouseClick(button, Qt.LeftButton)
                break

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(interact_message_box)
    timer.start(500)
    pathmanager.add_path(dir2)
    print(pathmanager.get_user_paths())

    # Back to main thread
    assert pathmanager.count() == 4
    assert list(pathmanager.get_user_paths().keys())[0] == dir2
    assert all(pathmanager.get_user_paths().values())


@pytest.mark.parametrize(
    'pathmanager', [(('/spam', '/bar'), ('/foo', ), ())], indirect=True
)
def test_buttons_state(qtbot, pathmanager, tmpdir):
    """Check buttons are enabled/disabled based on items and position."""
    pathmanager.show()

    # Default row is header so almost all buttons should be disabled
    assert not pathmanager.button_ok.isEnabled()
    assert not pathmanager.movetop_button.isEnabled()
    assert not pathmanager.moveup_button.isEnabled()
    assert not pathmanager.movebottom_button.isEnabled()
    assert not pathmanager.movedown_button.isEnabled()
    assert not pathmanager.remove_button.isEnabled()
    assert pathmanager.add_button.isEnabled()

    # First editable path
    pathmanager.set_current_row(3)
    assert not pathmanager.button_ok.isEnabled()
    assert not pathmanager.movetop_button.isEnabled()
    assert not pathmanager.moveup_button.isEnabled()
    assert pathmanager.movebottom_button.isEnabled()
    assert pathmanager.movedown_button.isEnabled()
    assert pathmanager.remove_button.isEnabled()
    assert pathmanager.add_button.isEnabled()

    # Check adding a path updates the right buttons
    path = tmpdir.mkdir("bloop")
    pathmanager.add_path(str(path))
    assert pathmanager.button_ok.isEnabled()
    assert not pathmanager.movetop_button.isEnabled()
    assert not pathmanager.moveup_button.isEnabled()

    # Check bottom state
    pathmanager.movebottom_button.animateClick()
    qtbot.waitUntil(pathmanager.movetop_button.isEnabled)
    assert pathmanager.movetop_button.isEnabled()
    assert pathmanager.moveup_button.isEnabled()
    assert not pathmanager.movebottom_button.isEnabled()
    assert not pathmanager.movedown_button.isEnabled()
    assert pathmanager.remove_button.isEnabled()
    assert pathmanager.current_row() == 5

    # Check delete and ok button
    pathmanager.remove_path(True)
    assert not pathmanager.button_ok.isEnabled()

    # Check prioritize button
    assert pathmanager.prioritize_button.isEnabled()
    assert not pathmanager.prioritize_button.isChecked()
    pathmanager.prioritize_button.animateClick()
    qtbot.waitUntil(pathmanager.prioritize_button.isChecked)
    assert pathmanager.prioritize_button.isChecked()
    assert pathmanager.button_ok.isEnabled()


if __name__ == "__main__":
    pytest.main([os.path.basename(__file__)])
