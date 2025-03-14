# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""Module checking Griffin installation requirements"""

# Third-party imports
from packaging.version import parse


def show_warning(message):
    """Show warning using Tkinter if available"""
    try:
        # If tkinter is installed (highly probable), show an error pop-up.
        # From https://stackoverflow.com/a/17280890/438386
        import tkinter as tk
        root = tk.Tk()
        root.title("Griffin")
        label = tk.Label(root, text=message, justify='left')
        label.pack(side="top", fill="both", expand=True, padx=20, pady=20)
        button = tk.Button(root, text="OK", command=root.destroy)
        button.pack(side="bottom", fill="none", expand=True)
        root.mainloop()
    except Exception:
        pass

    raise RuntimeError(message)


def check_qt():
    """Check Qt binding requirements"""
    qt_infos = dict(
        pyqt5=("PyQt5", "5.15"),
        pyside2=("PySide2", "5.15"),
        pyqt6=("PyQt6", "6.5"),
        pyside6=("PySide6", "6.5")
    )

    try:
        import qtpy
        package_name, required_ver = qt_infos[qtpy.API]
        actual_ver = qtpy.QT_VERSION

        if (
            actual_ver is None
            or parse(actual_ver) < parse(required_ver)
        ):
            show_warning("Please check Griffin installation requirements:\n"
                         "%s %s+ is required (found %s)."
                         % (package_name, required_ver, actual_ver))
    except ImportError:
        show_warning("Failed to import qtpy.\n"
                     "Please check Griffin installation requirements:\n\n"
                     "qtpy 1.2.0+ and\n"
                     "%s %s+\n\n"
                     "are required to run Griffin."
                     % (qt_infos['pyqt5']))
