# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""Online Help Plugin"""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from griffin.api.plugins import Plugins, GriffinDockablePlugin
from griffin.api.translations import _
from griffin.config.base import get_conf_path
from griffin.plugins.onlinehelp.widgets import PydocBrowser


# --- Plugin
# ----------------------------------------------------------------------------
class OnlineHelp(GriffinDockablePlugin):
    """
    Online Help Plugin.
    """

    NAME = 'onlinehelp'
    TABIFY = [Plugins.VariableExplorer, Plugins.Help]
    CONF_SECTION = NAME
    CONF_FILE = False
    WIDGET_CLASS = PydocBrowser
    LOG_PATH = get_conf_path(NAME)
    REQUIRE_WEB_WIDGETS = True

    # --- Signals
    # ------------------------------------------------------------------------
    sig_load_finished = Signal()
    """
    This signal is emitted to indicate the help page has finished loading.
    """

    # --- GriffinDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('Online help')

    @staticmethod
    def get_description():
        return _(
            "Browse and search documentation for installed Python modules "
            "interactively."
        )

    @classmethod
    def get_icon(cls):
        return cls.create_icon('online_help')

    def on_close(self, cancelable=False):
        self.save_history()
        self.set_conf('zoom_factor',
                      self.get_widget().get_zoom_factor())
        return True

    def on_initialize(self):
        widget = self.get_widget()
        widget.load_history(self.load_history())
        widget.sig_load_finished.connect(self.sig_load_finished)

    def update_font(self):
        self.get_widget().reload()

    # --- Public API
    # ------------------------------------------------------------------------
    def load_history(self):
        """
        Load history from a text file in the Griffin configuration directory.
        """
        if osp.isfile(self.LOG_PATH):
            with open(self.LOG_PATH, 'r') as fh:
                lines = fh.read().split('\n')

            history = [line.replace('\n', '') for line in lines]
        else:
            history = []

        return history

    def save_history(self):
        """
        Save history to a text file in the Griffin configuration directory.
        """
        data = "\n".join(self.get_widget().get_history())
        with open(self.LOG_PATH, 'w') as fh:
            fh.write(data)
