from pathlib import Path
from typing import Iterator


class ConversionJob:
    def __init__(self, job_dir: Path, files: dict, additional_args: str):
        self.job_dir = job_dir
        self.files = files
        self.additional_args = additional_args

    def list_files(self) -> Iterator[str]:
        for file_id, file_entry in self.files.items():
            yield file_id, file_entry.get("file_path").name, file_entry.get("use_channel")


class JobQueue:
    _current_job = None
    queue = list()

    @classmethod
    def current_job(cls):
        if cls.current_job:
            return cls._current_job

    @classmethod
    def add_job(cls, job):
        if job in cls.queue or job is cls._current_job:
            return

        if not cls._current_job:
            cls._current_job = job
        else:
            cls.queue.append(job)

    @classmethod
    def next_job(cls):
        if cls.queue:
            return cls.queue.pop(0)
        return None
