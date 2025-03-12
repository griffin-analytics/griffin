# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
#
'''
Tests for editor panels.
'''

# Third party imports
import pytest

# Local imports
from griffin.utils.qthelpers import qapplication
from griffin.plugins.editor.panels.linenumber import LineNumberArea
from griffin.plugins.editor.panels.edgeline import EdgeLine
from griffin.plugins.editor.panels.scrollflag import ScrollFlagArea
from griffin.plugins.editor.panels.indentationguides import IndentationGuide
from griffin.plugins.editor.widgets.codeeditor import CodeEditor


# --- Fixtures
# -----------------------------------------------------------------------------
def construct_editor(*args, **kwargs):
    app = qapplication()
    editor = CodeEditor(parent=None)
    kwargs['language'] = 'Python'
    editor.setup_editor(*args, **kwargs)
    return editor


# --- Tests
# -----------------------------------------------------------------------------
@pytest.mark.parametrize('state', [True, False])
@pytest.mark.parametrize('setting, panelclass', [
    ('linenumbers', LineNumberArea),
    ('edge_line', EdgeLine),
    ('scrollflagarea', ScrollFlagArea),
    ('indent_guides', IndentationGuide),
])
def test_activate_panels(setting, panelclass, state):
    """Test activate/deactivate of editors Panels.

    Also test that the panel is added to the editor.
    """
    kwargs = {}
    kwargs[setting] = state
    editor = construct_editor(**kwargs)

    found = False
    for panel in editor.panels:
        if isinstance(panel, panelclass):
            assert panel.enabled == state
            found = True
    assert found


if __name__ == '__main__':
    pytest.main()
