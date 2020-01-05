import os
from pathlib import Path
from typing import Iterator, Tuple, Union

from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.utils import secure_filename

from app import App, db
from modules.create_process import RunProcess
from modules.file_mgr import FileManager
from modules.log import setup_logger
from modules.site import JobFormFields, Urls
from modules.usdzconvert_args import create_usdzconvert_arguments, usd_env

_logger = setup_logger(__name__)

# set up a scoped_session
from flask_sqlalchemy import orm

session_factory = orm.sessionmaker(bind=db.engine)
Session = orm.scoped_session(session_factory)


class ConversionJob(db.Model):
    __tablename__ = 'jobs'

    job_id = db.Column(db.Integer, primary_key=True)
    files = db.Column(db.PickleType)
    option_args = db.Column(db.PickleType)
    additional_args = db.Column(db.String(120))
    state = db.Column(db.Integer)
    progress = db.Column(db.Integer)
    completed = db.Column(db.Boolean)
    is_current = db.Column(db.Boolean)
    process_messages = db.Column(db.String(1000))
    errors = db.Column(db.String(200))

    class States:
        queued = 0
        in_progress = 1
        finished = 2
        failed = 3

    state_names = {States.queued: 'Queued', States.in_progress: 'In progress',
                   States.finished: 'finished', States.failed: 'failed'}

    def __init__(self, job_dir: Path, files: dict, form: ImmutableMultiDict):
        self.files = files
        self.files['job_dir'] = {'file_path': job_dir}

        self.option_args = self.create_options(form)
        self.additional_args = form.get(JobFormFields.additional_args, '')

        self.state = -1  # One of self.States
        self.progress = int()  # Progress 0-100
        self.completed = False

        self.process_messages = str()
        self.errors = str()

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

    def job_dir(self) -> Path:
        return self.files.get('job_dir', dict()).get('file_path', Path('.'))

    def out_file(self) -> Path:
        return self.files.get('out_file', dict()).get('file_path', Path('.'))

    def set_out_file(self, val: Path):
        self.files['out_file']['file_path'] = val

        # Force a database update of PickeldType by reassigning the value
        ConversionJob.query.filter_by(job_id=self.job_id).update(dict(files=self.files))

    def list_files(self) -> Iterator[str]:
        for file_id, file_entry in self.files.items():
            p = file_entry.get("file_path")
            shortend_file_name = p if len(p.as_posix()) < 68 else f'...{p.as_posix()[-65:]}'
            yield file_id, shortend_file_name, file_entry.get("use_channel")

    def message_update(self, msg):
        self.process_messages += f'{msg}\n'
        self.progress = min(self.progress, self.progress + 15)

    def download_filename(self) -> Union[None, str]:
        if self.state == self.States.failed:
            return

        if self.out_file().exists() and self.completed:
            return f'{os.path.split(Urls.static_downloads)[1]}/' \
                   f'{secure_filename(self.job_dir().name)}/{self.out_file().name}'

    def direct_download_url(self) -> Union[None, str]:
        if self.state == self.States.failed:
            return
            
        if self.out_file().exists() and self.completed:
            return f'{Urls.static_downloads}/' \
                   f'{secure_filename(self.job_dir().name)}/{self.out_file().name}'

    def download_dir_id(self) -> Union[None, str]:
        if self.out_file().exists() and self.completed:
            return f'{secure_filename(self.job_dir().name)}'

    def get_state(self) -> str:
        return self.state_names.get(self.state, 'No job state set')

    def set_error(self, error_message: str):
        self.errors = error_message

    def set_in_progress(self):
        self.state = self.States.in_progress
        self.progress = 5

    def set_current(self, is_current: bool):
        self.is_current = is_current

    def set_complete(self):
        # Move Job file to static, public available, directory
        static_file_path = FileManager.move_to_static_dir(self.out_file(), self.job_dir().name)

        if static_file_path is None:
            _logger.error('Could not move final Job file. Setting job failed.')
            self.set_failed('Could not move USDZ to static directory.')
            return

        _logger.info('Moved Job result file to static directory: %s', static_file_path)

        self.set_out_file(static_file_path)
        self.state = self.States.finished
        self.completed = True
        self.progress = 100

        self.set_current(False)

    def set_failed(self, error_msg: str = ''):
        self.state = self.States.failed
        self.completed = True
        if error_msg:
            self.set_error(error_msg)
        self.progress = 0

        self.set_current(False)


class JobManager:
    @staticmethod
    def get_jobs() -> Iterator[ConversionJob]:
        return ConversionJob.query.all()

    @staticmethod
    def get_job_by_id(_id: int) -> Union[None, ConversionJob]:
        if isinstance(_id, str) and _id.isdigit():
            _id = int(_id)

        return ConversionJob.query.get(_id)

    @staticmethod
    def _get_next_job() -> Union[None, ConversionJob]:
        return ConversionJob.query.filter_by(completed=False).first()

    @staticmethod
    def current_job() -> ConversionJob:
        current_job = ConversionJob.query.filter_by(is_current=True).first()
        if current_job:
            return current_job
        return ConversionJob(Path(), dict(), ImmutableMultiDict())

    @classmethod
    def remove_job(cls, job_id: int) -> Tuple[bool, str]:
        with App.app_context():
            job = cls.get_job_by_id(job_id)

            if job and job.completed:
                db.session.delete(job)
                db.session.commit()
                _logger.debug('Deleted job: %s', job_id)
                return True, f'Job {job_id} successfully deleted.'
            elif not job.completed:
                return False, f'Job {job_id} is in process and can not be deleted.'
            elif not job:
                return False, f'Could not find job {job_id} you requested deletion for.'

        return False, f'Could not delete job {job_id}. Unknown error.'

    @staticmethod
    def create_job_arguments(job: ConversionJob) -> list:
        args = list()
        current_material = ''

        # Sort file dict by material entry
        for file_id, file_entry in sorted(job.files.items(), key=lambda f: f[1].get('material', '')):
            file_path = Path(file_entry.get("file_path"))

            if file_id in ('scene_file', 'out_file'):
                args.append(file_path.as_posix())  # inputFile/outputFile arguments
                continue

            # Only TextureMaps from here
            # -m materialName -diffuseColor diffuseFile.png
            if not file_id.startswith(JobFormFields.TextureMap.file_storage):
                continue

            material = file_entry.get(JobFormFields.TextureMap.material)
            if material and material != current_material:
                current_material = material
                args.append(f'-m')
                args.append(material)

            # Add texture maps file arguments
            args.append(f'-{file_entry.get(JobFormFields.TextureMap.type)}')

            channel = file_entry.get(JobFormFields.TextureMap.channel)
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
        with App.app_context():
            job = cls._get_next_job()
            if not job:
                return
            job.set_current(True)
            job.set_in_progress()
            job_arguments = create_usdzconvert_arguments(cls.create_job_arguments(job))
            job_dir = job.job_dir()
            db.session.commit()

        process_thread = RunProcess(job_arguments, job_dir, usd_env(),
                                    cls._finished_callback, cls._failed_callback, cls._message_callback)
        process_thread.start()

    @classmethod
    def _failed_callback(cls, error: str):
        with App.app_context():
            _logger.info('Job processing failed: %s', error)
            cls.current_job().set_failed(error)
            db.session.commit()
            cls.run_job_queue()

    @classmethod
    def _finished_callback(cls):
        with App.app_context():
            _logger.info('Job finished.')
            cls.current_job().set_complete()
            db.session.commit()
            cls.run_job_queue()

    @classmethod
    def _message_callback(cls, message):
        with App.app_context():
            cls.current_job().message_update(message)
            db.session.commit()
