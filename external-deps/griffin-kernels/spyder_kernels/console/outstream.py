# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Griffin Kernels Contributors
#
# 
# (see griffin_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Custom Griffin Outstream class.
"""
import os
import sys

from ipykernel.iostream import OutStream


class TTYOutStream(OutStream):
    """Subclass of OutStream that represents a TTY."""

    def __init__(self, session, pub_thread, name, pipe=None, echo=None, *,
                 watchfd=True):
        super().__init__(session, pub_thread, name, pipe,
                         echo=echo, watchfd=watchfd, isatty=True)

    def _flush(self):
        """This is where the actual send happens.

        _flush should generally be called in the IO thread,
        unless the thread has been destroyed (e.g. forked subprocess).

        NOTE: Overrided method to be able to filter messages.
        See griffin-ide/griffin#22181
        """
        self._flush_pending = False
        self._subprocess_flush_pending = False

        if self.echo is not None:
            try:
                self.echo.flush()
            except OSError as e:
                if self.echo is not sys.__stderr__:
                    print(f"Flush failed: {e}", file=sys.__stderr__)

        for parent, data in self._flush_buffers():
            # Messages that will not be printed to the console. This allows us
            # to deal with issues such as griffin-ide/griffin#22181
            filter_messages = ["Parent poll failed."]

            if data and not any(
                [message in data for message in filter_messages]
            ):
                # FIXME: this disables Session's fork-safe check,
                # since pub_thread is itself fork-safe.
                # There should be a better way to do this.
                self.session.pid = os.getpid()
                content = {"name": self.name, "text": data}
                msg = self.session.msg("stream", content, parent=parent)

                # Each transform either returns a new
                # message or None. If None is returned,
                # the message has been 'used' and we return.
                for hook in self._hooks:
                    msg = hook(msg)
                    if msg is None:
                        return

                self.session.send(
                    self.pub_thread,
                    msg,
                    ident=self.topic,
                )
