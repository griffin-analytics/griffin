# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Griffin Project Contributors
#
# 
# ----------------------------------------------------------------------------
"""Tests for plugin config dialog."""

# Standard library imports
import pytest

# Local imports
from griffin.plugins.shortcuts.plugin import Shortcuts
from griffin.plugins.preferences.tests.conftest import config_dialog


@pytest.mark.parametrize(
    'config_dialog',
    [[None, [], [Shortcuts]]],
    indirect=True)
def test_config_dialog(config_dialog):
    configpage = config_dialog.get_page()
    configpage.save_to_conf()
    assert configpage
