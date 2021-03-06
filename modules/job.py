from pathlib import Path
from typing import Iterator, Tuple, Union

from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.utils import secure_filename

from modules.app import App, db
from modules.create_process import RunProcess
from modules.file_mgr import FileManager
from modules.globals import default_tex_coord_set_names
from modules.log import setup_logger
from modules.site import JobFormFields, Urls
from modules.usdzconvert_args import create_usdzconvert_arguments, usd_env, create_abc_post_process_arguments, \
    create_usdscript_arguments
from modules.utils import get_usdz_color_argument

_logger = setup_logger(__name__)

"""
# set up a scoped_session
from flask_sqlalchemy import orm

session_factory = orm.sessionmaker(bind=db.engine)
Session = orm.scoped_session(session_factory)
"""


class ConversionJob(db.Model):
    __tablename__ = 'jobs'

    job_id = db.Column(db.Integer, primary_key=True)
    files = db.Column(db.PickleType)
    option_args = db.Column(db.PickleType)
    additional_args = db.Column(db.String(120))
    state = db.Column(db.Integer)
    progress = db.Column(db.Integer)
    completed = db.Column(db.Boolean)
    process_messages = db.Column(db.String(1000))
    errors = db.Column(db.String(200))

    class States:
        queued = 0
        in_progress = 1
        post_processed = 2
        finished = 3
        failed = 4

    state_names = {States.queued: 'Queued', States.in_progress: 'In progress', States.post_processed: 'post processing',
                   States.finished: 'finished', States.failed: 'failed'}

    def __init__(self, job_dir: Path, files: dict, form: ImmutableMultiDict):
        self.files = files
        self.files['job_dir'] = {'file_path': job_dir}
        self.files['preview'] = {'file_path': Path('.')}

        self.option_args = self.create_options(form)
        self.additional_args = form.get(JobFormFields.additional_args, '')

        self.state = -1  # One of self.States
        self.progress = int()  # Progress 0-100
        self.completed = False

        self.process_messages = str()
        self.errors = str()

    @staticmethod
    def create_options(form: ImmutableMultiDict) -> list:
        option_args = list()
        for option in JobFormFields.option_fields:
            if option.id == 'outSuffix':
                # Not a valid usdzconvert argument, will be used to name outFile
                continue

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

    def preview_file(self) -> Path:
        return self.files.get('preview', dict()).get('file_path', Path('.'))

    def _set_file(self, file_key: str, val: Path):
        self.files[file_key]['file_path'] = val
        # Force a database update of PickeldType by reassigning the value
        ConversionJob.query.filter_by(job_id=self.job_id).update(dict(files=self.files))

    def set_out_file(self, val: Path):
        self._set_file('out_file', val)

    def set_preview_file(self, val: Path):
        self._set_file('preview', val)

    def list_files(self) -> Iterator[Tuple[str, str, str, str, str]]:
        """ List files to Jinja html template """
        for file_id, file_entry in self.files.items():
            file_path = file_entry.get("file_path")
            if not file_path:
                p = '- No file set -'
            else:
                p = file_path.name

            short_file_name = p if len(p) < 43 else f'...{p[-40:]}'

            yield (file_id,
                   short_file_name,
                   file_entry.get('use_channel', ''),
                   file_entry.get(JobFormFields.TextureMap.material, ''),
                   file_entry.get(JobFormFields.TextureMap.uv_coord, ''),
                   file_entry.get(JobFormFields.TextureMap.type, ''),
                   file_entry.get(JobFormFields.TextureMap.material_color, ''),
                   )

    @staticmethod
    def create_arguments_message(args) -> str:
        arg_message = ''
        for arg in args:
            try:
                p = Path(arg)
            except Exception:
                p = None

            if p is not None:
                arg_message += f'{p.name} '
            else:
                arg_message += f'{arg} '

        return arg_message.rstrip(' ')

    def add_arguments_message(self, args):
        self.message_update(self.create_arguments_message(args) + '\n')

    def message_update(self, msg):
        self.process_messages += f'{msg}\n'
        self.progress = min(self.progress, self.progress + 15)

    def preview_url(self) -> Union[None, str]:
        if self.preview_file().exists() and self.completed:
            return f'{Urls.downloads}/' \
                   f'{secure_filename(self.job_dir().name)}/{self.preview_file().name}'

    def direct_download_url(self) -> Union[None, str]:
        if self.state == self.States.failed:
            return

        if self.out_file().exists() and self.completed:
            return f'{Urls.downloads}/' \
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

    def set_preview_image_static(self):
        img_file_path = FileManager.move_to_static_dir(self.preview_file(), self.job_dir().name)
        if img_file_path is None:
            _logger.error('Could not move preview image file.')
            return

        self.set_preview_file(img_file_path)

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

    def set_failed(self, error_msg: str = ''):
        self.state = self.States.failed
        self.completed = True
        if error_msg:
            self.set_error(error_msg)
        self.progress = 0


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

    @classmethod
    def create_job_arguments(cls, job: ConversionJob) -> list:
        args = list()
        scene_file_path = job.files.get(JobFormFields.scene_file_field.id, dict()).get('file_path', Path('.'))
        out_file = job.out_file()

        # --- Handle Alembic files --
        # Alembic files need to be post-processed due to "missing" material assignments
        # intended by the nature of the format. We will assign to matching material/mesh names instead.
        #
        # The combination of .abc in suffix and .usdc out suffix will trigger the post-process
        if scene_file_path.suffix == '.abc':
            out_file = out_file.with_suffix('.usdc')

        # -inputFile arg -outputFile arg
        args += [scene_file_path, out_file]

        # Always copy textures for USD inputs
        if out_file.suffix in ('.usd', '.usda', '.usdc') and '-copytextures' not in job.option_args:
            args.append('-copytextures')

        # --- Add additional arguments ---
        if job.additional_args:
            for a in job.additional_args.split(' '):
                args.append(a)

        # --- Add options ---
        if job.option_args:
            args += job.option_args

        # --- Check if we have individual Uv sets per material ---
        tex_coords = set(f.get(JobFormFields.TextureMap.uv_coord) for f in job.files.values()
                         if f.get(JobFormFields.TextureMap.uv_coord, ''))
        individual_tex_coords = True if len(tex_coords) > 1 else False

        # usdpython 0.62 usdzconvert sets wrong source UVset for alembic files
        # If the user does not choose to provide individual texCoord setting per material
        # set a default value guessed by the file extension.
        if not individual_tex_coords:
            # Set a default value guessed by file extension
            default_tex_arg = default_tex_coord_set_names.get(scene_file_path.suffix)
            if default_tex_arg:
                args += ['-texCoordSet', default_tex_arg]

        # --- Add Material and Texture Map arguments ---
        current_material = ''

        # Sort file dict by material entry
        for file_id, file_entry in sorted(job.files.items(), key=lambda f: f[1].get('material', '')):
            # -m materialName -diffuseColor diffuseFile.png
            if not file_id.startswith(JobFormFields.TextureMap.file_storage):
                continue

            file_path = file_entry.get("file_path")
            material = file_entry.get(JobFormFields.TextureMap.material)
            tex_coord = file_entry.get(JobFormFields.TextureMap.uv_coord)
            map_type = file_entry.get(JobFormFields.TextureMap.type)
            color = get_usdz_color_argument(map_type, file_entry.get(JobFormFields.TextureMap.material_color))

            # Add material argument
            if material and material != current_material:
                current_material = material
                args += ['-m', material]

                # Add texCoordSet argument
                if individual_tex_coords and tex_coord:
                    args += ['-texCoordSet', tex_coord]

            # Add texture maps file arguments
            args.append(f'-{map_type}')

            channel = file_entry.get(JobFormFields.TextureMap.channel)
            if channel:
                _logger.info('Adding channel argument: %s', channel)
                args.append(channel.lower())

            if file_path:
                args.append(Path(file_path))

            # Add fallback color or luminosity constant
            if color:
                args.append(color)

        return args

    @classmethod
    def run_job_queue(cls):
        with App.app_context():
            job = cls._get_next_job()
            if not job:
                return
            job.set_in_progress()
            job_arguments = create_usdzconvert_arguments(cls.create_job_arguments(job))
            _logger.info('Running Job with arguments: %s', job_arguments)
            job.add_arguments_message(job_arguments)  # Document cmd line arguments

            process_thread = RunProcess(job_arguments, job.job_dir(), usd_env(), job.job_id,
                                        cls._finished_callback, cls._failed_callback, cls._message_callback)
            db.session.commit()
        process_thread.start()
        _logger.info('Started thread with id: %s', process_thread.ident)

    @classmethod
    def _run_post_process(cls, job: ConversionJob) -> bool:
        """Decide if we need to post process an alembic input file """
        scene_file: Path = job.files[JobFormFields.scene_file_field.id].get('file_path', Path('.'))

        if scene_file.suffix != '.abc':
            return False

        job.progress = 75
        job.message_update('USDZ Conversion Server is post processing your Alembic input file.')

        # --- Start Alembic post process ---
        args = create_abc_post_process_arguments()
        args.append(scene_file.with_suffix('.usdc'))

        job.add_arguments_message(args)

        post_process_thread = RunProcess(args, job.job_dir(), usd_env(), job.job_id,
                                         cls._finished_callback, cls._failed_callback, cls._message_callback)
        post_process_thread.start()
        _logger.info('Started post processing thread with id: %s', post_process_thread.ident)

        # Post process will create a usdz
        job.files[JobFormFields.scene_file_field.id]['file_path'] = scene_file.parent / f'{scene_file.stem}_out.usdc'
        job.set_out_file(job.out_file().with_suffix('.usdz'))
        job.state = ConversionJob.States.post_processed
        db.session.commit()
        return True

    @classmethod
    def _run_usdrecord(cls, job: ConversionJob):
        """ Create a preview image of the output scene file """
        args = create_usdscript_arguments('usdrecord')
        if not args[-1:][0].exists():
            # Our environment does not provide USD imaging components
            return

        usdz_file = job.out_file()
        if not usdz_file.exists():
            # No scene file to create preview image from
            return
        img_file = usdz_file.with_suffix(App.config.get('PREVIEW_IMG_SUFFIX'))
        if img_file.exists():
            # Preview image already created
            return
        job.set_preview_file(img_file)

        args += [usdz_file, img_file, '--imageWidth', '400', '--renderer', 'GL']

        job.add_arguments_message(args)

        post_process_thread = RunProcess(args, job.job_dir(), usd_env(), job.job_id,
                                         cls._preview_image_generated, None, cls._message_callback)
        post_process_thread.start()
        _logger.info('Started preview image generation thread with id: %s', post_process_thread.ident)
        db.session.commit()

    @classmethod
    def _preview_image_generated(cls, thread_id: int):
        with App.app_context():
            job = cls.get_job_by_id(thread_id)
            job.set_preview_image_static()
            db.session.commit()

    @classmethod
    def _failed_callback(cls, thread_id: int, error: str):
        with App.app_context():
            _logger.info('Job processing failed: %s', error)
            cls.get_job_by_id(thread_id).set_failed(error)
            db.session.commit()
            cls.run_job_queue()

    @classmethod
    def _finished_callback(cls, thread_id: int):
        with App.app_context():
            job = cls.get_job_by_id(thread_id)

            # -- Post process alembic input --
            if cls._run_post_process(job):
                return

            _logger.info('Job processing finished.')
            job.set_complete()
            db.session.commit()

            # -- Try to create scene preview image --
            cls._run_usdrecord(job)
        cls.run_job_queue()

    @classmethod
    def _message_callback(cls, thread_id: int, message):
        with App.app_context():
            cls.get_job_by_id(thread_id).message_update(message)
            db.session.commit()
