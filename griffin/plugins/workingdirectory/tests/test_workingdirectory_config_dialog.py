# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Griffin Project Contributors
#
# 
# ----------------------------------------------------------------------------
"""Tests for plugin config dialog."""

# Third party imports
import pytest

# Local imports
from griffin.plugins.workingdirectory.plugin import WorkingDirectory
from griffin.plugins.preferences.tests.conftest import config_dialog


@pytest.mark.parametrize(
    'config_dialog',
    # [[MainWindowMock, [ConfigPlugins], [Plugins]]]
    [[None, [], [WorkingDirectory]]],
    indirect=True)
def test_config_dialog(qtbot, config_dialog):
    configpage = config_dialog.get_page()
    configpage.save_to_conf()
    assert configpage
