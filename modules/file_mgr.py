import time
from pathlib import Path
from shutil import rmtree
from typing import Tuple, Union, Set, List

from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.utils import secure_filename

from app import App
from modules.log import setup_logger
from modules.site import JobFormFields

_logger = setup_logger(__name__)


class FileManager:
    def __init__(self):
        self.job_dir = None
        self.files = dict()

    @staticmethod
    def clear_upload_folder() -> bool:
        upload_dir: Path = App.config.get('UPLOAD_FOLDER')

        if upload_dir.exists():
            try:
                rmtree(upload_dir)
            except Exception as e:
                _logger.error('Error cleaning upload folder! %s', e, exc_info=1)
                return False

            try:
                upload_dir.mkdir(exist_ok=False)
            except FileExistsError or FileNotFoundError:
                _logger.error('Error re-creating upload folder!', exc_info=1)
                return False

        return True

    @staticmethod
    def _allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in App.config.get('UPLOAD_ALLOWED_EXT')

    @classmethod
    def _get_valid_files(cls, files: ImmutableMultiDict) -> List[JobFormFields.FileField]:
        valid_file_fields = list()

        for file_field in JobFormFields.file_fields:
            file_name = ''

            if file_field.id in files:
                file_name = files[file_field.id].filename

            if file_name:
                if cls._allowed_file(file_name):
                    valid_file_fields.append(file_field)
                else:
                    _logger.error('File extension not allowed! %s', file_name)
                    file_name = ''

            if file_field.required:
                if not file_name:
                    _logger.error('Required file: %s is missing or of wrong type!', file_field.id)
                    return list()

        return valid_file_fields

    @staticmethod
    def create_job_dir() -> Union[Path, None]:
        name = f'up_{str(time.time()).replace(".", "")[-15:]}'
        upload_dir = App.config.get('UPLOAD_FOLDER') or Path('.')
        job_dir = upload_dir / name

        try:
            job_dir.mkdir(exist_ok=False)
        except FileExistsError or FileNotFoundError as e:
            _logger.error('Could not create upload job directory: %s', e)
            return None

        _logger.debug('Created Job directory %s', job_dir)
        return job_dir

    def handle_post_request(self, files: ImmutableMultiDict, form: ImmutableMultiDict) -> Tuple[bool, str]:
        """ Handle POST request and store files in new job directory if valid files found.

        :param ImmutableMultiDict files: POST request files dict to handle
        :param ImmutableMultiDict form: POST request form dict
        :return: bool, message
        """
        valid_file_fields = self._get_valid_files(files)

        if not valid_file_fields:
            return False, 'No files received or file types not supported.'

        self.job_dir = self.create_job_dir()

        if self.job_dir is None:
            return False, 'Error storing files on the server. There is nothing you can do about that.'

        # Store files in job dir
        for file_field in valid_file_fields:
            file = files[file_field.id]
            file_path = self.job_dir / secure_filename(file.filename)
            file.save(file_path.as_posix())

            use_channel = form.get(file_field.channel_id) or ''

            # Update files dict
            self.files[file_field.id] = {
                'file_path': file_path, 'use_channel': use_channel if use_channel else None
                }

        _logger.info('FileManager stored files: %s', ', '. join([str(f) for f in self.files.values()]))
        return True, 'Files successfully uploaded.'
