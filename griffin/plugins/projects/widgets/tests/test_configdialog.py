# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
#

"""
Tests for configdialog.py
"""

# Standard library imports
import os.path as osp
import tempfile

# Test library imports
import pytest

# Local imports
from griffin.plugins.projects.api import EmptyProject

@pytest.fixture
def project(qtbot):
    """Set up ProjectPreferences."""
    project_dir = tempfile.mkdtemp() + osp.sep + '.griffinproject'
    project = EmptyProject(project_dir, None)
    return project


def test_projects_preferences(project):
    """Run Project Preferences."""
    assert project


if __name__ == "__main__":
    pytest.main()
