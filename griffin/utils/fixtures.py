# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
#

"""Testing utilities to be used with pytest."""

# Standard library imports
import shutil

# Third party imports
import pytest

from griffin.config.user import UserConfig
from griffin.config.main import CONF_VERSION, DEFAULTS


@pytest.fixture
def tmpconfig(tmpdir, request):
    path = str(tmpdir)
    default_kwargs = {
        'name': 'griffin-test',
        'path': path,
        'defaults': DEFAULTS,
        'load': True,
        'version': CONF_VERSION,
        'backup': True,
        'raw_mode': True,
        'remove_obsolete': False,
    }

    conf = UserConfig(**default_kwargs)

    def fin():
        """Fixture finalizer to delete the temporary CONF element."""
        shutil.rmtree(path)

    request.addfinalizer(fin)

    return conf
