# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Griffin Project Contributors
#
# 
# (see griffin/__init__.py for details)
# -----------------------------------------------------------------------------
"""
Worker manager and workers for running files long processes in non GUI
blocking threads.
"""

# Standard library imports
from collections import deque
import logging
import sys

# Third party imports
from qtpy.QtCore import (QByteArray, QObject, QProcess, QThread, QTimer,
                         Signal)

# Local imports
from griffin.py3compat import to_text_string


logger = logging.getLogger(__name__)


def handle_qbytearray(obj, encoding):
    """Qt/Python2/3 compatibility helper."""
    if isinstance(obj, QByteArray):
        obj = obj.data()

    return to_text_string(obj, encoding=encoding)


class PythonWorker(QObject):
    """
    Generic python worker for running python code on threads.

    For running processes (via QProcess) use the ProcessWorker.
    """
    sig_started = Signal(object)
    sig_finished = Signal(object, object, object)  # worker, stdout, stderr

    def __init__(self, func, args, kwargs):
        """Generic python worker for running python code on threads."""
        super(PythonWorker, self).__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._is_finished = False
        self._started = False

    def is_finished(self):
        """Return True if worker status is finished otherwise return False."""
        return self._is_finished

    def start(self):
        """Start the worker (emits sig_started signal with worker as arg)."""
        if not self._started:
            self.sig_started.emit(self)
            self._started = True

    def terminate(self):
        """Mark the worker as finished."""
        self._is_finished = True

    def _start(self):
        """Start process worker for given method args and kwargs."""
        error = None
        output = None

        try:
            output = self.func(*self.args, **self.kwargs)
        except Exception as err:
            error = err

        if not self._is_finished:
            try:
                self.sig_finished.emit(self, output, error)
            except RuntimeError:
                pass
        self._is_finished = True


class ProcessWorker(QObject):
    """Process worker based on a QProcess for non blocking UI."""

    sig_started = Signal(object)
    sig_finished = Signal(object, object, object)
    sig_partial = Signal(object, object, object)

    def __init__(self, parent, cmd_list, environ=None):
        """
        Process worker based on a QProcess for non blocking UI.

        Parameters
        ----------
        cmd_list : list of str
            Command line arguments to execute.
        environ : dict
            Process environment,
        """
        super(ProcessWorker, self).__init__(parent)
        self._result = None
        self._cmd_list = cmd_list
        self._fired = False
        self._communicate_first = False
        self._partial_stdout = None
        self._started = False

        self._timer = QTimer(self)
        self._process = QProcess(self)
        self._set_environment(environ)

        # This is necessary to pass text input to the process as part of
        # cmd_list
        self._process.setInputChannelMode(QProcess.ForwardedInputChannel)

        self._timer.setInterval(150)
        self._timer.timeout.connect(self._communicate)
        self._process.readyReadStandardOutput.connect(self._partial)

    def _get_encoding(self):
        """Return the encoding to use."""
        # It seems that in Python 3 we only need this encoding to correctly
        # decode bytes on all operating systems.
        # See griffin-ide/griffin#22546
        return 'utf-8'

    def _set_environment(self, environ):
        """Set the environment on the QProcess."""
        if environ:
            q_environ = self._process.processEnvironment()
            for k, v in environ.items():
                q_environ.insert(k, v)
            self._process.setProcessEnvironment(q_environ)

    def _partial(self):
        """Callback for partial output."""
        raw_stdout = self._process.readAllStandardOutput()
        stdout = handle_qbytearray(raw_stdout, self._get_encoding())

        if self._partial_stdout is None:
            self._partial_stdout = stdout
        else:
            self._partial_stdout += stdout

        self.sig_partial.emit(self, stdout, None)

    def _communicate(self):
        """Callback for communicate."""
        if (not self._communicate_first and
                self._process.state() == QProcess.NotRunning):
            self.communicate()
        elif self._fired:
            self._timer.stop()

    def communicate(self):
        """Retrieve information."""
        self._communicate_first = True
        self._process.waitForFinished(5000)

        enco = self._get_encoding()
        if self._partial_stdout is None:
            raw_stdout = self._process.readAllStandardOutput()
            stdout = handle_qbytearray(raw_stdout, enco)
        else:
            stdout = self._partial_stdout

        raw_stderr = self._process.readAllStandardError()
        stderr = handle_qbytearray(raw_stderr, enco)
        result = [stdout.encode(enco), stderr.encode(enco)]

        result[-1] = ''

        self._result = result

        if not self._fired:
            self.sig_finished.emit(self, result[0], result[-1])

        self._fired = True

        return result

    def close(self):
        """Close the running process."""
        self._timer.stop()
        self._process.close()
        self._process.waitForFinished(1000)

    def is_finished(self):
        """Return True if worker has finished processing."""
        return self._process.state() == QProcess.NotRunning and self._fired

    def _start(self):
        """Start process."""
        if not self._fired:
            self._partial_ouput = None
            self._process.start(self._cmd_list[0], self._cmd_list[1:])
            self._timer.start()

    def terminate(self):
        """Terminate running processes."""
        self._timer.stop()
        if self._process.state() == QProcess.Running:
            try:
                self._process.close()
                self._process.waitForFinished(1000)
            except Exception:
                pass
        self._fired = True

    def start(self):
        """Start worker."""
        if not self._started:
            self.sig_started.emit(self)
            self._started = True

    def set_cwd(self, cwd):
        """Set the process current working directory."""
        self._process.setWorkingDirectory(cwd)


class WorkerManager(QObject):
    """Manager for generic workers."""

    def __init__(self, parent=None, max_threads=10):
        super().__init__(parent=parent)
        self.parent = parent

        self._queue = deque()
        self._queue_workers = deque()
        self._threads = []
        self._workers = []
        self._timer = QTimer(self)
        self._timer_worker_delete = QTimer(self)
        self._running_threads = 0
        self._max_threads = max_threads

        # Keeps references to old workers
        # Needed to avoid C++/python object errors
        self._bag_collector = deque()

        self._timer.setInterval(333)
        self._timer.timeout.connect(self._start)
        self._timer_worker_delete.setInterval(5000)
        self._timer_worker_delete.timeout.connect(self._clean_workers)

    def _clean_workers(self):
        """Delete periodically workers in workers bag."""
        while self._bag_collector:
            self._bag_collector.popleft()
        self._timer_worker_delete.stop()

    def _start(self, worker=None):
        """Start threads and check for inactive workers."""
        if worker:
            self._queue_workers.append(worker)

        if self._queue_workers and self._running_threads < self._max_threads:
            if self.parent is not None:
                logger.debug(
                    f"Workers managed in {self.parent} -- "
                    f"In queue: {len(self._queue_workers)} -- "
                    f"Running threads: {self._running_threads} -- "
                    f"Workers: {len(self._workers)} -- "
                    f"Threads: {len(self._threads)}"
                )

            worker = self._queue_workers.popleft()
            if isinstance(worker, PythonWorker):
                self._running_threads += 1
                thread = QThread(None)
                self._threads.append(thread)

                worker.moveToThread(thread)
                worker.sig_finished.connect(thread.quit)
                thread.started.connect(worker._start)
                thread.start()
            elif isinstance(worker, ProcessWorker):
                worker._start()
        else:
            self._timer.start()

        if self._workers:
            for w in self._workers:
                if w.is_finished():
                    self._bag_collector.append(w)
                    self._workers.remove(w)

        if self._threads:
            for t in self._threads:
                if t.isFinished():
                    self._threads.remove(t)
                    self._running_threads -= 1

        if len(self._threads) == 0 and len(self._workers) == 0:
            self._timer.stop()
            self._timer_worker_delete.start()

    def create_python_worker(self, func, *args, **kwargs):
        """Create a new python worker instance."""
        worker = PythonWorker(func, args, kwargs)
        self._create_worker(worker)
        return worker

    def create_process_worker(self, cmd_list, environ=None):
        """Create a new process worker instance."""
        worker = ProcessWorker(self, cmd_list, environ=environ)
        self._create_worker(worker)
        return worker

    def terminate_all(self):
        """Terminate all worker processes."""
        for worker in self._workers:
            worker.terminate()

        for thread in self._threads:
            try:
                thread.quit()
                thread.wait()
            except Exception:
                pass

        self._queue_workers = deque()

    def _create_worker(self, worker):
        """Common worker setup."""
        worker.sig_started.connect(self._start)
        self._workers.append(worker)

# --- Local testing
# -----------------------------------------------------------------------------
def ready_print(worker, output, error):  # pragma: no cover
    """Print worker output for tests."""
    print(worker, output, error)  # griffin: test-skip


def sleeping_func(arg, secs=10, result_queue=None):
    """This methods illustrates how the workers can be used."""
    import time
    time.sleep(secs)
    if result_queue is not None:
        result_queue.put(arg)
    else:
        return arg


def local_test():  # pragma: no cover
    """Main local test."""
    from griffin.utils.qthelpers import qapplication
    app = qapplication()
    wm = WorkerManager(max_threads=3)
    for i in range(7):
        worker = wm.create_python_worker(sleeping_func, 'BOOM! {}'.format(i),
                                         secs=5)
        worker.sig_finished.connect(ready_print)
        worker.start()
    worker = wm.create_python_worker(sleeping_func, 'BOOM!', secs=5)
    worker.sig_finished.connect(ready_print)
    worker.start()

    worker = wm.create_process_worker(['conda', 'info', '--json'])
    worker.sig_finished.connect(ready_print)
    worker.start()
#    wm.terminate_all()
#    wm.terminate_all()

    sys.exit(app.exec_())


if __name__ == '__main__':  # pragma: no cover
    local_test()
