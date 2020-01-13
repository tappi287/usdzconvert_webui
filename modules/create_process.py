import os
import sys
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


def create_piped_process(arguments: Union[str, Iterable], current_working_directory: Path, env=None):
    _logger.debug('Running command line with arguments:\n%s\nIn cwd: %s', arguments, current_working_directory)

    my_env = dict()
    my_env.update(os.environ)
    my_env.update(env or dict())

    if sys.platform == 'win32':
        process = sp.Popen(arguments, cwd=current_working_directory.as_posix(),
                           env=my_env, stdout=sp.PIPE, stderr=sp.STDOUT,
                           creationflags=IDLE_PRIORITY_CLASS)
    else:
        process = sp.Popen(arguments, cwd=current_working_directory.as_posix(),
                           env=my_env, stdout=sp.PIPE, stderr=sp.STDOUT)

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
                 # optional OS enironment
                 env: dict = None,
                 # Thread id reported with callbacks
                 identifier: int = 0,
                 # Callbacks
                 finished_callback=None, failed_callback=None, status_callback=None):
        super(RunProcess, self).__init__()

        self.args = args
        self.cwd: Path = cwd
        self.env = env or dict()
        self.identifier = identifier

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
        self.process_exitcode = -1

        self.event = threading.Event()

    @staticmethod
    def _dummy_callback(*args, **kwargs):
        _logger.info('Dummy callback called: %s %s', args, kwargs)

    def process_log_callback(self, message: str):
        self.status_callback(self.identifier, message)

    def run(self):
        # Reset thread event
        self.event.clear()

        # Run in own thread to keep parent thread ready for abort signals
        if not self._start_process():
            self.failed_callback(self.identifier, 'Process could not be started.')
            return

        # Wait until process finished or aborted
        while not self.event.is_set():
            self.event.wait()

        # Process result unsuccessful
        if self.process_exitcode != 0:
            self.failed_callback(self.identifier, 'Process returned with error code.')
            return

        # Exit successfully
        self.finished_callback(self.identifier)

    def _start_process(self):
        """ Start process and log to file and stdout """
        try:
            self.process = create_piped_process(self.args, self.cwd, self.env)
            _logger.info('Process started.')
        except Exception as e:
            _logger.error(e, exc_info=1)
            return False

        # Log STDOUT in own thread to keep parent thread ready for abort signals
        log_thread = threading.Thread(target=self._process_log_loop)
        log_thread.start()
        return True

    def _process_log_loop(self):
        """ Reads and writes process stdout to log until process ends """
        with self.process.stdout:
            log_subprocess_output(self.process.stdout, self.process_log_callback)

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
