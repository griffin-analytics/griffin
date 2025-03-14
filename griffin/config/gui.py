# -*- coding: utf-8 -*-
#

# 
# (see griffin/__init__.py for details)

"""
Griffin GUI-related configuration management
(for non-GUI configuration, see griffin/config/base.py)

Important note regarding shortcuts:
    For compatibility with QWERTZ keyboards, one must avoid using the following
    shortcuts:
        Ctrl + Alt + Q, W, F, G, Y, X, C, V, B, N
"""

# Third party imports
from qtconsole.styles import dark_color
from qtpy import QT_VERSION
from qtpy.QtGui import QFont, QFontDatabase

# Local imports
from griffin.config.manager import CONF
from griffin.py3compat import to_text_string
from griffin.utils import syntaxhighlighters as sh


def font_is_installed(font):
    """Check if font is installed"""
    db = QFontDatabase() if QT_VERSION.startswith("5") else QFontDatabase
    return [fam for fam in db.families() if str(fam) == font]


def get_family(families):
    """Return the first installed font family in family list"""
    if not isinstance(families, list):
        families = [ families ]
    for family in families:
        if font_is_installed(family):
            return family
    else:
        print("Warning: None of the following fonts is installed: %r" % families)  # griffin: test-skip
        return QFont().family()


FONT_CACHE = {}

def get_font(section='appearance', option='font', font_size_delta=0):
    """Get console font properties depending on OS and user options"""
    font = FONT_CACHE.get((section, option, font_size_delta))

    if font is None:
        families = CONF.get(section, option+"/family", None)

        if families is None:
            return QFont()

        family = get_family(families)
        weight = QFont.Normal
        italic = CONF.get(section, option+'/italic', False)

        if CONF.get(section, option+'/bold', False):
            weight = QFont.Bold

        size = CONF.get(section, option+'/size', 9) + font_size_delta
        font = QFont(family, size, weight)
        font.setItalic(italic)
        FONT_CACHE[(section, option, font_size_delta)] = font

    size = CONF.get(section, option+'/size', 9) + font_size_delta
    if size > 0:
        font.setPointSize(size)
    return font


def set_font(font, section='appearance', option='font'):
    """Set font properties in our config system."""
    CONF.set(section, option+'/family', to_text_string(font.family()))
    CONF.set(section, option+'/size', float(font.pointSize()))
    CONF.set(section, option+'/italic', int(font.italic()))
    CONF.set(section, option+'/bold', int(font.bold()))

    # This function is only used to set fonts that were changed through
    # Preferences. And in that case it's not possible to set a delta.
    font_size_delta = 0

    FONT_CACHE[(section, option, font_size_delta)] = font


def get_color_scheme(name):
    """Get syntax color scheme"""
    color_scheme = {}
    for key in sh.COLOR_SCHEME_KEYS:
        color_scheme[key] = CONF.get(
            "appearance",
            "%s/%s" % (name, key),
            default=sh.COLOR_SCHEME_DEFAULT_VALUES[key])
    return color_scheme


def set_color_scheme(name, color_scheme, replace=True):
    """Set syntax color scheme"""
    section = "appearance"
    names = CONF.get("appearance", "names", [])
    for key in sh.COLOR_SCHEME_KEYS:
        option = "%s/%s" % (name, key)
        value = CONF.get(section, option, default=None)
        if value is None or replace or name not in names:
            CONF.set(section, option, color_scheme[key])
    names.append(to_text_string(name))
    CONF.set(section, "names", sorted(list(set(names))))


def set_default_color_scheme(name, replace=True):
    """Reset color scheme to default values"""
    assert name in sh.COLOR_SCHEME_NAMES
    set_color_scheme(name, sh.get_color_scheme(name), replace=replace)


def is_dark_font_color(color_scheme):
    """Check if the font color used in the color scheme is dark."""
    color_scheme = get_color_scheme(color_scheme)
    font_color, fon_fw, fon_fs = color_scheme['normal']
    return dark_color(font_color)


def is_dark_interface():
    ui_theme = CONF.get('appearance', 'ui_theme')
    color_scheme = CONF.get('appearance', 'selected')
    if ui_theme == 'dark':
        return True
    elif ui_theme == 'automatic':
        if not is_dark_font_color(color_scheme):
            return True
        else:
            return False
    else:
        return False


for _name in sh.COLOR_SCHEME_NAMES:
    set_default_color_scheme(_name, replace=False)
