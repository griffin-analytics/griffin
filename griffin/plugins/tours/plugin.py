# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Griffin Project Contributors
#
# Distributed under the terms of the MIT License
# (see griffin/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tours Plugin.
"""

# Local imports
from griffin.api.plugins import Plugins, GriffinPluginV2
from griffin.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from griffin.api.translations import _
from griffin.config.base import get_safe_mode, running_under_pytest
from griffin.plugins.application.api import ApplicationActions
from griffin.plugins.mainmenu.api import ApplicationMenus, HelpMenuSections
from griffin.plugins.tours.container import TourActions, ToursContainer
from griffin.plugins.tours.tours import INTRO_TOUR, TourIdentifiers
from griffin.plugins.tours.api import GriffinWidgets


class Tours(GriffinPluginV2):
    """
    Tours Plugin.
    """
    NAME = 'tours'
    CONF_SECTION = NAME
    OPTIONAL = [Plugins.MainMenu]
    CONF_FILE = False
    CONTAINER_CLASS = ToursContainer

    # ---- GriffinPluginV2 API
    # -------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Interactive tours")

    @staticmethod
    def get_description():
        return _("Provide interactive tours of the Griffin interface.")

    @classmethod
    def get_icon(cls):
        return cls.create_icon('tour')

    def on_initialize(self):
        pass

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        mainmenu.add_item_to_application_menu(
            self.get_container().tour_action,
            menu_id=ApplicationMenus.Help,
            section=HelpMenuSections.Documentation,
            before_section=HelpMenuSections.Support,
            before=ApplicationActions.GriffinDocumentationAction)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.remove_item_from_application_menu(
            TourActions.ShowTour,
            menu_id=ApplicationMenus.Help)

    def on_mainwindow_visible(self):
        # Remove from intro tour steps for unavailable plugins.
        # Fixes griffin-ide/griffin#22635
        trimmed_intro_tour = self._trim_intro_tour()

        # Register trimmed tour
        self.register_tour(
            TourIdentifiers.IntroductionTour,
            _("Introduction to Griffin"),
            trimmed_intro_tour,
        )

        # Show tour message (only the first time Griffin starts)
        self.show_tour_message()

    # ---- Public API
    # -------------------------------------------------------------------------
    def register_tour(self, tour_id, title, tour_data):
        """
        Register a new interactive tour on griffin.

        Parameters
        ----------
        tour_id: str
            Unique tour string identifier.
        title: str
            Localized tour name.
        tour_data: dict
            The tour steps.
        """
        self.get_container().register_tour(tour_id, title, tour_data)

    def show_tour(self, index):
        """
        Show interactive tour.

        Parameters
        ----------
        index: int
            The tour index to display.
        """
        self.get_container().show_tour(index)

    def show_tour_message(self, force=False):
        """
        Show message about starting the tour the first time Griffin starts.

        Parameters
        ----------
        force: bool
            Force the display of the tour message.
        """
        should_show_tour = self.get_conf('show_tour_message')
        if force or (should_show_tour and not running_under_pytest()
                     and not get_safe_mode()):
            self.set_conf('show_tour_message', False)
            self.get_container().show_tour_message()

    # ---- Private API
    # -------------------------------------------------------------------------
    def _trim_intro_tour(self):
        """Trim intro tour according to available plugins."""
        # Mapping of GriffinWidgets to Plugins (some names are different)
        # TODO: This should be fixed.
        widgets_to_plugins = {
            GriffinWidgets.editor: Plugins.Editor,
            GriffinWidgets.ipython_console: Plugins.IPythonConsole,
            GriffinWidgets.variable_explorer: Plugins.VariableExplorer,
            GriffinWidgets.help_plugin: Plugins.Help,
            GriffinWidgets.plots_plugin: Plugins.Plots,
            GriffinWidgets.file_explorer: Plugins.Explorer,
            GriffinWidgets.history_log: Plugins.History,
            GriffinWidgets.find_plugin: Plugins.Find,
            GriffinWidgets.profiler: Plugins.Profiler,
            GriffinWidgets.code_analysis: Plugins.Pylint,
        }

        # Only leave on tour the steps for available plugins
        trimmed_tour = []
        for step in INTRO_TOUR:
            if "widgets" in step:
                widget = step["widgets"][0]
                if self.is_plugin_available(widgets_to_plugins[widget]):
                    trimmed_tour.append(step)
            else:
                trimmed_tour.append(step)

        return trimmed_tour
