# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)
"""
Profiler Plugin.
"""
# Standard library imports
from typing import TypedDict

# Local imports
from griffin.plugins.profiler.widgets.main_widget import (  # noqa
    ProfilerWidgetActions, ProfilerWidgetInformationToolbarSections,
    ProfilerWidgetMainToolbarSections, ProfilerWidgetToolbars)


class ProfilerPyConfiguration(TypedDict):
    """Profiler execution parameters for Python files."""

    # True if the script is using custom arguments. False otherwise
    args_enabled: bool

    # Custom arguments to pass to the script when profiling.
    args: str
