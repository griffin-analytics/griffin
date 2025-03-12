# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""
Application Plugin.
"""

# Standard library imports
import os
import os.path as osp
import subprocess
import sys

# Third party imports
from qtpy.QtCore import Slot

# Local imports
from griffin.api.plugins import Plugins, GriffinPluginV2
from griffin.api.translations import _
from griffin.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from griffin.api.widgets.menus import GriffinMenu, MENU_SEPARATOR
from griffin.config.base import (get_module_path, get_debug_level,
                                running_under_pytest)
from griffin.plugins.application.confpage import ApplicationConfigPage
from griffin.plugins.application.container import (
    ApplicationActions, ApplicationContainer, ApplicationPluginMenus)
from griffin.plugins.console.api import ConsoleActions
from griffin.plugins.mainmenu.api import (
    ApplicationMenus, FileMenuSections, HelpMenuSections, ToolsMenuSections)
from griffin.utils.qthelpers import add_actions


class Application(GriffinPluginV2):
    NAME = 'application'
    REQUIRES = [Plugins.Console, Plugins.Preferences]
    OPTIONAL = [Plugins.Help, Plugins.MainMenu, Plugins.Shortcuts,
                Plugins.Editor, Plugins.StatusBar, Plugins.UpdateManager]
    CONTAINER_CLASS = ApplicationContainer
    CONF_SECTION = 'main'
    CONF_FILE = False
    CONF_WIDGET_CLASS = ApplicationConfigPage
    CAN_BE_DISABLED = False

    @staticmethod
    def get_name():
        return _('Application')

    @classmethod
    def get_icon(cls):
        return cls.create_icon('genprefs')

    @staticmethod
    def get_description():
        return _('Provide main application base actions.')

    def on_initialize(self):
        container = self.get_container()
        container.sig_report_issue_requested.connect(self.report_issue)
        container.set_window(self._window)

    # --------------------- PLUGIN INITIALIZATION -----------------------------
    @on_plugin_available(plugin=Plugins.Shortcuts)
    def on_shortcuts_available(self):
        if self.is_plugin_available(Plugins.MainMenu):
            self._populate_help_menu()

    @on_plugin_available(plugin=Plugins.Console)
    def on_console_available(self):
        if self.is_plugin_available(Plugins.MainMenu):
            self.report_action.setVisible(True)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        # Register conf page
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        self._populate_file_menu()
        self._populate_tools_menu()

        if self.is_plugin_enabled(Plugins.Shortcuts):
            if self.is_plugin_available(Plugins.Shortcuts):
                self._populate_help_menu()
        else:
            self._populate_help_menu()

        if not self.is_plugin_available(Plugins.Console):
            self.report_action.setVisible(False)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        editor = self.get_plugin(Plugins.Editor)
        self.get_container().sig_load_log_file.connect(editor.load)

    @on_plugin_available(plugin=Plugins.StatusBar)
    def on_statusbar_available(self):
        statusbar = self.get_plugin(Plugins.StatusBar)
        inapp_appeal_status = self.get_container().inapp_appeal_status
        statusbar.add_status_widget(inapp_appeal_status)

    # -------------------------- PLUGIN TEARDOWN ------------------------------
    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        editor = self.get_plugin(Plugins.Editor)
        self.get_container().sig_load_log_file.disconnect(editor.load)

    @on_plugin_teardown(plugin=Plugins.Console)
    def on_console_teardown(self):
        if self.is_plugin_available(Plugins.MainMenu):
            self.report_action.setVisible(False)

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        self._depopulate_file_menu()
        self._depopulate_tools_menu()
        self._depopulate_help_menu()
        self.report_action.setVisible(False)

    @on_plugin_teardown(plugin=Plugins.StatusBar)
    def on_statusbar_teardown(self):
        statusbar = self.get_plugin(Plugins.StatusBar)
        inapp_appeal_status = self.get_container().inapp_appeal_status
        statusbar.remove_status_widget(inapp_appeal_status.ID)

    def on_close(self, _unused=True):
        self.get_container().on_close()

    def on_mainwindow_visible(self):
        """Actions after the mainwindow in visible."""
        container = self.get_container()

        # Show dialog with missing dependencies
        if not running_under_pytest():
            container.compute_dependencies()

        # Handle DPI scale and window changes to show a restart message.
        # Don't activate this functionality on macOS because it's being
        # triggered in the wrong situations.
        # See griffin-ide/griffin#11846
        if not sys.platform == 'darwin':
            window = self._window.windowHandle()
            window.screenChanged.connect(container.handle_new_screen)
            screen = self._window.windowHandle().screen()
            container.current_dpi = screen.logicalDotsPerInch()
            screen.logicalDotsPerInchChanged.connect(
                container.show_dpi_change_message)

        # Show appeal the fifth and 25th time Griffin starts
        griffin_runs = self.get_conf("griffin_runs_for_appeal", default=1)
        if griffin_runs in [5, 25]:
            container.inapp_appeal_status.show_appeal()

            # Increase counting in one to not get stuck at this point.
            # Fixes griffin-ide/griffin#22457
            self.set_conf("griffin_runs_for_appeal", griffin_runs + 1)
        else:
            if griffin_runs < 25:
                self.set_conf("griffin_runs_for_appeal", griffin_runs + 1)

    # ---- Private API
    # ------------------------------------------------------------------------
    def _populate_file_menu(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.add_item_to_application_menu(
            self.restart_action,
            menu_id=ApplicationMenus.File,
            section=FileMenuSections.Restart)
        mainmenu.add_item_to_application_menu(
            self.restart_debug_action,
            menu_id=ApplicationMenus.File,
            section=FileMenuSections.Restart)

    def _populate_tools_menu(self):
        """Add base actions and menus to the Tools menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.add_item_to_application_menu(
            self.user_env_action,
            menu_id=ApplicationMenus.Tools,
            section=ToolsMenuSections.Tools)

        if get_debug_level() >= 2:
            mainmenu.add_item_to_application_menu(
                self.debug_logs_menu,
                menu_id=ApplicationMenus.Tools,
                section=ToolsMenuSections.Extras)

    def _populate_help_menu(self):
        """Add base actions and menus to the Help menu."""
        self._populate_help_menu_documentation_section()
        self._populate_help_menu_support_section()
        self._populate_help_menu_about_section()

    def _populate_help_menu_documentation_section(self):
        """Add base Griffin documentation actions to the Help main menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        shortcuts = self.get_plugin(Plugins.Shortcuts)
        shortcuts_summary_action = None

        if shortcuts:
            from griffin.plugins.shortcuts.plugin import ShortcutActions
            shortcuts_summary_action = ShortcutActions.ShortcutSummaryAction
        for documentation_action in [
                self.documentation_action, self.video_action]:
            mainmenu.add_item_to_application_menu(
                documentation_action,
                menu_id=ApplicationMenus.Help,
                section=HelpMenuSections.Documentation,
                before=shortcuts_summary_action,
                before_section=HelpMenuSections.Support)

    def _populate_help_menu_support_section(self):
        """Add Griffin base support actions to the Help main menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for support_action in [
            self.trouble_action,
            self.report_action,
            self.dependencies_action,
            self.support_group_action,
            self.get_action(ApplicationActions.HelpGriffinAction),
        ]:
            mainmenu.add_item_to_application_menu(
                support_action,
                menu_id=ApplicationMenus.Help,
                section=HelpMenuSections.Support,
                before_section=HelpMenuSections.ExternalDocumentation
            )

    def _populate_help_menu_about_section(self):
        """Create Griffin base about actions."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.add_item_to_application_menu(
            self.about_action,
            menu_id=ApplicationMenus.Help,
            section=HelpMenuSections.About)

    @property
    def _window(self):
        return self.main.window()

    def _depopulate_help_menu(self):
        self._depopulate_help_menu_documentation_section()
        self._depopulate_help_menu_support_section()
        self._depopulate_help_menu_about_section()

    def _depopulate_help_menu_documentation_section(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for documentation_action in [
                ApplicationActions.GriffinDocumentationAction,
                ApplicationActions.GriffinDocumentationVideoAction]:
            mainmenu.remove_item_from_application_menu(
                documentation_action,
                menu_id=ApplicationMenus.Help)

    def _depopulate_help_menu_support_section(self):
        """Remove Griffin base support actions from the Help main menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for support_action in [
                ApplicationActions.GriffinTroubleshootingAction,
                ConsoleActions.GriffinReportAction,
                ApplicationActions.GriffinDependenciesAction,
                ApplicationActions.GriffinSupportAction]:
            mainmenu.remove_item_from_application_menu(
                support_action,
                menu_id=ApplicationMenus.Help)

    def _depopulate_help_menu_about_section(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.remove_item_from_application_menu(
            ApplicationActions.GriffinAbout,
            menu_id=ApplicationMenus.Help)

    def _depopulate_file_menu(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)
        for action_id in [ApplicationActions.GriffinRestart,
                          ApplicationActions.GriffinRestartDebug]:
            mainmenu.remove_item_from_application_menu(
                action_id,
                menu_id=ApplicationMenus.File)

    def _depopulate_tools_menu(self):
        """Add base actions and menus to the Tools menu."""
        mainmenu = self.get_plugin(Plugins.MainMenu)
        mainmenu.remove_item_from_application_menu(
            ApplicationActions.GriffinUserEnvVariables,
            menu_id=ApplicationMenus.Tools)

        if get_debug_level() >= 2:
            mainmenu.remove_item_from_application_menu(
                ApplicationPluginMenus.DebugLogsMenu,
                menu_id=ApplicationMenus.Tools)

    # ---- Public API
    # ------------------------------------------------------------------------
    def get_application_context_menu(self, parent=None):
        """
        Return menu with the actions to be shown by the Griffin context menu.
        """
        tutorial_action = None
        shortcuts_action = None

        help_plugin = self.get_plugin(Plugins.Help)
        shortcuts = self.get_plugin(Plugins.Shortcuts)
        menu = GriffinMenu(parent=parent)
        actions = [self.documentation_action]
        # Help actions
        if help_plugin:
            from griffin.plugins.help.plugin import HelpActions
            tutorial_action = help_plugin.get_action(
                HelpActions.ShowGriffinTutorialAction)
            actions += [tutorial_action]
        # Shortcuts actions
        if shortcuts:
            from griffin.plugins.shortcuts.plugin import ShortcutActions
            shortcuts_action = shortcuts.get_action(
                ShortcutActions.ShortcutSummaryAction)
            actions.append(shortcuts_action)
        # Application actions
        actions += [MENU_SEPARATOR, self.about_action]

        add_actions(menu, actions)

        return menu

    def report_issue(self):
        if self.is_plugin_available(Plugins.Console):
            console = self.get_plugin(Plugins.Console)
            console.report_issue()

    def apply_settings(self):
        """Apply applications settings."""
        self._main.apply_settings()

    @Slot()
    def restart(self, reset=False, close_immediately=False):
        """
        Quit and Restart Griffin application.

        If reset True it allows to reset griffin on restart.
        """
        # Get console plugin reference to call the quit action
        console = self.get_plugin(Plugins.Console)

        # Get start path to use in restart script
        griffin_start_directory = get_module_path('griffin')
        restart_script = osp.join(griffin_start_directory, 'app', 'restart.py')

        # Get any initial argument passed when griffin was started
        # Note: Variables defined in bootstrap.py and griffin/app/start.py
        env = os.environ.copy()
        bootstrap_args = env.pop('GRIFFIN_BOOTSTRAP_ARGS', None)
        griffin_args = env.pop('GRIFFIN_ARGS')

        # Get current process and python running griffin
        pid = os.getpid()
        python = sys.executable

        # Check if started with bootstrap.py
        if bootstrap_args is not None:
            griffin_args = bootstrap_args
            is_bootstrap = True
        else:
            is_bootstrap = False

        # Pass variables as environment variables (str) to restarter subprocess
        env['GRIFFIN_ARGS'] = griffin_args
        env['GRIFFIN_PID'] = str(pid)
        env['GRIFFIN_IS_BOOTSTRAP'] = str(is_bootstrap)

        # Build the command and popen arguments depending on the OS
        if os.name == 'nt':
            # Hide flashing command prompt
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            shell = False
        else:
            startupinfo = None
            shell = True

        command = '"{0}" "{1}"'
        command = command.format(python, restart_script)

        try:
            if self.main.closing(True, close_immediately=close_immediately):
                subprocess.Popen(command, shell=shell, env=env,
                                 startupinfo=startupinfo)
                console.quit()
        except Exception as error:
            # If there is an error with subprocess, Griffin should not quit and
            # the error can be inspected in the internal console
            print(error)  # griffin: test-skip
            print(command)  # griffin: test-skip

    @property
    def documentation_action(self):
        """Open Griffin's Documentation in the browser."""
        return self.get_container().documentation_action

    @property
    def video_action(self):
        """Open Griffin's video documentation in the browser."""
        return self.get_container().video_action

    @property
    def trouble_action(self):
        """Open Griffin's troubleshooting documentation in the browser."""
        return self.get_container().trouble_action

    @property
    def dependencies_action(self):
        """Show Griffin's Dependencies dialog box."""
        return self.get_container().dependencies_action

    @property
    def support_group_action(self):
        """Open Griffin's Google support group in the browser."""
        return self.get_container().support_group_action

    @property
    def about_action(self):
        """Show Griffin's About dialog box."""
        return self.get_container().about_action

    @property
    def user_env_action(self):
        """Show Griffin's Windows user env variables dialog box."""
        return self.get_container().user_env_action

    @property
    def restart_action(self):
        """Restart Griffin action."""
        return self.get_container().restart_action

    @property
    def restart_debug_action(self):
        """Restart Griffin in DEBUG mode action."""
        return self.get_container().restart_debug_action

    @property
    def report_action(self):
        """Restart Griffin action."""
        return self.get_container().report_action

    @property
    def debug_logs_menu(self):
        return self.get_container().get_menu(
            ApplicationPluginMenus.DebugLogsMenu)
