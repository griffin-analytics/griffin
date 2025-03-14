# -*- coding: utf-8 -*-
#

# 
# (see griffin/__init__.py for details)

"""
Griffin API toolbar widgets.
"""

# Standard library imports
from collections import OrderedDict
import os
import sys
from typing import Dict, List, Optional, Tuple, Union
import uuid

# Third part imports
from qtpy.QtCore import QEvent, QObject, QSize, Qt, Signal
from qtpy.QtWidgets import (
    QAction, QProxyStyle, QStyle, QToolBar, QToolButton, QWidget)

# Local imports
from griffin.api.exceptions import GriffinAPIError
from griffin.api.translations import _
from griffin.api.widgets.menus import GriffinMenu, GriffinMenuProxyStyle
from griffin.utils.icon_manager import ima
from griffin.utils.qthelpers import GriffinAction
from griffin.utils.stylesheet import (
    APP_TOOLBAR_STYLESHEET, PANES_TOOLBAR_STYLESHEET)


# Generic type annotations
ToolbarItem = Union[GriffinAction, QWidget]
ToolbarItemEntry = Tuple[ToolbarItem, Optional[str], Optional[str],
                         Optional[str]]

# ---- Constants
# ----------------------------------------------------------------------------
class ToolbarLocation:
    Top = Qt.TopToolBarArea
    Bottom = Qt.BottomToolBarArea


# ---- Event filters
# ----------------------------------------------------------------------------
class ToolTipFilter(QObject):
    """
    Filter tool tip events on toolbuttons.
    """

    def eventFilter(self, obj, event):
        event_type = event.type()
        action = obj.defaultAction() if isinstance(obj, QToolButton) else None
        if event_type == QEvent.ToolTip and action is not None:
            if action.tip is None:
                return action.text_beside_icon

        return QObject.eventFilter(self, obj, event)


# ---- Styles
# ----------------------------------------------------------------------------
class ToolbarStyle(QProxyStyle):

    # The toolbar type. This can be 'Application' or 'MainWidget'
    TYPE = None

    def pixelMetric(self, pm, option, widget):
        """
        Adjust size of toolbar extension button (in pixels).

        From https://stackoverflow.com/a/27042352/438386
        """
        # Important: These values need to be updated in case we change the size
        # of our toolbar buttons in utils/stylesheet.py. That's because Qt only
        # allow to set them in pixels here, not em's.
        if pm == QStyle.PM_ToolBarExtensionExtent:
            if self.TYPE == 'Application':
                if os.name == 'nt':
                    return 40
                elif sys.platform == 'darwin':
                    return 54
                else:
                    return 57
            elif self.TYPE == 'MainWidget':
                if os.name == 'nt':
                    return 36
                elif sys.platform == 'darwin':
                    return 42
                else:
                    return 44
            else:
                print("Unknown toolbar style type")  # griffin: test-skip
        return super().pixelMetric(pm, option, widget)


# ---- Toolbars
# ----------------------------------------------------------------------------
class GriffinToolbar(QToolBar):
    """
    Griffin Toolbar.

    This class provides toolbars with some predefined functionality.
    """

    sig_is_rendered = Signal()
    """
    This signal is emitted to let other objects know that the toolbar is now
    rendered.
    """

    def __init__(self, parent, title):
        super().__init__(parent=parent)

        # Attributes
        self._title = title
        self._section_items = OrderedDict()
        self._item_map: Dict[str, ToolbarItem] = {}
        self._pending_items: Dict[str, List[ToolbarItemEntry]] = {}
        self._default_section = "default_section"
        self._filter = None

        self.setWindowTitle(title)

        # Set attributes for extension button.
        # From https://stackoverflow.com/a/55412455/438386
        ext_button = self.findChild(QToolButton, "qt_toolbar_ext_button")
        ext_button.setIcon(ima.icon('toolbar_ext_button'))
        ext_button.setToolTip(_("More"))

        # Set style for extension button menu (not all extension buttons have
        # it).
        if ext_button.menu():
            ext_button.menu().setStyleSheet(
                GriffinMenu._generate_stylesheet().toString()
            )

            ext_button_menu_style = GriffinMenuProxyStyle(None)
            ext_button_menu_style.setParent(self)
            ext_button.menu().setStyle(ext_button_menu_style)

    def add_item(
        self,
        action_or_widget: ToolbarItem,
        section: Optional[str] = None,
        before: Optional[str] = None,
        before_section: Optional[str] = None,
        omit_id: bool = False
    ):
        """
        Add action or widget item to given toolbar `section`.

        Parameters
        ----------
        item: GriffinAction or QWidget
            The item to add to the `toolbar`.
        toolbar_id: str or None
            The application toolbar unique string identifier.
        section: str or None
            The section id in which to insert the `item` on the `toolbar`.
        before: str or None
            Make the item appear before another given item.
        before_section: str or None
            Make the item defined section appear before another given section
            (must be already defined).
        omit_id: bool
            If True, then the toolbar will check if the item to add declares an
            id, False otherwise. This flag exists only for items added on
            Griffin 4 plugins. Default: False
        """
        item_id = None
        if (
            isinstance(action_or_widget, GriffinAction)
            or hasattr(action_or_widget, 'action_id')
        ):
            item_id = action_or_widget.action_id
        elif hasattr(action_or_widget, 'ID'):
            item_id = action_or_widget.ID
        if not omit_id and item_id is None and action_or_widget is not None:
            raise GriffinAPIError(
                f'Item {action_or_widget} must declare an ID attribute.'
            )

        if before is not None:
            if before not in self._item_map:
                before_pending_items = self._pending_items.get(before, [])
                before_pending_items.append(
                    (action_or_widget, section, before, before_section))
                self._pending_items[before] = before_pending_items
                return
            else:
                before = self._item_map[before]

        if section is None:
            section = self._default_section

        action_or_widget._section = section

        if before is not None:
            if section == self._default_section:
                action_or_widget._section = before._section
                section = before._section

        if section not in self._section_items:
            self._section_items[section] = [action_or_widget]
        else:
            if before is not None:
                new_actions_or_widgets = []
                for act_or_wid in self._section_items[section]:
                    if act_or_wid == before:
                        new_actions_or_widgets.append(action_or_widget)
                    new_actions_or_widgets.append(act_or_wid)

                self._section_items[section] = new_actions_or_widgets
            else:
                self._section_items[section].append(action_or_widget)
        if (before_section is not None and
                before_section in self._section_items):
            new_sections_keys = []
            for sec in self._section_items.keys():
                if sec == before_section:
                    new_sections_keys.append(section)
                if sec != section:
                    new_sections_keys.append(sec)
            self._section_items = OrderedDict(
                (section_key, self._section_items[section_key])
                for section_key in new_sections_keys)

        if item_id is not None:
            self._item_map[item_id] = action_or_widget
            if item_id in self._pending_items:
                item_pending = self._pending_items.pop(item_id)
                for item, section, before, before_section in item_pending:
                    self.add_item(item, section=section, before=before,
                                  before_section=before_section)

    def remove_item(self, item_id: str):
        """Remove action or widget from toolbar by id."""
        try:
            item = self._item_map.pop(item_id)
            for section in list(self._section_items.keys()):
                section_items = self._section_items[section]
                if item in section_items:
                    section_items.remove(item)
                if len(section_items) == 0:
                    self._section_items.pop(section)
            self.clear()
            self.render()
        except KeyError:
            pass

    def render(self):
        """Create the toolbar taking into account sections and locations."""
        sec_items = []
        for sec, items in self._section_items.items():
            for item in items:
                sec_items.append([sec, item])

            sep = QAction(self)
            sep.setSeparator(True)
            sec_items.append((None, sep))

        if sec_items:
            sec_items.pop()

        for (sec, item) in sec_items:
            if isinstance(item, QAction):
                add_method = super().addAction
            else:
                add_method = super().addWidget

            add_method(item)

            if isinstance(item, QAction):
                widget = self.widgetForAction(item)

                if self._filter is not None:
                    widget.installEventFilter(self._filter)

                text_beside_icon = getattr(item, 'text_beside_icon', False)
                if text_beside_icon:
                    widget.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

                if item.isCheckable():
                    widget.setCheckable(True)

        self.sig_is_rendered.emit()


class ApplicationToolbar(GriffinToolbar):
    """
    Griffin Main application Toolbar.
    """

    ID = None
    """
    Unique string toolbar identifier.

    This is used by Qt to be able to save and restore the state of widgets.
    """

    def __init__(self, parent, toolbar_id, title):
        super().__init__(parent=parent, title=title)
        self.ID = toolbar_id

        self._style = ToolbarStyle(None)
        self._style.TYPE = 'Application'
        self._style.setParent(self)
        self.setStyle(self._style)

        self.setStyleSheet(str(APP_TOOLBAR_STYLESHEET))

    def __str__(self):
        return f"ApplicationToolbar('{self.ID}')"

    def __repr__(self):
        return f"ApplicationToolbar('{self.ID}')"


class MainWidgetToolbar(GriffinToolbar):
    """
    Griffin Widget toolbar class.

    A toolbar used in Griffin dockable plugins to add internal toolbars
    to their interface.
    """

    ID = None
    """
    Unique string toolbar identifier.
    """

    def __init__(self, parent=None, title=None):
        super().__init__(parent, title=title or '')
        self._icon_size = QSize(16, 16)

        # Setup
        self.setObjectName("main_widget_toolbar_{}".format(
            str(uuid.uuid4())[:8]))
        self.setFloatable(False)
        self.setMovable(False)
        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self.setIconSize(self._icon_size)

        self._style = ToolbarStyle(None)
        self._style.TYPE = 'MainWidget'
        self._style.setParent(self)
        self.setStyle(self._style)

        self.setStyleSheet(str(PANES_TOOLBAR_STYLESHEET))

        self._filter = ToolTipFilter()

    def set_icon_size(self, icon_size):
        self._icon_size = icon_size
        self.setIconSize(icon_size)
