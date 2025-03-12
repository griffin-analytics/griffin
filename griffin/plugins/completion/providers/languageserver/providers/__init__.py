# -*- coding: utf-8 -*-

# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""Griffin Language Server Protocol Client method providers."""

from .document import DocumentProvider
from .window import WindowProvider
from .workspace import WorkspaceProvider
from .client import ClientProvider


class LSPMethodProviderMixIn(DocumentProvider, WindowProvider,
                             WorkspaceProvider, ClientProvider):
    pass
