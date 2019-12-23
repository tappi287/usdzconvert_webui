import os
import subprocess as sp
import threading
import locale
from pathlib import Path
from typing import Union, Iterable

from modules.log import setup_logger

_logger = setup_logger(__name__)

_encoding = locale.getpreferredencoding() or 'utf-8'

ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
HIGH_PRIORITY_CLASS = 0x00000080
IDLE_PRIORITY_CLASS = 0x00000040
NORMAL_PRIORITY_CLASS = 0x00000020
REALTIME_PRIORITY_CLASS = 0x00000100


def _create_process(arguments: Union[str, Iterable], current_working_directory: Path):
    _logger.debug('Running command line with arguments:\n%s\nIn cwd: %s', arguments, current_working_directory)

    my_env = dict()
    my_env.update(os.environ)

    process = sp.Popen(arguments, cwd=current_working_directory.as_posix(),
                       env=my_env, stdout=sp.PIPE, stderr=sp.STDOUT,
                       creationflags=IDLE_PRIORITY_CLASS)

    return process


def log_subprocess_output(pipe, message_callback):
    """ Redirect subprocess output to logging so it appears in console and log file """
    for line in iter(pipe.readline, b''):
        try:
            line = line.decode(encoding=_encoding)
            line = line.replace('\n', '')
        except Exception as e:
            _logger.error('Error decoding process output: %s', e)

        if line:
            _logger.info('%s', line)

            if message_callback and isinstance(line, str):
                message_callback(line)


class RunProcess(threading.Thread):
    def __init__(self, args, cwd: Path,
                 # Callbacks
                 finished_callback=None, failed_callback=None, status_callback=None):
        super(RunProcess, self).__init__()

        self.args = args
        self.cwd: Path = cwd

        # -- Prepare callbacks
        self.finished_callback = self.failed_callback = self.status_callback = self._dummy_callback

        if finished_callback:
            self.finished_callback = finished_callback
        if failed_callback:
            self.failed_callback = failed_callback
        if status_callback:
            self.status_callback = status_callback

        # Prepare workers
        self.process = None
        self.process_exitcode = None

        self.event = threading.Event()

    @staticmethod
    def _dummy_callback(*args, **kwargs):
        _logger.info('Dummy callback called: %s %s', args, kwargs)

    def run(self):
        # Reset thread event
        self.event.clear()

        # Run in own thread to keep parent thread ready for abort signals
        self._start_process()

        # Wait until process finished or aborted
        while not self.event.is_set():
            self.event.wait()

        if self.process_exitcode != 0:
            self.failed_callback()
            return

        # Exit successfully
        self.finished_callback()

    def _start_process(self):
        """ Start process and log to file and stdout """
        try:
            self.process = _create_process(self.args, self.cwd)
            _logger.info('Process started.')
        except Exception as e:
            _logger.error(e, exc_info=1)

        # Log STDOUT in own thread to keep parent thread ready for abort signals
        log_thread = threading.Thread(target=self._process_log_loop)
        log_thread.start()

    def _process_log_loop(self):
        """ Reads and writes process stdout to log until process ends """
        with self.process.stdout:
            log_subprocess_output(self.process.stdout, self.status_callback)

        _logger.info('Process stdout stream ended. Fetching exitcode.')
        self.process_exitcode = self.process.wait()
        _logger.info('Process ended with exitcode %s', self.process_exitcode)

        # Wake up parent thread
        self.event.set()

    def kill_process(self):
        if self.process:
            try:
                _logger.info('Attempting to kill process.')
                self.process.kill()
                _logger.info('Process killed.')
            except Exception as e:
                _logger.error(e)