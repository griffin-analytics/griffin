# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""Profiler config page."""

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from griffin.api.preferences import PluginConfigPage
from griffin.config.base import _
from griffin.plugins.profiler.widgets.main_widget import ProfilerWidget


class ProfilerConfigPage(PluginConfigPage):
    def setup_page(self):
        results_group = QGroupBox(_("Results"))
        results_label1 = QLabel(_("Profiler plugin results "
                                  "(the output of python's profile/cProfile)\n"
                                  "are stored here:"))
        results_label1.setWordWrap(True)

        # Warning: do not try to regroup the following QLabel contents with
        # widgets above -- this string was isolated here in a single QLabel
        # on purpose: to fix griffin-ide/griffin#863.
        results_label2 = QLabel(ProfilerWidget.DATAPATH)

        results_label2.setTextInteractionFlags(Qt.TextSelectableByMouse)
        results_label2.setWordWrap(True)

        results_layout = QVBoxLayout()
        results_layout.addWidget(results_label1)
        results_layout.addWidget(results_label2)
        results_group.setLayout(results_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(results_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)
