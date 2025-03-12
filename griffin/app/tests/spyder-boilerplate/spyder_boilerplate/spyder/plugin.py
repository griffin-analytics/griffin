# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2021, Griffin Bot
#
# 
# ----------------------------------------------------------------------------
"""
Griffin Boilerplate Plugin.
"""

# Third party imports
import qtawesome as qta
from qtpy.QtWidgets import QHBoxLayout, QTextEdit

# Griffin imports
from griffin.api.config.decorators import on_conf_change
from griffin.api.plugins import GriffinDockablePlugin
from griffin.api.preferences import PluginConfigPage
from griffin.api.widgets.main_widget import PluginMainWidget
from griffin.plugins.layout.layouts import VerticalSplitLayout2
from griffin.utils.palette import GriffinPalette


class GriffinBoilerplateConfigPage(PluginConfigPage):

    # --- PluginConfigPage API
    # ------------------------------------------------------------------------
    def setup_page(self):
        pass


class GriffinBoilerplateActions:
    ExampleAction = "example_action"


class GriffinBoilerplateToolBarSections:
    ExampleSection = "example_section"


class GriffinBoilerplateOptionsMenuSections:
    ExampleSection = "example_section"


class GriffinBoilerplateWidget(PluginMainWidget):

    # PluginMainWidget class constants

    # Signals

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)

        # Create example widgets
        self._example_widget = QTextEdit(self)
        self._example_widget.setText("Example text")

        # Add example label to layout
        layout = QHBoxLayout()
        layout.addWidget(self._example_widget)
        self.setLayout(layout)

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return "Griffin boilerplate plugin"

    def get_focus_widget(self):
        return self

    def setup(self):
        # Create an example action
        example_action = self.create_action(
            name=GriffinBoilerplateActions.ExampleAction,
            text="Example action",
            tip="Example hover hint",
            icon=self.create_icon("python"),
            triggered=lambda: print("Example action triggered!"),
        )

        # Add an example action to the plugin options menu
        menu = self.get_options_menu()
        self.add_item_to_menu(
            example_action,
            menu,
            GriffinBoilerplateOptionsMenuSections.ExampleSection,
        )

        # Add an example action to the plugin toolbar
        toolbar = self.get_main_toolbar()
        self.add_item_to_toolbar(
            example_action,
            toolbar,
            GriffinBoilerplateOptionsMenuSections.ExampleSection,
        )

        # Shortcuts
        self.register_shortcut_for_widget(
            "Change text",
            self.change_text,
        )

        self.register_shortcut_for_widget(
            "new text",
            self.new_text,
            context="editor",
            plugin_name=self._plugin.NAME,
        )

    def update_actions(self):
        pass

    @on_conf_change
    def on_section_conf_change(self, section):
        pass

    # --- Public API
    # ------------------------------------------------------------------------
    def change_text(self):
        if self._example_widget.toPlainText() == "":
            self._example_widget.setText("Example text")
        else:
            self._example_widget.setText("")

    def new_text(self):
        if self._example_widget.toPlainText() != "Another text":
            self._example_widget.setText("Another text")


class GriffinBoilerplate(GriffinDockablePlugin):
    """
    Griffin Boilerplate plugin.
    """

    NAME = "griffin_boilerplate"
    REQUIRES = []
    OPTIONAL = []
    WIDGET_CLASS = GriffinBoilerplateWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = GriffinBoilerplateConfigPage
    CUSTOM_LAYOUTS = [VerticalSplitLayout2]
    CONF_DEFAULTS = [
        (CONF_SECTION, {}),
        (
            "shortcuts",
            # Note: These shortcut names are capitalized to check we can
            # set/get/reset them correctly.
            {f"{NAME}/Change text": "Ctrl+B", "editor/New text": "Ctrl+H"},
        ),
    ]

    # --- Signals

    # --- GriffinDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return "Griffin boilerplate plugin"

    @staticmethod
    def get_description():
        return "A boilerplate plugin for testing."

    @staticmethod
    def get_icon():
        return qta.icon('mdi6.alpha-b-box', color=GriffinPalette.ICON_1)

    def on_initialize(self):
        pass

    def check_compatibility(self):
        valid = True
        message = ""  # Note: Remember to use _("") to localize the string
        return valid, message

    def on_close(self, cancellable=True):
        return True

    # --- Public API
    # ------------------------------------------------------------------------
