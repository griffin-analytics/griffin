# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Griffin Project Contributors
#
# Distributed under the terms of the MIT License
# (see griffin/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Griffin MS Language Server Protocol v3.0 transport proxy implementation.

This module handles and processes incoming stdin messages sent by an
LSP server, then it relays the information to the actual Griffin LSP
client via ZMQ.
"""

import logging
from griffin.plugins.completion.providers.languageserver.transport.common.consumer import (
    IncomingMessageThread)

logger = logging.getLogger(__name__)


class StdioIncomingMessageThread(IncomingMessageThread):
    """Stdio socket consumer."""

    def read_num_bytes(self, n):
        return self.fd.read(n).encode('utf-8')
