from pathlib import Path

from flask import flash, redirect, render_template, request, url_for, jsonify, make_response

from app import App, db
from modules.file_mgr import FileManager
from modules.ftp import FtpRemote
from modules.globals import LOG_FILE_PATH, get_current_modules_dir
from modules.job import ConversionJob, JobManager
from modules.settings import JsonConfig
from modules.site import Site, Urls


def log_request(r: request):
    App.logger.info('Endpoint %s requested by %s with method %s', r.endpoint, r.remote_addr, r.method)


@App.before_first_request
def _clean_uploads():
    with App.app_context():
        jobs = JobManager.get_jobs()
        if FileManager.clear_upload_folders(jobs):
            App.logger.info('Clean Upload folder created @ %s', App.config.get('UPLOAD_FOLDER'))
        else:
            App.logger.info('Could not create clean upload folder @ %s', App.config.get('UPLOAD_FOLDER'))


@App.route(Urls.root)
def index():
    log_request(request)
    return render_template(Urls.templates[Urls.root], content=Site(),
                           upload_allowed_maps_ext=list(App.config.get('UPLOAD_ALLOWED_MAPS')),
                           upload_allowed_scene_ext=list(App.config.get('UPLOAD_ALLOWED_SCENE')),
                           )


@App.route("/upload", methods=["POST"])
def upload_async():
    """ Not used for now """
    App.logger.info('Fetch request: %s %s %s', request.files, request.get_json(), request.data)
    return make_response(jsonify({"message": "OK"}), 200)


@App.route(Urls.root, methods=['POST'])
def upload_files():
    if request.method != 'POST':
        return

    log_request(request)
    App.logger.debug('Submitted form data:\nFiles:\n%s\nForm:\n%s\nData\n%s', request.files, request.form, request.data)

    file_mgr = FileManager()
    result, message = file_mgr.handle_post_request(request.files, request.form)

    if not result:
        # --- Return to root and display errors ---
        App.logger.info('Upload failed for: %s', str(request.files))
        flash(message)

        return redirect(request.url)
    else:
        # --- Forward to current job page ---
        flash(message)

        with App.app_context():
            job = ConversionJob(file_mgr.job_dir, file_mgr.files, request.form)
            App.logger.info('Upload succeeded for: %s\nCreated job with id: %s', str(file_mgr.files), job.job_id)
            App.logger.info('Creating job with arguments: %s', ' '.join(JobManager.create_job_arguments(job)))

            db.session.add(job)
            db.session.commit()

        JobManager.run_job_queue()

        return redirect(Urls.job_page)


@App.route(Urls.job_page)
def job_page():
    log_request(request)
    return render_template(Urls.templates[Urls.job_page], content=Site(), jobs=JobManager.get_jobs())


@App.route(f'{Urls.job_download}/<job_id>')
def job_download(job_id):
    job = JobManager.get_job_by_id(job_id)
    App.logger.info('Received Download request for job_id: %s', job_id)

    if job and job.download_filename():
        App.logger.info('Serving with file: %s', job.download_filename())
        return redirect(url_for('static', filename=job.download_filename()))
    else:
        App.logger.info('Could not find job download file to serve: %s', job_id)
        return redirect(Urls.job_page)


@App.route(f'{Urls.job_delete}/<job_id>')
def job_delete(job_id):
    App.logger.info('Received deletion request for job_id: %s', job_id)
    result, msg = JobManager.remove_job(job_id)
    flash(msg)
    return redirect(Urls.job_page)


@App.route(Urls.downloads)
def static_downloads():
    log_request(request)
    dl_dict = FileManager.list_downloads()
    sorted_dls = sorted(dl_dict.items(), key=lambda x: x[1]['created'], reverse=True)  # Sort by date descending
    return render_template(Urls.templates[Urls.downloads], content=Site(),
                           downloads=sorted_dls)


@App.route(f'{Urls.download_delete}/<download_folder_id>')
def static_download_delete(download_folder_id):
    dl_dict = FileManager.list_downloads()
    dl = dl_dict.get(download_folder_id)
    App.logger.info('Received deletion request for download: %s %s', download_folder_id, dl)
    msg = f'Could not delete download {download_folder_id}/{dl.get("name")}'

    if FileManager.delete_download(download_folder_id):
        msg = f'Successfully deleted download {download_folder_id}/{dl.get("name")}'

    flash(msg)
    return redirect(Urls.downloads)


@App.route(f'{Urls.share}/<download_folder_id>')
def share_settings(download_folder_id):
    log_request(request)
    dl_dict = FileManager.list_downloads()
    dl = dl_dict.get(download_folder_id)
    config = JsonConfig.get_host_config_without_pswd(App.config.get('SHARE_HOST_CONFIG_PATH'))

    if not config:
        flash("No remote host sharing configuration has been setup. I have redirected you to the "
              "configuration page. You're welcome.")
        return redirect(Urls.host)

    App.logger.info('Sharing %s', dl)
    return render_template(Urls.templates[Urls.share], content=Site(), download=dl, config=config,
                           folder_id=download_folder_id)


@App.route(f'{Urls.share}/<download_folder_id>', methods=['POST'])
def share_file(download_folder_id):
    """ User submitted a download file to share """
    log_request(request)
    dl_dict = FileManager.list_downloads()
    dl = dl_dict.get(download_folder_id)
    App.logger.info('Download Share: %s %s', request.files, request.form)

    share_result = FileManager.remote_share_download(download_folder_id, dl, request.form, request.files)

    if share_result:
        flash(f'Shared at: <a href="{request.form.get("remote_url")}">{request.form.get("remote_url")}</a>')
    else:
        flash(f'Error sharing files on remote host! See the <a href="{Urls.log}">log page</a> for details.')

    return redirect(request.url)


@App.route(Urls.host)
def host():
    """ View to edit sharing host configuration """
    log_request(request)
    config = JsonConfig.get_host_config_without_pswd(App.config.get('SHARE_HOST_CONFIG_PATH'))
    return render_template(Urls.templates[Urls.host], content=Site(), config=config)


@App.route(Urls.host, methods=['POST'])
def host_post():
    """ User submitted an sharing host configuration """
    if request.method != 'POST':
        return
    log_request(request)

    if JsonConfig.save_host_config_form(request.form, App.config.get('SHARE_HOST_CONFIG_PATH')):
        flash('Sharing host configuration saved successfully')
        msg = 'Successfully tested an FTP connection to your remote host configuration'
        result = False

        try:
            ftp = FtpRemote(JsonConfig.load_config(App.config.get('SHARE_HOST_CONFIG_PATH')))
            result = ftp.connect()
            del ftp
        except Exception as e:
            result = False
            msg = f'Could not connect to the configured remote host! {e}'
        finally:
            flash(msg)
            if not result:
                App.logger.error(msg)
    else:
        flash('Sharing host configuration could not be saved! The server has no instance directory '
              'with an appropriate key file or the filesystem could not write the file. ')

    return redirect(Urls.host)


@App.route(Urls.about)
def about():
    log_request(request)
    return render_template(Urls.templates[Urls.about], content=Site())


@App.route(Urls.usd_man)
def usd_manual():
    log_request(request)
    usd_man_path = Path(get_current_modules_dir()) / 'usd_man' / 'usdzconvert_manual.txt'
    if usd_man_path.exists():
        with open(usd_man_path, 'r') as f:
            usd_man = f.read()
    else:
        usd_man = 'Could not find manual txt file.'

    return render_template(Urls.templates[Urls.usd_man], content=Site(), usd_manual=usd_man)


@App.route(Urls.log)
def log():
    log_request(request)

    log_file_path = Path(LOG_FILE_PATH)
    if log_file_path.exists():
        with open(log_file_path, 'r') as f:
            log_content = f.read()
    else:
        log_content = 'Could not locate log file.'

    return render_template(Urls.templates[Urls.log], content=Site(), log=log_content)


def import_dummy():
    # Doing nothing besides keeping the IDE from deleting imports
    pass
