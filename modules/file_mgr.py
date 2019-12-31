import shutil
import time
from datetime import datetime

from modules import filesize
from pathlib import Path
from shutil import rmtree
from typing import Dict, List, Tuple, Union

from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.utils import secure_filename

from app import App
from modules.globals import APP_NAME, get_current_modules_dir, OUT_SUFFIX
from modules.log import setup_logger
from modules.site import JobFormFields, Urls

_logger = setup_logger(__name__)


class FileManager:
    def __init__(self):
        self.job_dir = None
        self.files = dict()

    @classmethod
    def clear_upload_folders(cls, jobs) -> bool:
        upload_dir: Path = App.config.get('UPLOAD_FOLDER')
        active_job_dirs = [j.job_dir() for j in jobs if not j.completed]

        if active_job_dirs:
            _logger.info('Not touching active jobs dirs during clean-up: %s', active_job_dirs)
        
        sucess = True
        for p in upload_dir.glob('*'):
            if p not in active_job_dirs:
                sucess = False if not cls.clear_folder(p) else sucess

        return sucess

    @staticmethod
    def clear_folder(folder: Path, re_create: bool = True) -> bool:
        """ Clear all contents of a directory aka deleting and re-creating it. """
        if folder.exists():
            try:
                rmtree(folder)
            except Exception as e:
                _logger.error('Error cleaning upload folder! %s', e, exc_info=1)
                return False

        if re_create:
            try:
                folder.mkdir(exist_ok=False)
            except FileExistsError or FileNotFoundError:
                _logger.error('Error re-creating upload folder!', exc_info=1)
                return False

        return True

    @staticmethod
    def move_to_static_dir(file: Path, create_dir: str = '') -> Union[None, Path]:
        """
        Move a file to the static download dir.
        Provide a string with create_dir to create a sub directory of that name.
        """
        if not file.is_file() or not file.exists():
            return

        static_download_dir = Path(get_current_modules_dir()) / APP_NAME / Urls.static_downloads

        if create_dir:
            static_download_dir = static_download_dir / secure_filename(create_dir)
            try:
                static_download_dir.mkdir(parents=True, exist_ok=True)
            except FileExistsError or FileNotFoundError:
                _logger.error('Error creating download folder!', exc_info=1)
                return

        new_file_path = static_download_dir / file.name

        try:
            shutil.move(file.as_posix(), new_file_path.as_posix())
        except Exception as e:
            _logger.error('Error moving file: %s', e, exc_info=1)
            return

        return new_file_path

    @staticmethod
    def list_downloads() -> Dict[str, Dict]:
        """ Return contents of download directory:
            Dict[folder_name(unique)] = Tuple[download_url, file_name, file_size]
        """
        download_files: Dict[str, Dict] = dict()
        static_download_dir = Path(get_current_modules_dir()) / APP_NAME / Urls.static_downloads

        # Iterate sub directory's
        for folder in static_download_dir.glob('*'):
            for file in folder.glob('*.*'):
                # Create url
                download_url = f'{Urls.static_downloads}/{folder.name}/{file.name}'

                try:
                    # File size
                    size = filesize.size(file.stat().st_size, system=filesize.alternative)
                    # Created Date from folder modification time
                    created = datetime.fromtimestamp(folder.stat().st_mtime).strftime('%d.%m.%Y %H:%M:%S')
                except Exception as e:
                    _logger.error('Could not access file size: %s', e)
                    size = 'N/A'
                    created = 'N/A'

                # Store entry
                download_files[folder.name] = {'url': download_url, 'name': file.name, 'size': size, 'created': created}

        return download_files

    @classmethod
    def delete_download(cls, folder_id: str) -> bool:
        download_dir = Path(get_current_modules_dir()) / APP_NAME / Urls.static_downloads / folder_id

        if cls.clear_folder(download_dir, re_create=False):
            return True

        return False

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

        files_message = ''

        # Store files in job dir
        for file_field in valid_file_fields:
            file = files[file_field.id]
            file_path = self.job_dir / secure_filename(file.filename)
            file.save(file_path.as_posix())

            use_channel = form.get(file_field.channel_id, '')

            # Update files dict
            self.files[file_field.id] = {'file_path': file_path, 'use_channel': use_channel}

            # Set output scene file based on input scene file
            if file_field.id == 'scene_file':
                if file_path.suffix == OUT_SUFFIX:
                    # |in>> one.usdz |out>> one_out.usdz
                    self.files['out_file'] = {'file_path': file_path.with_name(
                        f'{file_path.stem}_out{file_path.suffix}')}
                else:
                    # |in>> one.abc |out>> one.usdz
                    self.files['out_file'] = {'file_path': file_path.with_suffix(OUT_SUFFIX)}

            files_message += f'[{file_field.id}] {file_path.name}'

        _logger.info('FileManager stored files: %s', ', '. join([str(f) for f in self.files.values()]))
        return True, f'Files successfully uploaded. {files_message}'
