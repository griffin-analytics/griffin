# -*- coding: utf-8 -*-
#

# 
# (see griffin/__init__.py for details)

"""
griffin.api.plugins
==================

Here, 'plugins' are Qt objects that can make changes to Griffin's main window
and call/connect to other plugins directly.

There are two types of plugins available:

1. GriffinPluginV2 is a plugin that does not create a new dock/pane on Griffin's
   main window. Note: GriffinPluginV2 will be renamed to GriffinPlugin once the
   migration to the new API is finished

2. GriffinDockablePlugin is a plugin that does create a new dock/pane on
   Griffin's main window.
"""

from .enum import Plugins, DockablePlugins  # noqa
from .new_api import GriffinDockablePlugin, GriffinPluginV2  # noqa
