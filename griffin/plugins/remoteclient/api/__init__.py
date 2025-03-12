# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""
griffin.plugins.remoteclient.api
===============================

Remote Client Plugin API.
"""

from griffin.plugins.remoteclient.api.manager import GriffinRemoteAPIManager  # noqa

# ---- Constants
# -----------------------------------------------------------------------------

# Max number of logged messages from the client that will be saved.
MAX_CLIENT_MESSAGES = 1000


class RemoteClientActions:
    ManageConnections = "manage connections"


class RemoteClientMenus:
    RemoteConsoles = "remote_consoles_menu"


class RemoteConsolesMenuSections:
    ManagerSection = "manager_section"
    ConsolesSection = "consoles_section"
