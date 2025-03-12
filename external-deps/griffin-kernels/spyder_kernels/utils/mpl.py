# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Griffin Kernels Contributors
#
# 
# (see griffin_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""Matplotlib utilities."""

from griffin_kernels.utils.misc import is_module_installed


# Inline backend
if is_module_installed('matplotlib_inline'):
    inline_backend = 'module://matplotlib_inline.backend_inline'
else:
    inline_backend = 'module://ipykernel.pylab.backend_inline'


# Mapping of matlotlib backends options to Griffin
MPL_BACKENDS_TO_GRIFFIN = {
    'inline': 'inline',  # For Matplotlib >=3.9
    inline_backend: "inline",  # For Matplotlib <3.9
    'qt5agg': 'qt',
    'qtagg': 'qt',  # For Matplotlib 3.5+
    'tkagg': 'tk',
    'macosx': 'osx',
}


def automatic_backend():
    """Get Matplolib automatic backend option."""
    if is_module_installed('PyQt5'):
        auto_backend = 'qt'
    elif is_module_installed('_tkinter'):
        auto_backend = 'tk'
    else:
        auto_backend = 'inline'
    return auto_backend
