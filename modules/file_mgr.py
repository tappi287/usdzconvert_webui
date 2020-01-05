import shutil
import time
from datetime import datetime
from pathlib import Path
from shutil import rmtree, copy
from typing import Dict, Tuple, Union

from flask import render_template
from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.utils import secure_filename

from app import App
from modules import filesize
from modules.ftp import FtpRemote
from modules.globals import APP_NAME, OUT_SUFFIX, get_current_modules_dir
from modules.log import setup_logger
from modules.settings import JsonConfig
from modules.site import JobFormFields, Urls

_logger = setup_logger(__name__)


class FileManager:
    static_download_dir = Path(get_current_modules_dir()) / APP_NAME / Urls.static_downloads
    static_img_dir = Path(get_current_modules_dir()) / APP_NAME / Urls.static_images

    def __init__(self):
        self.job_dir = None
        self.files = dict()

    @classmethod
    def remote_share_download(cls, folder_id: str, dl: dict,
                              form: ImmutableMultiDict, files: ImmutableMultiDict) -> bool:
        # -- Get Download directory --
        download_dir = cls.static_download_dir / folder_id
        if not download_dir.exists():
            _logger.error('File to share not found at: %s', download_dir.as_posix())
            return False

        # -- Clear and create share sub-directory --
        share_dir = download_dir / 'share'
        if not cls.clear_folder(share_dir, re_create=True):
            _logger.error('Could not create share folder at: %s', share_dir.as_posix())
            return False

        # -- Save preview image file in share folder --
        img_file = files.get('preview_image_store')
        if not img_file:
            img_file = cls.static_img_dir / 'preview.jpg'
            img_path = share_dir / img_file.name
            try:
                copy(img_file, img_path)
            except Exception as e:
                _logger.error('Error copying preview image: %s', e)
        else:
            img_path = share_dir / img_file.filename
            img_file.save(img_path.as_posix())

        # -- Save usdz file in share folder --
        in_scene_file = download_dir / dl.get('name')
        scene_path = share_dir / secure_filename(form.get('filename'))
        try:
            copy(in_scene_file, scene_path)
        except Exception as e:
            _logger.error('Could not save USDZ output file: %s', e)
            return False

        # -- Create index html file --
        index_html_path = share_dir / 'index.html'
        with App.app_context():
            with open(index_html_path.as_posix(), 'w') as f:
                f.write(
                    render_template(
                        Urls.templates.get(Urls.share_template),
                        page_description=form.get('footer-line'),
                        usdz_file=scene_path.name,
                        preview_image_url=img_path.name
                        )
                    )

        # -- Transfer Remote Share folder --
        conf = JsonConfig.load_config(App.config.get('SHARE_HOST_CONFIG_PATH'))
        remote = FtpRemote(conf)
        if not remote.connect():
            return False
        if not remote.create_dir(form.get('share_folder')):
            return False

        # Upload files
        for local_file in (index_html_path, scene_path, img_path):
            if not remote.put(local_file):
                return False

        # Clean up share directory
        cls.clear_folder(share_dir, re_create=False)

        return True

    @classmethod
    def clear_upload_folders(cls, jobs) -> bool:
        upload_dir: Path = App.config.get('UPLOAD_FOLDER')
        active_job_dirs = [j.job_dir() for j in jobs if not j.completed]

        if active_job_dirs:
            _logger.info('Not touching active jobs dirs during clean-up: %s', active_job_dirs)
        
        success = True
        for p in upload_dir.glob('*'):
            if p not in active_job_dirs:
                success = False if not cls.clear_folder(p) else success

        return success

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
            except FileExistsError or FileNotFoundError or PermissionError:
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

    @classmethod
    def list_downloads(cls) -> Dict[str, Dict]:
        """ Return contents of download directory:
            Dict[folder_name(unique)] = Tuple[download_url, file_name, file_size]
        """
        download_files: Dict[str, Dict] = dict()

        # Iterate sub directory's
        for folder in cls.static_download_dir.glob('*'):
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
        download_dir = cls.static_download_dir / folder_id

        if cls.clear_folder(download_dir, re_create=False):
            return True

        return False

    @staticmethod
    def _allowed_file(filename: str) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in App.config.get('UPLOAD_ALLOWED_EXT')

    @staticmethod
    def _is_multi_file_scene_primary(filename: str) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ('gltf', )

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

    def _save_file(self, file) -> Union[None, Path]:
        if not file or not self._allowed_file(file.filename):
            return

        file_path = self.job_dir / secure_filename(file.filename)
        file.save(file_path.as_posix())
        return file_path

    def _save_scene_file(self, files: ImmutableMultiDict) -> bool:
        scene_files = files.getlist(key=JobFormFields.scene_file_field.id)

        if not scene_files:
            _logger.error('Scene file not found in Form data.')
            return False

        file_path = None

        for file in scene_files:
            scene_path = self._save_file(file)

            if scene_path is None:
                _logger.error('File extension not allowed or file could not be stored: %s', file.filename)
                return False

            # eg. gltf + bin will return gltf scene file path as primary file path
            if self._is_multi_file_scene_primary(file.filename):
                file_path = scene_path
            elif len(scene_files) == 1:
                file_path = scene_path

        if not file_path:
            _logger.error('Could not locate primary scene file in: %s', scene_files)
            return False

        # Update files dict
        self.files[JobFormFields.scene_file_field.id] = {'file_path': file_path}

        # Set out file path
        if file_path.suffix == OUT_SUFFIX:
            # |in>> one.usdz |out>> one_out.usdz
            self.files['out_file'] = {'file_path': file_path.with_name(f'{file_path.stem}_out{file_path.suffix}')}
        else:
            # |in>> one.abc |out>> one.usdz
            self.files['out_file'] = {'file_path': file_path.with_suffix(OUT_SUFFIX)}

        return True

    @staticmethod
    def _create_flat_texture_files_dict(files: ImmutableMultiDict) -> dict:
        texture_files = dict()

        for k, v in files.items():
            if not k.startswith(JobFormFields.TextureMap.file_storage):
                continue

            file_list = files.getlist(key=k)

            for file in file_list:
                texture_files[file.filename] = file

        return texture_files

    def _get_texture_maps(self, files: ImmutableMultiDict, form: ImmutableMultiDict) -> str:
        texture_ids = JobFormFields.TextureMap
        texture_files = self._create_flat_texture_files_dict(files)
        option_ids = [o.id for o in JobFormFields.option_fields]
        msg = ''

        for key, value in form.items():
            if key in option_ids:
                continue

            # Get texture num 'texture_file_1' map_key = ('texture_file', 1)
            map_key = key.rsplit('_', 1)
            if len(map_key) < 2:
                continue

            map_id, map_num = map_key
            if map_id != texture_ids.file:
                continue

            file = texture_files.get(value)
            if not file:
                _logger.error('No texture file found for %s!', key)
                continue

            self.files[f'texture_map_{map_num}'] = {
                'file_path': self._save_file(file),
                texture_ids.channel: form.get(f'{texture_ids.channel}_{map_num}', ''),
                texture_ids.material: form.get(f'{texture_ids.material}_{map_num}', ''),
                texture_ids.type: form.get(f'{texture_ids.type}_{map_num}', ''),
                }

            line = "\n{}{} {}".format(
                form.get(f'{texture_ids.material}_{map_num} ', ''),
                form.get(f'{texture_ids.type}_{map_num}', ''),
                file.filename)
            _logger.debug('Saved texture_map: %s', line)
            msg += line

        return msg

    def handle_post_request(self, files: ImmutableMultiDict, form: ImmutableMultiDict) -> Tuple[bool, str]:
        """ Handle POST request and store files in new job directory if valid files found.

        :param ImmutableMultiDict files: POST request files dict to handle
        :param ImmutableMultiDict form: POST request form dict
        :return: bool, message
        """
        self.job_dir = self.create_job_dir()
        if not self._save_scene_file(files):
            return False, 'Scene file not found or not supported.'

        msg = self._get_texture_maps(files, form)
        msg += f'\n{self.files[JobFormFields.scene_file_field.id]}'

        return True, f'Files successfully uploaded.\n{msg}'
