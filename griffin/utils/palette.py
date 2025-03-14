# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""
Palettes for dark and light themes used in Griffin.
"""

# Third-party imports
from qdarkstyle.colorsystem import Blue, Gray
from qdarkstyle.dark.palette import DarkPalette
from qdarkstyle.light.palette import LightPalette

# Local imports
from griffin.config.gui import is_dark_interface
from griffin.utils.color_system import (Green, Red, Orange, GroupDark,
                                       GroupLight, Logos)

# =============================================================================
# ---- Griffin palettes
# =============================================================================
class GriffinPaletteDark(DarkPalette):
    """Dark palette for Griffin."""

    # Colors for information and feedback in dialogs
    COLOR_SUCCESS_1 = Green.B40
    COLOR_SUCCESS_2 = Green.B70
    COLOR_SUCCESS_3 = Green.B90

    COLOR_ERROR_1 = Red.B40
    COLOR_ERROR_2 = Red.B70
    COLOR_ERROR_3 = Red.B110

    COLOR_WARN_1 = Orange.B40
    COLOR_WARN_2 = Orange.B70
    COLOR_WARN_3 = Orange.B90
    COLOR_WARN_4 = Orange.B100

    # Icon colors
    ICON_1 = Gray.B140
    ICON_2 = Blue.B80
    ICON_3 = Green.B80
    ICON_4 = Red.B70
    ICON_5 = Orange.B70
    ICON_6 = Gray.B30

    # Colors for icons and variable explorer in dark mode
    GROUP_1 = GroupDark.B10
    GROUP_2 = GroupDark.B20
    GROUP_3 = GroupDark.B30
    GROUP_4 = GroupDark.B40
    GROUP_5 = GroupDark.B50
    GROUP_6 = GroupDark.B60
    GROUP_7 = GroupDark.B70
    GROUP_8 = GroupDark.B80
    GROUP_9 = GroupDark.B90
    GROUP_10 = GroupDark.B100
    GROUP_11 = GroupDark.B110
    GROUP_12 = GroupDark.B120

    # Colors for highlight in editor
    COLOR_HIGHLIGHT_1 = Blue.B10
    COLOR_HIGHLIGHT_2 = Blue.B20
    COLOR_HIGHLIGHT_3 = Blue.B30
    COLOR_HIGHLIGHT_4 = Blue.B50

    # Colors for occurrences from find widget
    COLOR_OCCURRENCE_1 = Gray.B10
    COLOR_OCCURRENCE_2 = Gray.B20
    COLOR_OCCURRENCE_3 = Gray.B30
    COLOR_OCCURRENCE_4 = Gray.B50
    COLOR_OCCURRENCE_5 = Gray.B80

    # Colors for Griffin and Python logos
    PYTHON_LOGO_UP = Logos.B10
    PYTHON_LOGO_DOWN = Logos.B20
    GRIFFIN_LOGO_BACKGROUND = Logos.B30
    GRIFFIN_LOGO_WEB = Logos.B40
    GRIFFIN_LOGO_SNAKE = Logos.B50

    # For special tabs
    SPECIAL_TABS_SEPARATOR = Gray.B70
    SPECIAL_TABS_SELECTED = DarkPalette.COLOR_ACCENT_2

    # For the heart used to ask for donations
    COLOR_HEART = Blue.B80

    # For editor tooltips
    TIP_TITLE_COLOR = Green.B80
    TIP_CHAR_HIGHLIGHT_COLOR = Orange.B90


class GriffinPaletteLight(LightPalette):
    """Light palette for Griffin."""

    # Colors for information and feedback in dialogs
    COLOR_SUCCESS_1 = Green.B40
    COLOR_SUCCESS_2 = Green.B70
    COLOR_SUCCESS_3 = Green.B30

    COLOR_ERROR_1 = Red.B40
    COLOR_ERROR_2 = Red.B70
    COLOR_ERROR_3 = Red.B110

    COLOR_WARN_1 = Orange.B40
    COLOR_WARN_2 = Orange.B70
    COLOR_WARN_3 = Orange.B50
    COLOR_WARN_4 = Orange.B40

    # Icon colors
    ICON_1 = Gray.B30
    ICON_2 = Blue.B50
    ICON_3 = Green.B30
    ICON_4 = Red.B70
    ICON_5 = Orange.B70
    ICON_6 = Gray.B140

    # Colors for icons and variable explorer in light mode
    GROUP_1 = GroupLight.B10
    GROUP_2 = GroupLight.B20
    GROUP_3 = GroupLight.B30
    GROUP_4 = GroupLight.B40
    GROUP_5 = GroupLight.B50
    GROUP_6 = GroupLight.B60
    GROUP_7 = GroupLight.B70
    GROUP_8 = GroupLight.B80
    GROUP_9 = GroupLight.B90
    GROUP_10 = GroupLight.B100
    GROUP_11 = GroupLight.B110
    GROUP_12 = GroupLight.B120

    # Colors for highlight in editor
    COLOR_HIGHLIGHT_1 = Blue.B140
    COLOR_HIGHLIGHT_2 = Blue.B130
    COLOR_HIGHLIGHT_3 = Blue.B120
    COLOR_HIGHLIGHT_4 = Blue.B110

    # Colors for occurrences from find widget
    COLOR_OCCURRENCE_1 = Gray.B120
    COLOR_OCCURRENCE_2 = Gray.B110
    COLOR_OCCURRENCE_3 = Gray.B100
    COLOR_OCCURRENCE_4 = Gray.B90
    COLOR_OCCURRENCE_5 = Gray.B60

    # Colors for Griffin and Python logos
    PYTHON_LOGO_UP = Logos.B10
    PYTHON_LOGO_DOWN = Logos.B20
    GRIFFIN_LOGO_BACKGROUND = Logos.B30
    GRIFFIN_LOGO_WEB = Logos.B40
    GRIFFIN_LOGO_SNAKE = Logos.B50

    # For special tabs
    SPECIAL_TABS_SEPARATOR = Gray.B70
    SPECIAL_TABS_SELECTED = LightPalette.COLOR_ACCENT_5

    # For the heart used to ask for donations
    COLOR_HEART = Red.B70

    # For editor tooltips
    TIP_TITLE_COLOR = Green.B20
    TIP_CHAR_HIGHLIGHT_COLOR = Orange.B30


# =============================================================================
# ---- Exported classes
# =============================================================================
if is_dark_interface():
    GriffinPalette = GriffinPaletteDark
else:
    GriffinPalette = GriffinPaletteLight
