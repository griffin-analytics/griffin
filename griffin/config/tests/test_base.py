# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Griffin Project Contributors
#
# Distributed under the terms of the MIT License
# (see griffin/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the griffin.config.base module.
"""

# Standard library imports
from importlib import reload
import os
import os.path as osp
from pathlib import Path
import shutil
import sys


# Third party imports
import pytest
from griffin_kernels.utils.pythonenv import is_conda_env

# Local imports
import griffin.config.base
from griffin.utils.conda import get_list_conda_envs


# ============================================================================
# ---- Tests
# ============================================================================
def test_is_stable_version():
    """Test that stable and non-stable versions are recognized correctly."""
    for stable_version in ['3.3.0', '2', ('0', '5')]:
        assert griffin.config.base.is_stable_version(stable_version)
    for not_stable_version in ['4.0.0b1', '3.3.2.dev0',
                               'beta', ('2', '0', 'alpha')]:
        assert not griffin.config.base.is_stable_version(not_stable_version)


@pytest.mark.parametrize('use_dev_config_dir', [True, False])
def test_get_conf_path(monkeypatch, use_dev_config_dir):
    """Test that the config dir path is set under dev and release builds."""
    monkeypatch.setenv('GRIFFIN_USE_DEV_CONFIG_DIR', str(use_dev_config_dir))
    monkeypatch.setenv('GRIFFIN_PYTEST', '')
    reload(griffin.config.base)
    conf_path = griffin.config.base.get_conf_path()
    assert conf_path
    assert ((osp.basename(conf_path).split('-')[-1] == 'dev')
            == use_dev_config_dir)
    assert osp.isdir(conf_path)
    monkeypatch.undo()
    reload(griffin.config.base)


@pytest.mark.skipif(
    not griffin.config.base.running_in_ci(), reason="Only works on CIs"
)
@pytest.mark.skipif(
    not is_conda_env(sys.prefix), reason='Only works with Anaconda'
)
def test_is_conda_based_app():
    """Test that is_conda_based_app is working as expected."""
    # Get conda env to use
    pyexec = get_list_conda_envs()['Conda: jedi-test-env'][0]

    # Get env's root
    env_root = (
        Path(pyexec).parents[0] if os.name == "nt" else Path(pyexec).parents[1]
    )

    # Create dir and file necessary to detect the app
    menu_dir = env_root / "Menu"
    menu_dir.mkdir()
    (menu_dir / "conda-based-app").touch()

    # Check the env is detected as belonging to the app
    assert griffin.config.base.is_conda_based_app(pyexec=pyexec)

    # Remove added dir
    shutil.rmtree(menu_dir, ignore_errors=True)


if __name__ == '__main__':
    pytest.main()
