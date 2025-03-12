# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
#

"""
Tests for the Griffin kernel
"""

import pytest

from griffin.config.manager import CONF
from griffin.plugins.ipythonconsole.utils.kernelspec import GriffinKernelSpec


def test_python_interpreter(tmpdir):
    """Test the validation of the python interpreter."""
    # Set a non existing python interpreter
    interpreter = str(tmpdir.mkdir('interpreter').join('python'))
    CONF.set('main_interpreter', 'default', False)
    CONF.set('main_interpreter', 'custom', True)
    CONF.set('main_interpreter', 'executable', interpreter)

    # Create a kernel spec
    kernel_spec = GriffinKernelSpec()

    # Assert that the python interprerter is the default one
    assert interpreter not in kernel_spec.argv
    assert CONF.get('main_interpreter', 'default')
    assert not CONF.get('main_interpreter', 'custom')


if __name__ == "__main__":
    pytest.main()
