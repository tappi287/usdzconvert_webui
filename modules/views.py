from pathlib import Path

from flask import flash, redirect, render_template, request

from app import App
from modules.file_mgr import FileManager
from modules.globals import get_current_modules_dir
from modules.job import ConversionJob, JobQueue
from modules.site import Site, JobFormFields, Urls


@App.before_first_request
def _clean_uploads():
    if FileManager.clear_upload_folder():
        App.logger.info('Clean Upload folder created @ %s', App.config.get('UPLOAD_FOLDER'))
    else:
        App.logger.info('Could not create clean upload folder @ %s', App.config.get('UPLOAD_FOLDER'))


@App.route(Urls.root)
def index():
    App.logger.info('Endpoint: %s', request.endpoint)
    return render_template(Urls.templates[Urls.root], content=Site())


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
        App.logger.info('Upload succeeded for: %s', str(file_mgr.files))
        flash(message)

        JobQueue.add_job(
            ConversionJob(file_mgr.job_dir, file_mgr.files, request.form.get(JobFormFields.additional_args))
            )

        return redirect(Urls.current_job)


@App.route(Urls.current_job)
def job_page():
    App.logger.info('Endpoint: %s', request.endpoint)
    return render_template(Urls.templates[Urls.current_job], content=Site(), job=JobQueue.current_job())


@App.route(Urls.usd_man)
def usd_manual():
    usd_man_path = Path(get_current_modules_dir()) / 'usd_man' / 'usdzconvert_manual.txt'
    usd_man = 'No data available'
    with open(usd_man_path, 'r') as f:
        usd_man = f.read()

    return render_template(Urls.templates[Urls.usd_man], content=Site(), usd_manual=usd_man)


def import_dummy():
    # Doing nothing besides keeping the IDE from deleting imports
    pass
