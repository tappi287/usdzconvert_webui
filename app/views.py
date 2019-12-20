import os
from flask import render_template, redirect, request, flash
from werkzeug.utils import secure_filename

from app import App
from app.site import SiteContent

ALLOWED_EXTENSIONS = {'obj', 'gltf', 'glb', 'fbx', 'abc', 'usd', 'usda', 'usdc', 'usdz',
                      'tga', 'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@App.route('/')
def index():
    print(App.config)
    print(App.secret_key)
    return render_template("index.html", content=SiteContent())


@App.route('/', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected for uploading')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            file.save(App.config['UPLOAD_FOLDER'] / filename)
            flash('File successfully uploaded')
            return redirect('/')
        else:
            flash(f'Allowed file types are {", ".join(ALLOWED_EXTENSIONS)}')
            return redirect(request.url)
