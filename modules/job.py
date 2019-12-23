from pathlib import Path
from typing import Iterator, Union

from modules.create_process import RunProcess
from modules.globals import get_current_modules_dir
from modules.log import setup_logger

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

    def __init__(self, job_dir: Path, files: dict, additional_args: str):
        self.job_dir = job_dir
        self.files = files
        self.additional_args = additional_args

        self.state = -1  # One of self.States
        self.progress = int()  # Progress 0-100
        self.completed = False

        self.process_messages = str()
        self.errors = str()

        self.id_count += 1
        self.id = self.id_count

        self.out_file = None

    def list_files(self) -> Iterator[str]:
        for file_id, file_entry in self.files.items():
            yield file_id, file_entry.get("file_path").name, file_entry.get("use_channel")

    def message_updates(self, msg):
        self.process_messages += msg

    def file(self) -> Union[None, str]:
        if Path(self.out_file).exists() and self.completed:
            return self.out_file

    def get_state(self) -> str:
        return self.state_names.get(self.state, 'No job state set')

    def set_complete(self):
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
    queue = list()

    @classmethod
    def jobs(cls):
        if cls.current_job():
            return [cls.current_job()] + cls.queue
        return cls.queue

    @classmethod
    def current_job(cls) -> Union[None, ConversionJob]:
        if cls.current_job:
            return cls._current_job

    @classmethod
    def add_job(cls, job: ConversionJob):
        if job in cls.queue or job is cls._current_job:
            return

        cls.queue.append(job)
        job.state = job.States.queued

        if not cls._current_job or cls._current_job.completed:
            cls.run_job_queue()

    @classmethod
    def _get_next_job(cls) -> Union[None, ConversionJob]:
        if cls.queue:
            return cls.queue.pop(0)
        return None

    @staticmethod
    def create_job_arguments(job: ConversionJob) -> list:
        args = list()

        # Add binary argument
        args.append(Path(Path(get_current_modules_dir()) / 'instance' / 'example.bat').as_posix())

        # Add texture maps file arguments
        for file_id, file_entry in job.files.items():
            path = Path(file_entry.get("file_path"))

            if file_id == 'scene_file':
                out_file = path.with_suffix('.usdz').as_posix()
                args.append(path.as_posix())  # inputFile
                args.append(out_file)  # outputFile
                job.out_file = path.as_posix()
                continue

            args.append(f'-{file_id}')

            channel = str(file_entry.get("use_channel")).lower()
            if channel:
                args.append(channel)
            args.append(path.as_posix())

        # Add additional arguments
        if job.additional_args:
            args.append(job.additional_args)

        return args

    @classmethod
    def run_job_queue(cls):
        job = cls._get_next_job()
        if not job:
            return

        cls._current_job = job
        job_arguments = cls.create_job_arguments(job)
        job.set_in_progress()

        process_thread = RunProcess(job_arguments, job.job_dir,
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
