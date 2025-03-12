# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""
griffin.plugins.ipythonconsole
=============================

IPython Console plugin based on QtConsole
"""

from griffin.config.base import is_stable_version


# Use this variable, which corresponds to the html dash symbol, for any command
# that requires a dash below. That way users will be able to copy/paste
# commands from the kernel error message directly to their terminals.
_d = '&#45;'

# Required version of Griffin-kernels
GRIFFIN_KERNELS_MIN_VERSION = "3.1.0.dev0"
GRIFFIN_KERNELS_MAX_VERSION = '3.2.0'
GRIFFIN_KERNELS_VERSION = (
    f'>={GRIFFIN_KERNELS_MIN_VERSION},<{GRIFFIN_KERNELS_MAX_VERSION}'
)

if is_stable_version(GRIFFIN_KERNELS_MIN_VERSION):
    GRIFFIN_KERNELS_CONDA = (
        f'conda install griffin{_d}kernels={GRIFFIN_KERNELS_MIN_VERSION[:-2]}'
    )
    GRIFFIN_KERNELS_PIP = (
        f'pip install griffin{_d}kernels=={GRIFFIN_KERNELS_MIN_VERSION[:-1]}*'
    )
else:
    GRIFFIN_KERNELS_CONDA = (
        f'conda install {_d}c conda{_d}forge/label/griffin_kernels_rc {_d}c '
        f'conda{_d}forge griffin{_d}kernels={GRIFFIN_KERNELS_MIN_VERSION}'
    )
    GRIFFIN_KERNELS_PIP = (
        f'pip install griffin{_d}kernels=={GRIFFIN_KERNELS_MIN_VERSION}'
    )


class GriffinKernelError(RuntimeError):
    """
    Error to be shown in the IPython console.

    Notes
    -----
    * Use this exception if you want to show a nice formatted error in the
      current console instead of a long and hard-to-read traceback.
    * This should only be used for errors whose cause we are certain of.
    """
