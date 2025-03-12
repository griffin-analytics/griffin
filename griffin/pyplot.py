# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Griffin Project Contributors
#
# Distributed under the terms of the MIT License
# (see griffin/__init__.py for details)
# -----------------------------------------------------------------------------


"""
Import guiqwt's pyplot module or matplotlib's pyplot.
"""


try:
    from guiqwt.pyplot import *
except Exception:
    from matplotlib.pyplot import *
