import os
from pathlib import Path
from typing import Iterator, Union

from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.utils import secure_filename

from modules.create_process import RunProcess
from modules.file_mgr import FileManager
from modules.globals import get_current_modules_dir
from modules.log import setup_logger
from modules.usdzconvert_args import create_usdzconvert_arguments, usd_env
from modules.site import Urls, JobFormFields

_logger = setup_logger(__name__)


class ConversionJob:
    id_count = 0

    class States:
        queued = 0
        in_progress = 1
        finished = 2
        failed = 3

    state_names = {States.queued: 'Queued', States.in_progress: 'In progress',
                   States.finished: 'finished', States.failed: 'failed'}

    def __init__(self, job_dir: Path, files: dict, form: ImmutableMultiDict):
        self.job_dir = job_dir
        self.files = files
        self.option_args = self.create_options(form)
        self.additional_args = form.get(JobFormFields.additional_args, '')

        self.state = -1  # One of self.States
        self.progress = int()  # Progress 0-100
        self.completed = False

        self.process_messages = str()
        self.errors = str()

        ConversionJob.id_count += 1
        self.id = ConversionJob.id_count

    def create_options(self, form: ImmutableMultiDict) -> list:
        option_args = list()
        for option in JobFormFields.option_fields:
            value = form.get(option.id)

            if option.input_type == 'checkbox':
                if value == 'on':
                    option_args.append(f'-{option.id}')
            else:
                if value:
                    option_args.append(f'-{option.id}')
                    option_args.append(value)

        return option_args

    @property
    def out_file(self) -> Path:
        return self.files.get('out_file', dict()).get('file_path', Path('.'))

    @out_file.setter
    def out_file(self, val: Path):
        self.files['out_file']['file_path'] = val

    def list_files(self) -> Iterator[str]:
        for file_id, file_entry in self.files.items():
            yield file_id, file_entry.get("file_path").name, file_entry.get("use_channel")

    def message_updates(self, msg):
        self.process_messages += msg
        self.progress = min(self.progress, self.progress + 15)

    def download_filename(self) -> Union[None, str]:
        if self.out_file.exists() and self.completed:
            return f'{os.path.split(Urls.static_downloads)[1]}/' \
                   f'{secure_filename(self.job_dir.name)}/{self.out_file.name}'

    def direct_download_url(self) -> Union[None, str]:
        if self.out_file.exists() and self.completed:
            return f'{Urls.static_downloads}/' \
                   f'{secure_filename(self.job_dir.name)}/{self.out_file.name}'

    def get_state(self) -> str:
        return self.state_names.get(self.state, 'No job state set')

    def set_complete(self):
        # Move Job file to static, public available, directory
        static_file_path = FileManager.move_to_static_dir(self.out_file, self.job_dir.name)

        if static_file_path is None:
            _logger.error('Could not move final Job file. Setting job failed.')
            self.set_failed('Could not move USDZ to static directory.')
            return

        _logger.info('Moved Job result file to static directory: %s', static_file_path)
        self.out_file = static_file_path
        self.state = self.States.finished
        self.completed = True
        self.progress = 100

    def set_error(self, error_message: str):
        self.errors = error_message

    def set_in_progress(self):
        self.state = self.States.in_progress
        self.progress = 5

    def set_failed(self, error_msg: str = ''):
        self.state = self.States.failed
        self.completed = True
        if error_msg:
            self.set_error(error_msg)
        self.progress = 0


class JobManager:
    _current_job: Union[None, ConversionJob] = None
    _queue = list()
    _jobs = list()

    @classmethod
    def get_jobs(cls) -> Iterator[ConversionJob]:
        return cls._jobs

    @classmethod
    def current_job(cls) -> Union[None, ConversionJob]:
        if cls.current_job:
            return cls._current_job

    @classmethod
    def add_job(cls, job: ConversionJob):
        if job in cls._queue or job is cls._current_job:
            return

        cls._jobs.append(job)

        cls._queue.append(job)
        job.state = job.States.queued

        if not cls._current_job or cls._current_job.completed:
            cls.run_job_queue()

    @classmethod
    def remove_job(cls, job_id) -> bool:
        for job in cls.get_jobs():
            _logger.debug('Mgr iterating job: %s', job.id)
            if str(job.id) == str(job_id):
                _logger.debug('Deleting job: %s', job_id)
                cls._jobs.remove(job)
                del job
                return True

        return False

    @classmethod
    def _get_next_job(cls) -> Union[None, ConversionJob]:
        if cls._queue:
            return cls._queue.pop(0)
        return None

    @classmethod
    def get_job_by_id(cls, job_id) -> Union[None, ConversionJob]:
        for job in cls.get_jobs():
            if str(job_id) == str(job.id):
                return job
        else:
            return

    @staticmethod
    def create_job_arguments(job: ConversionJob) -> list:
        args = list()

        # Add texture maps file arguments
        for file_id, file_entry in job.files.items():
            file_path = Path(file_entry.get("file_path"))

            if file_id in ('scene_file', 'out_file'):
                args.append(file_path.as_posix())  # inputFile/outputFile arguments
                continue

            args.append(f'-{file_id}')

            channel = file_entry.get('use_channel')
            if channel:
                _logger.info('Adding channel argument: %s', channel)
                args.append(channel.lower())
            args.append(file_path.as_posix())

        # Add options
        if job.option_args:
            args += job.option_args

        # Add additional arguments
        if job.additional_args:
            for a in job.additional_args.split(' '):
                args.append(a)

        return args

    @classmethod
    def run_job_queue(cls):
        job = cls._get_next_job()
        if not job:
            return

        cls._current_job = job
        job_arguments = create_usdzconvert_arguments(cls.create_job_arguments(job))
        job.set_in_progress()

        process_thread = RunProcess(job_arguments, job.job_dir, usd_env(),
                                    cls.job_finished, cls.job_failed, job.message_updates)
        process_thread.start()

    @classmethod
    def job_failed(cls, error: str):
        _logger.info('Job processing failed: %s', error)
        cls.current_job().set_failed(error)
        cls.run_job_queue()

    @classmethod
    def job_finished(cls):
        _logger.info('Job finished.')
        cls.current_job().set_complete()
        cls.run_job_queue()
