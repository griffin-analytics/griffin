# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""
griffin.plugins.preferences
==========================

Preferences plugin
"""

from griffin.api.plugins import Plugins


# We consider these to be the plugins with the most important pages. So, we'll
# show those pages as the first entries in the config dialog
MOST_IMPORTANT_PAGES = [
    Plugins.Appearance,
    Plugins.Application,
    Plugins.MainInterpreter,
    Plugins.Shortcuts,
]
