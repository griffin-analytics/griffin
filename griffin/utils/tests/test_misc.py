# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
#

"""
Tests for misc.py
"""

# Standard library imports
import os

# Test library imports
import pytest

# Local imports
from griffin.utils.misc import get_common_path


def test_get_common_path():
    """Test getting the common path."""
    if os.name == 'nt':
        assert get_common_path(['D:\\Python\\griffin-v21\\griffin\\widgets',
                                'D:\\Python\\griffin\\griffin\\utils',
                                'D:\\Python\\griffin\\griffin\\widgets',
                                'D:\\Python\\griffin-v21\\griffin\\utils',
                                ]) == 'D:\\Python'
    else:
        assert get_common_path(['/Python/griffin-v21/griffin.widgets',
                                '/Python/griffin/griffin.utils',
                                '/Python/griffin/griffin.widgets',
                                '/Python/griffin-v21/griffin.utils',
                                ]) == '/Python'


if __name__ == "__main__":
    pytest.main()
