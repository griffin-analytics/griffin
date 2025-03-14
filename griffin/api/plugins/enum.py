# -*- coding: utf-8 -*-
#

# 
# (see griffin/__init__.py for details)

"""Enum of Griffin internal plugins."""


class Plugins:
    """
    Convenience class for accessing Griffin internal plugins.
    """
    All = "all"   # Wildcard to populate REQUIRES with all available plugins
    Appearance = 'appearance'
    Application = 'application'
    Completions = 'completions'
    Console = 'internal_console'
    Debugger = 'debugger'
    Editor = 'editor'
    Explorer = 'explorer'
    ExternalTerminal = 'external_terminal'
    Find = 'find_in_files'
    Help = 'help'
    History = 'historylog'
    IPythonConsole = 'ipython_console'
    Layout = 'layout'
    MainInterpreter = 'main_interpreter'
    MainMenu = 'mainmenu'
    OnlineHelp = 'onlinehelp'
    OutlineExplorer = 'outline_explorer'
    Plots = 'plots'
    Preferences = 'preferences'
    Profiler = 'profiler'
    Projects = 'project_explorer'
    Pylint = 'pylint'
    PythonpathManager = 'pythonpath_manager'
    RemoteClient = 'remoteclient'
    Run = 'run'
    Shortcuts = 'shortcuts'
    StatusBar = 'statusbar'
    Switcher = 'switcher'
    Toolbar = "toolbar"
    Tours = 'tours'
    UpdateManager = 'update_manager'
    VariableExplorer = 'variable_explorer'
    WorkingDirectory = 'workingdir'


class DockablePlugins:
    Console = 'internal_console'
    Debugger = 'debugger'
    Editor = 'editor'
    Explorer = 'explorer'
    Find = 'find_in_files'
    Help = 'help'
    History = 'historylog'
    IPythonConsole = 'ipython_console'
    OnlineHelp = 'onlinehelp'
    OutlineExplorer = 'outline_explorer'
    Plots = 'plots'
    Profiler = 'profiler'
    Projects = 'project_explorer'
    Pylint = 'pylint'
    VariableExplorer = 'variable_explorer'
