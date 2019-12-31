var texture_map_counter = 0;
var drop_counter = 0;

function getFileExtension(path) {
    var regexp = /\.([0-9a-z]+)(?:[\?#]|$)/i
    var extension = path.match(regexp)
    return extension && extension[1]
}

function isFileAllowed(file_ext) {
    if (upload_allowed_ext.indexOf(file_ext) == -1) {
        return false;
    }
    return true;
}

function checkFiles(files) {
    for (let file_idx = 0; file_idx < files.length; file_idx++) {
        if (isFileAllowed(getFileExtension(files[file_idx].name)) == false) {
            return false
        }
    }
    return true
}

function createTextureMapField(container, event) {
    let p = document.getElementById("drop_text");

    /* Abort on none-allowed files */
    if (checkFiles(event.dataTransfer.files) == false) {
        p.innerHTML = "Allowed files: " + upload_allowed_ext;
        p.style.display = 'block';
        p.style.color = 'red';
        return
    }

    p.style.display = 'none';
    p.style.color = '';
    drop_counter += 1

    /* Store the dropped files in hidden input because files array is immutable */
    let f = document.createElement("input")
    f.type = "file";
    f.name = "texture_map_store_" + drop_counter
    f.style.display = "none";
    f.files = event.dataTransfer.files
    /* add the hidden input to form */
    document.getElementById("reused_form").appendChild(f)
    
    /* Create a Texture Map Field from hidden template for each dropped file */
    for (let file_idx = 0; file_idx < event.dataTransfer.files.length; file_idx++) {
        let filename = event.dataTransfer.files[file_idx].name

        texture_map_counter += 1;
        var texture_node = document.getElementById("texture-form-template").cloneNode(true);
        texture_node.style.display = 'block';
        texture_node.id = 'texture_map_' + texture_map_counter;
    
        /* Rename input elements with unique names */
        let t = ['texture_file_label', 'texture_file_name', 'texture_type', 'texture_channel', 'texture_material']

        t.forEach( function(value) {
            let e = texture_node.getElementsByClassName(value);
            if (e.length == 0) {
                return
            }
            /* Create unique name */
            e[0].name = value + "_" + texture_map_counter;
            
            if (value == 'texture_file_name') { e[0].value = filename }
            if (value == 'texture_file_label') {
                e[0].innerHTML = filename
            }
        });
    
        container.appendChild(texture_node);
    }
};

document.onreadystatechange = function () {
    if (document.readyState == 'complete') {
        const dropzone = document.getElementById("dropzone")
        const texture_map_container = document.getElementById("texture-map-container");

        dropzone.ondragover = function(event) {
            event.preventDefault();
            dropzone.classList.add('entered');
        }

        dropzone.ondragleave = function(event) {
            event.preventDefault();
            dropzone.classList.remove('entered');
        }
        
        dropzone.ondrop = function(event) {
            event.preventDefault();
            dropzone.classList.remove('entered');
            createTextureMapField(texture_map_container, event);
        }
        console.log('Document ready.')
    }
};
