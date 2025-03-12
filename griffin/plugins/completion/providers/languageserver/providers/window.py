# -*- coding: utf-8 -*-

# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""Griffin Language Server Protocol Client window handler routines."""

import logging

from griffin.plugins.completion.api import CompletionRequestTypes
from griffin.plugins.completion.providers.languageserver.decorators import (
    handles)

logger = logging.getLogger(__name__)


class WindowProvider:
    @handles(CompletionRequestTypes.WINDOW_SHOW_MESSAGE)
    def process_show_message(self, response, *args):
        """Handle window/showMessage notifications from LSP server."""
        logger.debug("Received showMessage: %r" % response)

    @handles(CompletionRequestTypes.WINDOW_LOG_MESSAGE)
    def process_log_message(self, response, *args):
        """Handle window/logMessage notifications from LSP server."""
        logger.debug("Received logMessage: %r" % response)
