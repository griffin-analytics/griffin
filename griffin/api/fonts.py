# -*- coding: utf-8 -*-
#

# 
# (see griffin/__init__.py for details)

"""
Helper classes to get and set the fonts used in Griffin.
"""

# Standard library imports
from typing import Optional

# Third-party imports
from qtpy.QtGui import QFont

# Local imports
from griffin.config.gui import get_font


class GriffinFontType:
    """
    Font types used in Griffin plugins and the entire application.

    Notes
    -----
    * This enum is meant to be used to get the QFont object corresponding to
      each type.
    * The names associated to the values in this enum depend on historical
      reasons that go back to Griffin 2 and are not easy to change now.
    * Monospace is the font used used in the Editor, IPython console and
      History; Interface is used by the entire Griffin app; and
      MonospaceInterface is used, for instance, by the Variable Explorer and
      corresponds to Monospace font resized to look good against the
      Interface one.
    """
    Monospace = 'font'
    Interface = 'app_font'
    MonospaceInterface = 'monospace_app_font'


class GriffinFontsMixin:
    """Mixin to get the different Griffin font types from our config system."""

    @classmethod
    def get_font(
        cls,
        font_type: str,
        font_size_delta: Optional[int] = 0
    ) -> QFont:
        """
        Get a font type as a QFont object.

        Parameters
        ----------
        font_type: str
            A Griffin font type. This must be one of the `GriffinFontType` enum
            values.
        font_size_delta: int, optional
            Small increase or decrease over the default font size. The default
            is 0.
        """
        return get_font(option=font_type, font_size_delta=font_size_delta)
