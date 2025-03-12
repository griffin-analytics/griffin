# -*- coding: utf-8 -*-

# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

import pytest

from qtpy.QtCore import QObject, Signal

from griffin.plugins.completion.providers.fallback.provider import (
    FallbackProvider)
from griffin.plugins.completion.tests.conftest import qtbot_module


class CompletionManagerMock(QObject):
    sig_recv_tokens = Signal(list)

    def handle_response(self, client, req_id, response):
        tokens = list(response['params'])
        self.sig_recv_tokens.emit(list(tokens))


@pytest.fixture(scope='module')
def fallback_completions(qtbot_module, request):
    fallback = FallbackProvider(None, {})
    completions = CompletionManagerMock(None)

    with qtbot_module.waitSignal(fallback.sig_provider_ready, timeout=30000):
        fallback.start()

    def teardown():
        fallback.shutdown()

    request.addfinalizer(teardown)

    fallback.sig_response_ready.connect(completions.handle_response)
    return fallback, completions
