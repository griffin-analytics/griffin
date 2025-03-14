# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Griffin Project Contributors
#
# 
# (see griffin/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the array editor.
"""

# Standard library imports
import os
import sys
from unittest.mock import Mock, patch, ANY

# Third party imports
from flaky import flaky
import numpy as np
from numpy.testing import assert_array_equal
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMessageBox
from scipy.io import loadmat

# Local imports
from griffin.plugins.variableexplorer.widgets.arrayeditor import (
    ArrayEditor, ArrayModel)


# =============================================================================
# Constants
# =============================================================================
HERE = os.path.dirname(os.path.realpath(__file__))


# =============================================================================
# Utility functions
# =============================================================================
def launch_arrayeditor(data, title=""):
    """Helper routine to launch an arrayeditor and return its result."""
    dlg = ArrayEditor()
    assert dlg.setup_and_check(data, title)
    dlg.show()
    dlg.accept()  # trigger slot connected to OK button
    return dlg.get_value()


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def setup_arrayeditor(qtbot, data):
    """Setups an arrayeditor."""
    dlg = ArrayEditor()
    dlg.setup_and_check(data)
    dlg.show()
    qtbot.addWidget(dlg)
    return dlg


# =============================================================================
# Tests
# =============================================================================
def test_object_arrays(qtbot):
    """Test that object arrays are working properly."""
    arr = np.array([u'a', 1, [2]], dtype=object)
    assert_array_equal(arr, launch_arrayeditor(arr, "object array"))


@pytest.mark.parametrize(
    'data',
    [np.array([[np.array([1, 2])], 2], dtype=object)],
)
def test_object_arrays_display(setup_arrayeditor):
    """
    Test that value_to_display is being used to display the values of
    object arrays.
    """
    dlg = setup_arrayeditor
    idx = dlg.arraywidget.model.index(0, 0)
    assert u'[Numpy array]' == dlg.arraywidget.model.data(idx)


@pytest.mark.parametrize(
    'data',
    [loadmat(os.path.join(HERE, 'issue_11216.mat'))['S']],
)
def test_attribute_errors(setup_arrayeditor):
    """
    Verify that we don't get a AttributeError for certain structured arrays.

    Fixes griffin-ide/griffin#11216 .
    """
    dlg = setup_arrayeditor
    data = loadmat(os.path.join(HERE, 'issue_11216.mat'))
    contents = dlg.arraywidget.model.get_value(dlg.arraywidget.model.index(0, 0))
    assert_array_equal(contents, data['S'][0][0][0])


@pytest.mark.parametrize(
    'data',
    [np.ones(2, dtype=[('X', 'f8', (2,10)), ('S', 'S10')])],
)
def test_type_errors(setup_arrayeditor, qtbot):
    """
    Verify that we don't get a TypeError for certain structured arrays.

    Fixes griffin-ide/griffin#5254.
    """
    dlg = setup_arrayeditor
    qtbot.keyClick(dlg.arraywidget.view, Qt.Key_Down, modifier=Qt.ShiftModifier)
    contents = dlg.arraywidget.model.get_value(dlg.arraywidget.model.index(0, 0))
    assert_array_equal(contents, np.ones(10))


@pytest.mark.parametrize(
    'data',
    [np.array([['a', 'b'], ['c', 'd']])]
)
def test_string_array_data_is_str(setup_arrayeditor):
    """
    Verify that the displayed data of an array of strings is of type `str`.

    Regression test for griffin-ide/griffin#22466.
    """
    dlg = setup_arrayeditor
    idx = dlg.arraywidget.model.index(0, 0)
    data = dlg.arraywidget.model.data(idx)
    assert data == 'a'
    assert type(data) is str


@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="Only works on Linux")
@pytest.mark.parametrize(
    'data',
    [np.array([1, 2, 3], dtype=np.float32)],
)
def test_arrayeditor_format(setup_arrayeditor, qtbot):
    """Changes the format of the array and validates its selected content."""
    dlg = setup_arrayeditor
    qtbot.keyClick(dlg.arraywidget.view, Qt.Key_Down, modifier=Qt.ShiftModifier)
    qtbot.keyClick(dlg.arraywidget.view, Qt.Key_Down, modifier=Qt.ShiftModifier)
    contents = dlg.arraywidget.view._sel_to_text(dlg.arraywidget.view.selectedIndexes())
    assert contents == "1\n2\n"
    dlg.arraywidget.view.model().set_format_spec(".18e")
    assert dlg.arraywidget.view.model().get_format_spec() == ".18e"
    qtbot.keyClick(dlg.arraywidget.view, Qt.Key_Down, modifier=Qt.ShiftModifier)
    qtbot.keyClick(dlg.arraywidget.view, Qt.Key_Down, modifier=Qt.ShiftModifier)
    contents = dlg.arraywidget.view._sel_to_text(dlg.arraywidget.view.selectedIndexes())
    assert contents == "1.000000000000000000e+00\n2.000000000000000000e+00\n"


@pytest.mark.parametrize(
    'data',
    [np.array([10000])]
)
def test_arrayeditor_format_thousands(setup_arrayeditor):
    """Check that format can include thousands separator."""
    model = setup_arrayeditor.arraywidget.model
    model.set_format_spec(',.2f')
    assert model.data(model.index(0, 0)) == '10,000.00'


def test_arrayeditor_with_inf_array(qtbot, recwarn):
    """See: griffin-ide/griffin#8093"""
    arr = np.array([np.inf])
    res = launch_arrayeditor(arr, "inf array")
    assert len(recwarn) == 0
    assert arr == res


def test_arrayeditor_with_string_array(qtbot):
    arr = np.array(["kjrekrjkejr"])
    assert arr == launch_arrayeditor(arr, "string array")


def test_arrayeditor_with_unicode_array(qtbot):
    arr = np.array([u"ñññéáíó"])
    assert arr == launch_arrayeditor(arr, "unicode array")


def test_arrayeditor_with_masked_array(qtbot):
    arr = np.ma.array([[1, 0], [1, 0]], mask=[[True, False], [False, False]])
    assert_array_equal(arr, launch_arrayeditor(arr, "masked array"))


def test_arrayeditor_with_record_array(qtbot):
    arr = np.zeros((2, 2), {'names': ('red', 'green', 'blue'),
                            'formats': (np.float32, np.float32, np.float32)})
    assert_array_equal(arr, launch_arrayeditor(arr, "record array"))


@pytest.mark.skipif(not os.name == 'nt', reason="It segfaults sometimes on Linux")
def test_arrayeditor_with_record_array_with_titles(qtbot):
    arr = np.array([(0, 0.0), (0, 0.0), (0, 0.0)],
                   dtype=[(('title 1', 'x'), '|i1'),
                          (('title 2', 'y'), '>f4')])
    assert_array_equal(arr, launch_arrayeditor(arr, "record array with titles"))


def test_arrayeditor_with_float_array(qtbot):
    arr = np.random.rand(5, 5)
    assert_array_equal(arr, launch_arrayeditor(arr, "float array"))


def test_arrayeditor_with_complex_array(qtbot):
    arr = np.round(np.random.rand(5, 5)*10)+\
                   np.round(np.random.rand(5, 5)*10)*1j
    assert_array_equal(arr, launch_arrayeditor(arr, "complex array"))


def test_arrayeditor_with_bool_array(qtbot):
    arr_in = np.array([True, False, True])
    arr_out = launch_arrayeditor(arr_in, "bool array")
    assert arr_in is arr_out

def test_arrayeditor_with_int8_array(qtbot):
    arr = np.array([1, 2, 3], dtype="int8")
    assert_array_equal(arr, launch_arrayeditor(arr, "int array"))


def test_arrayeditor_with_float16_array(qtbot):
    arr = np.zeros((5,5), dtype=np.float16)
    assert_array_equal(arr, launch_arrayeditor(arr, "float16 array"))


def test_arrayeditor_with_3d_array(qtbot):
    arr = np.zeros((3,3,4))
    arr[0,0,0]=1
    arr[0,0,1]=2
    arr[0,0,2]=3
    assert_array_equal(arr, launch_arrayeditor(arr, "3D array"))


def test_arrayeditor_with_empty_3d_array(qtbot):
    arr = np.zeros((0, 10, 2))
    assert_array_equal(arr, launch_arrayeditor(arr, "3D array"))
    arr = np.zeros((1, 10, 2))
    assert_array_equal(arr, launch_arrayeditor(arr, "3D array"))


def test_arrayeditor_refreshaction_disabled():
    """
    Test that the Refresh action is disabled by default.
    """
    arr_ones = np.ones((3, 3))
    dlg = ArrayEditor()
    dlg.setup_and_check(arr_ones, '2D array')
    assert not dlg.refresh_action.isEnabled()


def test_arrayeditor_refresh():
    """
    Test that after pressing the refresh button, the value of the editor is
    replaced by the return value of the data_function.
    """
    arr_ones = np.ones((3, 3))
    arr_zeros = np.zeros((4, 4))
    datafunc = lambda: arr_zeros
    dlg = ArrayEditor(data_function=datafunc)
    assert dlg.setup_and_check(arr_ones, '2D array')
    assert_array_equal(dlg.get_value(), arr_ones)
    assert dlg.refresh_action.isEnabled()
    dlg.refresh_action.trigger()
    assert_array_equal(dlg.get_value(), arr_zeros)


@pytest.mark.parametrize('result', [QMessageBox.Yes, QMessageBox.No])
def test_arrayeditor_refresh_after_edit(result):
    """
    Test that after changing a value in the array editor, pressing the Refresh
    button opens a dialog box (which asks for confirmation), and that the
    editor is only refreshed if the user clicks Yes.
    """
    arr_ones = np.ones((3, 3))
    arr_edited = arr_ones.copy()
    arr_edited[0, 0] = 2
    arr_zeros = np.zeros((4, 4))
    datafunc = lambda: arr_zeros
    dlg = ArrayEditor(data_function=datafunc)
    dlg.setup_and_check(arr_ones, '2D array')
    dlg.show()
    model = dlg.arraywidget.model
    model.setData(model.index(0, 0), '2')
    with patch('griffin.plugins.variableexplorer.widgets.arrayeditor'
               '.QMessageBox.question',
               return_value=result) as mock_question:
        dlg.refresh_action.trigger()
    mock_question.assert_called_once()
    dlg.accept()
    if result == QMessageBox.Yes:
        assert_array_equal(dlg.get_value(), arr_zeros)
    else:
        assert_array_equal(dlg.get_value(), arr_edited)


def test_arrayeditor_refresh_into_int(qtbot):
    """
    Test that if the value after refreshing is not an array but an integer,
    a critical dialog box is displayed and that the array editor is closed.
    """
    arr_ones = np.ones((3, 3))
    datafunc = lambda: 1
    dlg = ArrayEditor(data_function=datafunc)
    dlg.setup_and_check(arr_ones, '2D array')
    with patch('griffin.plugins.variableexplorer.widgets.arrayeditor'
               '.QMessageBox.critical') as mock_critical, \
         qtbot.waitSignal(dlg.rejected, timeout=0):
        dlg.refresh_action.trigger()
    mock_critical.assert_called_once()


def test_arrayeditor_refresh_when_variable_deleted(qtbot):
    """
    Test that if the variable is deleted and then the editor is refreshed
    (resulting in data_function raising a KeyError), a critical dialog box
    is displayed and that the array editor is closed.
    """
    def datafunc():
        raise KeyError
    arr_ones = np.ones((3, 3))
    dlg = ArrayEditor(data_function=datafunc)
    dlg.setup_and_check(arr_ones, '2D array')
    with patch('griffin.plugins.variableexplorer.widgets.arrayeditor'
               '.QMessageBox.critical') as mock_critical, \
         qtbot.waitSignal(dlg.rejected, timeout=0):
        dlg.refresh_action.trigger()
    mock_critical.assert_called_once()


def test_arrayeditor_edit_1d_array(qtbot):
    exp_arr = np.array([1, 0, 2, 3, 4])
    arr = np.arange(0, 5)
    dlg = ArrayEditor()
    assert dlg.setup_and_check(arr, '1D array')
    with qtbot.waitExposed(dlg):
        dlg.show()
    view = dlg.arraywidget.view

    qtbot.keyPress(view, Qt.Key_Down)
    qtbot.keyPress(view, Qt.Key_Up)
    qtbot.keyClicks(view, '1')
    qtbot.keyPress(view, Qt.Key_Down)
    qtbot.keyClicks(view, '0')
    qtbot.keyPress(view, Qt.Key_Down)
    qtbot.keyPress(view, Qt.Key_Return)
    assert np.sum(exp_arr == dlg.get_value()) == 5


@pytest.mark.skipif(sys.platform == 'darwin', reason="It fails on macOS")
def test_arrayeditor_edit_2d_array(qtbot):
    arr = np.ones((3, 3))
    diff_arr = arr.copy()
    dlg = ArrayEditor()
    assert dlg.setup_and_check(arr, '2D array')
    with qtbot.waitExposed(dlg):
        dlg.show()
    view = dlg.arraywidget.view

    qtbot.keyPress(view, Qt.Key_Down)
    qtbot.keyPress(view, Qt.Key_Right)
    qtbot.keyClicks(view, '3')
    qtbot.keyPress(view, Qt.Key_Down)
    qtbot.keyPress(view, Qt.Key_Right)
    qtbot.keyClicks(view, '0')
    qtbot.keyPress(view, Qt.Key_Left)
    qtbot.keyPress(view, Qt.Key_Return)

    assert np.sum(diff_arr != dlg.get_value()) == 2


@pytest.mark.skipif(
    sys.platform.startswith('linux'),
    reason="Sometimes fails on Linux ")
def test_arrayeditor_edit_complex_array(qtbot):
    """See: griffin-ide/griffin#7848"""
    cnum = -1+0.5j
    arr = (np.random.random((10, 10)) - 0.50) * cnum
    dlg = ArrayEditor()
    assert dlg.setup_and_check(arr, '2D complex array')
    with qtbot.waitExposed(dlg):
        dlg.show()
    view = dlg.arraywidget.view
    qtbot.keyPress(view, Qt.Key_Down)

    # Prevent the test from failing
    qtbot.wait(300)

    # This is the actual editor widget on the cell
    cell_editor = view.viewport().focusWidget()
    qtbot.keyClicks(cell_editor, str(cnum))
    qtbot.keyPress(cell_editor, Qt.Key_Return)
    dlg.accept()


def test_arraymodel_set_data_overflow(monkeypatch):
    """
    Test that entry of an overflowing integer is caught and handled properly.

    Unit regression test for griffin-ide/griffin#6114.
    """
    MockQMessageBox = Mock()
    attr_to_patch = 'griffin.plugins.variableexplorer.widgets.arrayeditor.QMessageBox'
    monkeypatch.setattr(attr_to_patch, MockQMessageBox)

    # Numpy doesn't raise OverflowError on Linux for ints smaller than 64 bits
    if not os.name == 'nt':
        int32_bit_exponent = 66
    else:
        int32_bit_exponent = 34
    test_parameters = [(1, np.int32, int32_bit_exponent), (2, np.int64, 66)]

    for idx, int_type, bit_exponent in test_parameters:
        test_array = np.array([[5], [6], [7], [3], [4]], dtype=int_type)
        model = ArrayModel(test_array.copy())
        index = model.createIndex(0, 2)
        assert not model.setData(index, str(int(2 ** bit_exponent)))
        MockQMessageBox.critical.assert_called_with(ANY, "Error", ANY)
        assert MockQMessageBox.critical.call_count == idx
        assert np.sum(test_array == model._data) == len(test_array)


@flaky(max_runs=3)
@pytest.mark.skipif(sys.platform == 'darwin', reason="It fails on macOS")
def test_arrayeditor_edit_overflow(qtbot, monkeypatch):
    """
    Test that entry of an overflowing integer is caught and handled properly.

    Integration regression test for griffin-ide/griffin#6114.
    """
    MockQMessageBox = Mock()
    attr_to_patch = 'griffin.plugins.variableexplorer.widgets.arrayeditor.QMessageBox'
    monkeypatch.setattr(attr_to_patch, MockQMessageBox)

    # Numpy doesn't raise the OverflowError for ints smaller than 64 bits
    if not os.name == 'nt':
        int32_bit_exponent = 66
    else:
        int32_bit_exponent = 34
    test_parameters = [(1, np.int32, int32_bit_exponent), (2, np.int64, 66)]
    expected_array = np.array([5, 6, 7, 3, 4])

    for idx, int_type, bit_exponent in test_parameters:
        test_array = np.arange(0, 5).astype(int_type)
        dialog = ArrayEditor()
        assert dialog.setup_and_check(test_array, '1D array')
        with qtbot.waitExposed(dialog):
            dialog.show()
        view = dialog.arraywidget.view

        qtbot.keyClick(view, Qt.Key_Down)
        qtbot.keyClick(view, Qt.Key_Up)
        qtbot.keyClicks(view, '5')
        qtbot.keyClick(view, Qt.Key_Down)
        qtbot.keyClick(view, Qt.Key_Space)
        qtbot.keyClicks(view.focusWidget(), str(int(2 ** bit_exponent)))
        qtbot.keyClick(view.focusWidget(), Qt.Key_Down)
        MockQMessageBox.critical.assert_called_with(ANY, "Error", ANY)
        assert MockQMessageBox.critical.call_count == idx
        qtbot.keyClicks(view, '7')
        qtbot.keyClick(view, Qt.Key_Up)
        qtbot.keyClicks(view, '6')
        qtbot.keyClick(view, Qt.Key_Down)
        qtbot.wait(200)
        dialog.accept()
        qtbot.wait(500)
        assert np.sum(expected_array ==
                      dialog.get_value()) == len(expected_array)


if __name__ == "__main__":
    pytest.main()
