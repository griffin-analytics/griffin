# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
#

"""
Tests for status.py
"""

# Test library imports
import pytest

# Third party imports
from qtpy.QtWidgets import QMainWindow

# Local imports
from griffin.plugins.editor.widgets.status import (CursorPositionStatus,
                                                  EncodingStatus, EOLStatus,
                                                  ReadWriteStatus, VCSStatus)


@pytest.fixture
def status_bar(qtbot):
    """Set up StatusBarWidget."""
    win = QMainWindow()
    win.setWindowTitle("Status widgets test")
    win.resize(900, 300)
    statusbar = win.statusBar()
    qtbot.addWidget(win)
    return (win, statusbar)


def test_status_bar(status_bar, qtbot):
    """Run StatusBarWidget."""
    win, statusbar = status_bar
    swidgets = []
    for klass in (ReadWriteStatus, EOLStatus, EncodingStatus,
                  CursorPositionStatus, VCSStatus):
        swidget = klass(win)
        swidgets.append(swidget)
    assert win
    assert len(swidgets) == 5


if __name__ == "__main__":
    pytest.main()
