# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""
Main menu Plugin.
"""

# Standard library imports
from collections import OrderedDict
import os
import sys
from typing import Dict, List, Tuple, Optional, Union

# Local imports
from griffin.api.exceptions import GriffinAPIError
from griffin.api.fonts import GriffinFontType
from griffin.api.plugin_registration.registry import PLUGIN_REGISTRY
from griffin.api.plugins import GriffinPluginV2, GriffinDockablePlugin, Plugins
from griffin.api.translations import _
from griffin.api.widgets.menus import GriffinMenu
from griffin.api.widgets.mixins import GriffinMenuMixin
from griffin.plugins.mainmenu.api import (
    ApplicationMenu,
    ApplicationMenus,
    MENUBAR_STYLESHEET,
)
from griffin.utils.qthelpers import GriffinAction


# Extended typing definitions
ItemType = Union[GriffinAction, GriffinMenu]
ItemSectionBefore = Tuple[
    ItemType, Optional[str], Optional[str], Optional[str]]
ItemQueue = Dict[str, List[ItemSectionBefore]]


class MainMenu(GriffinPluginV2, GriffinMenuMixin):
    NAME = 'mainmenu'
    CONF_SECTION = NAME
    CONF_FILE = False
    CAN_BE_DISABLED = False

    @staticmethod
    def get_name():
        return _('Main menus')

    @classmethod
    def get_icon(cls):
        return cls.create_icon('genprefs')

    @staticmethod
    def get_description():
        return _('Provide main application menu management.')

    def on_initialize(self):
        # Reference holder dict for the menus
        self._APPLICATION_MENUS = OrderedDict()

        # Queue that contain items that are pending to add to a non-existing
        # menu
        self._ITEM_QUEUE = {}  # type: ItemQueue

        # Set style. This is only necessary on Windows and Linux
        if not sys.platform == 'darwin':
            app_font = self.get_font(font_type=GriffinFontType.Interface)
            self.main.menuBar().setFont(app_font)
            self.main.menuBar().setStyleSheet(str(MENUBAR_STYLESHEET))

        # Create Application menus using plugin public API
        create_app_menu = self.create_application_menu
        create_app_menu(ApplicationMenus.File, _("&File"))
        create_app_menu(ApplicationMenus.Edit, _("&Edit"))
        create_app_menu(ApplicationMenus.Search, _("&Search"))
        create_app_menu(ApplicationMenus.Source, _("Sour&ce"))
        create_app_menu(ApplicationMenus.Run, _("&Run"))
        create_app_menu(ApplicationMenus.Debug, _("&Debug"))
        if self.is_plugin_enabled(Plugins.IPythonConsole):
            create_app_menu(ApplicationMenus.Consoles, _("C&onsoles"))
        if self.is_plugin_enabled(Plugins.Projects):
            create_app_menu(
                ApplicationMenus.Projects,
                _("&Projects"),
                min_width=150 if os.name == "nt" else 170
            )
        create_app_menu(ApplicationMenus.Tools, _("&Tools"))
        create_app_menu(ApplicationMenus.View, _("&View"))
        # Help menu disabled
        # create_app_menu(ApplicationMenus.Help, _("&Help"))

    def on_mainwindow_visible(self):
        # Pre-render menus so actions with menu roles (like "About Griffin" and
        # "Preferences") are located in the right place in Mac's menu bar.
        # Fixes griffin-ide/griffin#14917
        # This also registers shortcuts for actions that are only in menus.
        # Fixes griffin-ide/griffin#16061
        for menu in self._APPLICATION_MENUS.values():
            menu.render()

    # ---- Private methods
    # ------------------------------------------------------------------------
    def _hide_options_menus(self):
        """Hide options menu when menubar is pressed in macOS."""
        for plugin_name in PLUGIN_REGISTRY:
            plugin_instance = PLUGIN_REGISTRY.get_plugin(plugin_name)
            if isinstance(plugin_instance, GriffinDockablePlugin):
                if plugin_instance.CONF_SECTION == 'editor':
                    editorstack = self._main.editor.get_current_editorstack()
                    editorstack.menu.hide()
                else:
                    try:
                        # New API
                        plugin_instance.options_menu.hide()
                    except AttributeError:
                        # Old API
                        plugin_instance._options_menu.hide()

    # ---- Public API
    # ------------------------------------------------------------------------
    def create_application_menu(
        self,
        menu_id: str,
        title: str,
        min_width: Optional[int] = None
    ):
        """
        Create a Griffin application menu.

        Parameters
        ----------
        menu_id: str
            The menu unique identifier string.
        title: str
            The localized menu title to be displayed.
        min_width: int
            Minimum width for the menu in pixels.
        """
        if menu_id in self._APPLICATION_MENUS:
            raise GriffinAPIError(
                'Menu with id "{}" already added!'.format(menu_id)
            )

        menu = self._create_menu(
            menu_id=menu_id,
            parent=self.main,
            title=title,
            min_width=min_width,
            MenuClass=ApplicationMenu
        )
        self._APPLICATION_MENUS[menu_id] = menu
        self.main.menuBar().addMenu(menu)

        if sys.platform == 'darwin':
            menu.aboutToShow.connect(self._hide_options_menus)

            # This is necessary because for some strange reason the
            # "Configuration per file" entry disappears after showing other
            # dialogs and the only way to make it visible again is by
            # re-rendering the menu.
            if menu_id == ApplicationMenus.Run:
                menu.aboutToShow.connect(lambda: menu.render(force=True))

        if menu_id in self._ITEM_QUEUE:
            pending_items = self._ITEM_QUEUE.pop(menu_id)
            for pending in pending_items:
                (item, section,
                 before_item, before_section) = pending
                self.add_item_to_application_menu(
                    item, menu_id=menu_id, section=section,
                    before=before_item, before_section=before_section)

        return menu

    def add_item_to_application_menu(self, item: ItemType,
                                     menu_id: Optional[str] = None,
                                     section: Optional[str] = None,
                                     before: Optional[str] = None,
                                     before_section: Optional[str] = None,
                                     omit_id: bool = False):
        """
        Add action or widget `item` to given application menu `section`.

        Parameters
        ----------
        item: GriffinAction or GriffinMenu
            The item to add to the `menu`.
        menu_id: str or None
            The application menu unique string identifier.
        section: str or None
            The section id in which to insert the `item` on the `menu`.
        before: str
            Make the item appear before the given object identifier.
        before_section: Section or None
            Make the item section (if provided) appear before another
            given section.
        omit_id: bool
            If True, then the menu will check if the item to add declares an
            id, False otherwise. This flag exists only for items added on
            Griffin 4 plugins. Default: False

        Notes
        -----
        Must provide a `menu` or a `menu_id`.
        """
        if not isinstance(item, (GriffinAction, GriffinMenu)) and not omit_id:
            raise GriffinAPIError('A menu only accepts items objects of type '
                                 'GriffinAction or GriffinMenu')

        if menu_id not in self._APPLICATION_MENUS:
            pending_menu_items = self._ITEM_QUEUE.get(menu_id, [])
            pending_menu_items.append((item, section, before,
                                       before_section))
            self._ITEM_QUEUE[menu_id] = pending_menu_items
        else:
            menu = self.get_application_menu(menu_id)
            menu.add_action(item, section=section, before=before,
                            before_section=before_section, omit_id=omit_id)

    def remove_application_menu(self, menu_id: str):
        """
        Remove a Griffin application menu.

        Parameters
        ----------
        menu_id: str
            The menu unique identifier string.
        """
        if menu_id in self._APPLICATION_MENUS:
            menu = self._APPLICATION_MENUS.pop(menu_id)
            self.main.menuBar().removeAction(menu.menuAction())

    def remove_item_from_application_menu(self, item_id: str,
                                          menu_id: Optional[str] = None):
        """
        Remove action or widget from given application menu by id.

        Parameters
        ----------
        item_id: str
            The item identifier to remove from the given menu.
        menu_id: str or None
            The application menu unique string identifier.
        """
        if menu_id not in self._APPLICATION_MENUS:
            raise GriffinAPIError('{} is not a valid menu_id'.format(menu_id))

        menu = self.get_application_menu(menu_id)
        menu.remove_action(item_id)

    def get_application_menu(self, menu_id: str) -> GriffinMenu:
        """
        Return an application menu by menu unique id.

        Parameters
        ----------
        menu_id: ApplicationMenu
            The menu unique identifier string.
        """
        if menu_id not in self._APPLICATION_MENUS:
            raise GriffinAPIError(
                'Application menu "{0}" not found! Available '
                'menus are: {1}'.format(
                    menu_id, list(self._APPLICATION_MENUS.keys()))
            )

        return self._APPLICATION_MENUS[menu_id]
