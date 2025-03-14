# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""Shortcut configuration page."""

# Third party imports
from qtpy.QtWidgets import (QHBoxLayout, QLabel, QMessageBox, QPushButton,
                            QVBoxLayout)

# Local imports
from griffin.api.preferences import PluginConfigPage
from griffin.api.translations import _
from griffin.plugins.shortcuts.widgets.table import (
    ShortcutFinder, ShortcutsTable)


class ShortcutsConfigPage(PluginConfigPage):
    APPLY_CONF_PAGE_SETTINGS = True

    def setup_page(self):
        # Widgets
        self.table = ShortcutsTable(self)
        self.finder = ShortcutFinder(self.table, self.table.set_regex)
        self.label_finder = QLabel(_('Search: '))
        self.reset_btn = QPushButton(_("Reset to default values"))
        self.top_label = QLabel(
            _("Here you can browse the list of all available shortcuts in "
              "Griffin. You can also customize them by double-clicking on any "
              "entry in this table."))

        # Widget setup
        self.table.finder = self.finder
        self.table.set_shortcut_data(self.plugin.get_shortcut_data())
        self.table.load_shortcuts()
        self.table.finder.setPlaceholderText(
            _("Search for a shortcut in the table above"))
        self.top_label.setWordWrap(True)

        # Layout
        hlayout = QHBoxLayout()
        vlayout = QVBoxLayout()
        vlayout.addWidget(self.top_label)
        hlayout.addWidget(self.label_finder)
        hlayout.addWidget(self.finder)
        vlayout.addWidget(self.table)
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.reset_btn)
        self.setLayout(vlayout)

        self.setTabOrder(self.table, self.finder)
        self.setTabOrder(self.finder, self.reset_btn)

        # Signals
        self.table.proxy_model.dataChanged.connect(
            lambda i1, i2, roles, opt='', sect='': self.has_been_modified(
                sect, opt))
        self.reset_btn.clicked.connect(self.reset_to_default)

    def check_settings(self):
        self.table.check_shortcuts()

    def reset_to_default(self, force=False):
        """Reset to default values of the shortcuts making a confirmation."""
        if not force:
            reset = QMessageBox.warning(
                self,
                _("Shortcuts reset"),
                _("Do you want to reset to default values?"),
                QMessageBox.Yes | QMessageBox.No,
            )

            if reset == QMessageBox.No:
                return

        self.plugin.reset_shortcuts()
        self.plugin.apply_shortcuts()
        self.table.load_shortcuts()
        self.load_from_conf()
        self.set_modified(False)

    def apply_settings(self, options):
        self.table.save_shortcuts()
        self.plugin.apply_shortcuts()
        self.plugin.apply_conf(options)
