# -*- coding: utf-8 -*-

# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""Griffin Language Server Protocol Client client handler routines."""

import logging

from griffin.plugins.completion.api import CompletionRequestTypes
from griffin.plugins.completion.providers.languageserver.decorators import (
    handles, send_response)

logger = logging.getLogger(__name__)


class ClientProvider:
    @handles(CompletionRequestTypes.CLIENT_REGISTER_CAPABILITY)
    @send_response
    def handle_register_capability(self, params):
        """TODO: Handle the glob patterns of the files to watch."""
        logger.debug('Register Capability: {0}'.format(params))
        return {}
