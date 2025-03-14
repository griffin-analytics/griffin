# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Griffin Kernels Contributors
#
# 
# (see griffin_kernels/__init__.py for details)
# -----------------------------------------------------------------------------
"""
Comms Utilities
"""

import sys
import threading


class WriteContext(object):
    class_lock = threading.RLock()
    def __init__(self, prefix):
        self.prefix = prefix

    def __enter__(self):
        self.class_lock.acquire()

        self.files = [sys.stdout, sys.stderr]
        self.saved_writes = [f.write for f in self.files]

        thread_id = threading.get_ident()

        for f in self.files:
            f.write = WriteWrapper(f.write, self.prefix, thread_id)
  
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            for f, old_write in zip(self.files, self.saved_writes):
                f.write = old_write
        finally:
            self.class_lock.release()


class WriteWrapper(object):
    """Wrapper to warn user when text is printed."""

    def __init__(self, write, name, thread_id):
        self._write = write
        self._name = name
        self._thread_id = thread_id
        self._warning_shown = False

    def is_benign_message(self, message):
        """Determine if a message is benign in order to filter it."""
        benign_messages = [
            # Fixes griffin-ide/griffin#14928
            # Fixes griffin-ide/griffin-kernels#343
            'DeprecationWarning',
            # Fixes griffin-ide/griffin-kernels#365
            'IOStream.flush timed out',
            # Avoid unnecessary messages from set_configuration when changing
            # Matplotlib options.
            "Warning: Cannot change to a different GUI toolkit",
            "%pylab is deprecated",
            "Populating the interactive namespace",
            "\n",
            # Fixes griffin-ide/griffin#21652
            "WARNING",
            "Active device does not have an attribute",
        ]

        return any([msg in message for msg in benign_messages])

    def __call__(self, string):
        """Print warning once."""
        if self._thread_id != threading.get_ident():
            return self._write(string)

        if not self.is_benign_message(string):
            if not self._warning_shown:
                self._warning_shown = True

                # request_pdb_stop is expected to print messages.
                if self._name not in ['request_pdb_stop']:
                    self._write(
                        "\nOutput from griffin call " + repr(self._name) + ":\n"
                    )

            return self._write(string)
