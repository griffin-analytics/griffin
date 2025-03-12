# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016 Pepijn Kenter.
# Copyright (c) 2019- Griffin Project Contributors
#
# Components of objectbrowser originally distributed under
# the MIT (Expat) license. ;
# see NOTICE.txt in the Griffin root directory for details
# -----------------------------------------------------------------------------


"""
griffin.plugins.variableexplorer.widgets.objectexplorer
======================================================

Object explorer widget.
"""

from .attribute_model import DEFAULT_ATTR_COLS, DEFAULT_ATTR_DETAILS
from .tree_item import TreeItem
from .tree_model import TreeModel, TreeProxyModel
from .toggle_column_mixin import ToggleColumnTreeView
from .objectexplorer import ObjectExplorer
