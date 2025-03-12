# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""
Python environments general utilities
"""

from griffin.utils.conda import get_list_conda_envs
from griffin.utils.pyenv import get_list_pyenv_envs


def get_list_envs():
    """
    Get the list of environments in the system.

    Currently detected conda and pyenv based environments.
    """
    conda_env = get_list_conda_envs()
    pyenv_env = get_list_pyenv_envs()

    return {**conda_env, **pyenv_env}
