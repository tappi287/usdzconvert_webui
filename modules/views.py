from pathlib import Path

from flask import flash, redirect, render_template, request, jsonify, url_for, send_from_directory

from app import App, db
from modules.file_mgr import FileManager
from modules.globals import get_current_modules_dir, LOG_FILE_PATH
from modules.job import ConversionJob, JobManager
from modules.site import Site, JobFormFields, Urls


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
    App.logger.info('Endpoint: %s', request.endpoint)
    return render_template(Urls.templates[Urls.root], content=Site(),
                           upload_allowed_ext=list(App.config.get('UPLOAD_ALLOWED_MAPS'))
                           )


@App.route(Urls.root, methods=['POST'])
def upload_files():
    if request.method != 'POST':
        return

    App.logger.info('Endpoint: %s', request.endpoint)
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


@App.route(Urls.usd_man)
def usd_manual():
    usd_man_path = Path(get_current_modules_dir()) / 'usd_man' / 'usdzconvert_manual.txt'
    if usd_man_path.exists():
        with open(usd_man_path, 'r') as f:
            usd_man = f.read()
    else:
        usd_man = 'Could not find manual txt file.'

    return render_template(Urls.templates[Urls.usd_man], content=Site(), usd_manual=usd_man)

@App.route(Urls.log)
def log():
    log_file_path = Path(LOG_FILE_PATH)
    if log_file_path.exists():
        with open(log_file_path, 'r') as f:
            log_content = f.read()
    else:
        log_content = 'Could not locate log file.'

    return render_template(Urls.templates[Urls.log], content=Site(), log=log_content)


@App.route(Urls.about)
def about():
    return render_template(Urls.templates[Urls.about], content=Site())


def import_dummy():
    # Doing nothing besides keeping the IDE from deleting imports
    pass
