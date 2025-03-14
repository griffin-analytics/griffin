# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
#

"""Tests for pyenv.py"""

import sys
import time

import pytest

from griffin.config.base import running_in_ci
from griffin.utils.programs import find_program
from griffin.utils.pyenv import get_list_pyenv_envs, get_list_pyenv_envs_cache


if not find_program('pyenv'):
    pytest.skip("Requires pyenv to be installed", allow_module_level=True)


@pytest.mark.skipif(not running_in_ci(), reason="Only meant for CIs")
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="Only runs on Linux")
def test_get_list_pyenv_envs():
    output = get_list_pyenv_envs()
    expected_envs = ['Pyenv: 3.8.1']
    assert set(expected_envs) == set(output.keys())


@pytest.mark.skipif(not running_in_ci(), reason="Only meant for CIs")
@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="Only runs on Linux")
def test_get_list_pyenv_envs_cache():
    time0 = time.time()
    output = get_list_pyenv_envs_cache()
    time1 = time.time()

    assert output != {}
    assert (time1 - time0) < 0.01
