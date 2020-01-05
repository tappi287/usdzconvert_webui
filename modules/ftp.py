import time
from ftplib import FTP_TLS
from pathlib import Path
from typing import Union

from paramiko import Transport, SFTPClient
from modules.log import setup_logger

_logger = setup_logger(__name__)


class FtpRemote:
    """ Provide SFTP or FTP over TLS interface
    """

    port = '22'

    # Temporary file transfer callback helpers
    _temp_total = 0
    _temp_transferred = 0

    def __init__(self, conf: dict):
        self.host = conf.get('host')
        self.port = conf.get('port')
        self.user = conf.get('user')
        self.pswd = conf.get('pswd')

        self.is_sftp = True if conf.get('protocol') == 'sftp' else False  # ftp / sftp

        self.connections = 0
        self.remote_dir = conf.get('remote_dir')

        self.in_progress = False
        self.transport = None
        self.sftp = None
        self.ftps = None

    def __del__(self):
        self.disconnect()

    def connect(self) -> bool:
        if self.is_sftp:
            return self._connect_sftp()
        else:
            return self._connect_ftp()

    def _connect_ftp(self) -> bool:
        try:
            self.ftps = FTP_TLS(self.host)
            self.ftps.login(self.user, self.pswd)
            self.connections += 1

            # switch to secure data connection.. IMPORTANT! Otherwise, only the user and password is
            # encrypted and not all the file data.
            prot_p_result = self.ftps.prot_p()
            _logger.info('FTP Secure Connection result %s', prot_p_result)

            # Change/Create current working directory
            if self.remote_dir:
                if not self.create_dir(self.remote_dir):
                    _logger.error('Could not create or change current directory to configuration remote directory.')
                    return False

            cwd = self.ftps.pwd() or '.'
            _logger.info('Connected to ' + self.host[0:9] + ' at dir: ' + cwd)

        except Exception as e:
            _logger.error(e, exc_info=1)
            return False
        return True

    def _connect_sftp(self) -> bool:
        try:
            # SSH Verbindung oeffnen
            self.transport = Transport((self.host, self.port))
            self.transport.connect(username=self.user, password=self.pswd)
        except Exception as e:
            _logger.error(e)
            return False

        try:
            # SFTP Verbindung oeffnen
            self.sftp = SFTPClient.from_transport(self.transport)
            self.connections += 1
            self.change_dir(self.remote_dir)
            cwd = self.sftp.getcwd() or '.'

            _logger.info('Connected to ' + self.host[0:9] + ' at dir: ' + cwd)

            return True
        except Exception as e:
            _logger.error('Could not create a connection to %s', self.host)
            _logger.error(e)
            return False

    def listdir(self, directory: str = ''):
        if self.is_sftp:
            return self._listdir_sftp(directory)
        else:
            return self._listdir_ftp(directory)

    def _listdir_ftp(self, directory: str) -> Union[None, list]:
        ftp_ls = list()

        def ls_callback(line: str):
            """ 'drwxr-xr-x   2 cgi      psacln       4096 Sep 13 08:28 ARObjects'
                extract directory str from output
            """
            if len(line.rsplit(' ', 1)) > 1:
                ftp_ls.append(line.rsplit(' ', 1)[1])

        try:
            self.ftps.dir(directory, ls_callback)
        except Exception as e:
            _logger.error(e, exc_info=1)
            return

        return ftp_ls

    def _listdir_sftp(self, directory: str):
        """ List given Remote directory """
        try:
            ftp_ls = self.sftp.listdir(path=directory)
        except Exception as e:
            _logger.error(e)
            return
        _logger.debug(str(ftp_ls) + ' - ' + str(type(ftp_ls)))
        return ftp_ls

    def change_dir(self, directory: str):
        if self.sftp is None and self.ftps is None:
            return

        try:
            if self.is_sftp:
                self.sftp.chdir(directory)
            else:
                self.ftps.cwd(directory)
        except Exception as e:
            _logger.error(e)
            return False

        return True

    def create_dir(self, directory: str) -> bool:
        """ Create directory if it does not exists and change current working directory to it """
        if self.sftp is None and self.ftps is None:
            return False

        if self.is_sftp:
            # TODO: Implement sftp create directory
            return False
        else:
            if self.ftps.pwd() != f'/{directory}' and directory not in self.listdir(''):
                self.ftps.mkd(directory)

            return self.change_dir(directory)

    def get(self, local_path: Path) -> bool:
        """ Provide local file name, Remote file will be grabbed from current Remote dir """
        if self.sftp is None and self.ftps is None:
            return False

        # BackUp local file
        backup_file = None
        if local_path.exists():
            backup_file = local_path.with_suffix('.bak')
            local_path.replace(backup_file)

        time.sleep(0.2)
        ftp_file = local_path.name

        if self.is_sftp:
            result = self._get_sftp(local_path, ftp_file)
        else:
            result = self._get_ftp(local_path, ftp_file)

        # Remove backup file
        if result and backup_file:
            backup_file.unlink()

        return result

    def _get_ftp(self, local_path: Path, ftp_file: str) -> bool:
        def write_file_callback(chunk):
            f.write(chunk)
            self._ftp_progress_callback(chunk)

        result = True
        self.ftps.voidcmd('TYPE I')  # Get size is not allowed in default ASCII mode
        self._temp_total = self.ftps.size(ftp_file) or 0
        self._temp_transferred = 0

        try:
            f = open(local_path.as_posix(), 'wb')
        except Exception as e:
            _logger.error('Could not open local file: %s', e)
            return False

        try:
            self.ftps.retrbinary(f'RETR {ftp_file}', callback=write_file_callback)
        except Exception as e:
            _logger.error('Error getting remote file: %s', e, exc_info=1)
            result = False
        finally:
            f.close()
            return result

    def _get_sftp(self, local_path: Path, ftp_file: str) -> bool:
        try:
            self.sftp.get(str(ftp_file), str(local_path), callback=self._sftp_progress_callback)
        except Exception as e:
            msg = 'Did not find remote file %s' % ftp_file
            _logger.debug(msg)
            _logger.error(e)
            return False
        return True

    def put(self, local_path) -> bool:
        if self.sftp is None and self.ftps is None:
            # No Connection
            _logger.error('Can not put file without connection.')
            return False

        local_path = Path(local_path)
        ftp_file = local_path.name

        if self.is_sftp:
            return self._put_sftp(local_path, ftp_file)
        else:
            return self._put_ftp(local_path, ftp_file)

    def _put_ftp(self, local_path: Path, ftp_file: str) -> bool:
        self._temp_total = local_path.stat().st_size
        self._temp_transferred = 0

        try:
            with open(local_path.as_posix(), 'rb') as f:
                self.ftps.storbinary(f'STOR {ftp_file}', f, callback=self._ftp_progress_callback)
        except Exception as e:
            _logger.error('Could not upload file %s', e, exc_info=1)
            return False

        return True

    def _ftp_progress_callback(self, chunk):
        self._temp_transferred += len(chunk)
        self._sftp_progress_callback(self._temp_transferred, self._temp_total)

    def _put_sftp(self, local_path: Path, ftp_file: str):
        try:
            self.sftp.put(str(local_path), str(ftp_file), callback=self._sftp_progress_callback, confirm=True)
            _logger.info('%s wurde erfolgreich übertragen.' % str(local_path.name))
            return True
        except Exception as e:
            _logger.info('Konnte Remotedatei %s nicht erstellen.\n%s', ftp_file, e)
            return False

    def _sftp_progress_callback(self, transferred: int, total: int):
        """ Callback method for get/put operations """
        current_percent = int(100 / min(10000, total * transferred))
        transfer_bar = self.text_transfer_bar(current_percent)

        # Report every 25 Percent
        if (current_percent % 25) == 0 and not self.in_progress:
            _logger.info('Übertragen: %s %s Prozent', transfer_bar, current_percent)
            self.in_progress = True

        if (current_percent % 25) > 0:
            self.in_progress = False

    @staticmethod
    def text_transfer_bar(current_percent) -> str:
        # Create text transfer bar
        transfer_bar, last = '', True
        for a in range(0, 22):
            current = int(current_percent / (100 / 20))
            if a < current:
                transfer_bar += '='
            elif a > current and last:
                last = False
                transfer_bar += '>'
            elif a > current and not last:
                transfer_bar += ' '

        return transfer_bar

    def disconnect(self):
        if self.ftps is not None:
            self.ftps.close()
            self.connections -= 1

        if self.sftp is not None:
            self.sftp.close()
            self.connections -= 1

        if self.transport is not None:
            self.transport.close()

        _logger.info('FtpRemote utility disconnected itself.')
