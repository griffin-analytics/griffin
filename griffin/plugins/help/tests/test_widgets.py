# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
#
"""
Tests for the Help widgets.
"""

# Test library imports
import pytest

# Local imports
from griffin.plugins.help.widgets import RichText, PlainText


@pytest.fixture
def richtext(qtbot):
    """Set up richtext widget."""
    widget = RichText(None)
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def plaintext(qtbot):
    """Set up plaintext widget."""
    widget = PlainText(None)
    qtbot.addWidget(widget)
    return widget


def test_richtext(richtext):
    """Run RichText."""
    assert richtext


def test_plaintext(plaintext):
    """Run PlainText."""
    assert plaintext


if __name__ == "__main__":
    pytest.main()
