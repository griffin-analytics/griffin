# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
#

"""
Testing utilities for Editor/EditorStack widgets to be used with pytest.
"""

# Local imports
from griffin.plugins.editor.tests.conftest import (
    editor_plugin,
    editor_plugin_open_files,
    python_files,
)
from griffin.plugins.completion.tests.conftest import (
    completion_plugin_all_started,
    completion_plugin_all,
    qtbot_module,
)
from griffin.plugins.editor.widgets.editorstack.tests.conftest import (
    setup_editor,
    completions_editor,
)
