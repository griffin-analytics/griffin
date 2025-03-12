# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""
griffin.plugins.remoteclient.widgets
===================================

Widgets for the Remote Client plugin.
"""


class AuthenticationMethod:
    """Enum for the different authentication methods we support."""

    Password = "password_login"
    KeyFile = "keyfile_login"
    ConfigFile = "configfile_login"
