'use_strict'

function dragDropUpload (uploadAllowedMapExt, uploadAllowedSceneExt, textureMapTypes, textureMapDesc, textureMapChannel, sceneFileInputName) {
  var textureMapCounter = 0
  var dropCounter = 0

  function getFileExtension (path) {
    var regexp = /\.([0-9a-z]+)(?:[?#]|$)/i
    var extension = path.match(regexp)
    return extension && extension[1]
  }

  function isFileMapAllowed (fileExt) {
    if (uploadAllowedMapExt.indexOf(fileExt) === -1) {
      return false
    }
    return true
  }

  function isFileSceneAllowed (fileExt) {
    if (uploadAllowedSceneExt.indexOf(fileExt) === -1) {
      return false
    }
    return true
  }

  function checkFiles (files, checkMethod) {
    for (let fileIdx = 0; fileIdx < files.length; fileIdx++) {
      if (checkMethod(getFileExtension(files[fileIdx].name)) === false) {
        return false
      }
    }
    return true
  }

  function shortenFilename (filename) {
    const l = filename.length
    const m = 55

    if (l > m) {
      return ''.concat(filename.slice(0, m - 15), ' ~ ', filename.slice(l - 15, l + 1))
    } else {
      return filename
    }
  }

  function updateMapTypeDesc (e, descElem, channelElem) {
    e.addEventListener('change', function (event) {
      const textureType = event.target.value
      let desc = ''

      for (let i = 0; i < textureMapTypes.length; i++) {
        if (textureMapTypes[i] === textureType) {
          desc = textureMapDesc[i]

          if (textureMapChannel[i]) {
            channelElem.removeAttribute('disabled')
          } else {
            channelElem.setAttribute('disabled', 'disabled')
          }
          break
        }
      }

      descElem.innerHTML = desc
    })
  }

  function updateSceneFileInput (event) {
    const sceneFileInput = document.getElementsByName(sceneFileInputName)
    const p = document.getElementById('scene_file_drop_text')

    if (sceneFileInput[0] === null) {
      return
    }
    if (checkFiles(event.dataTransfer.files, isFileSceneAllowed) === false) {
      p.innerHTML = 'Allowed scene files: ' + uploadAllowedSceneExt
      p.style.color = 'red'
      return
    }

    document.getElementById('scene-file-spacer').style.display = 'none'
    sceneFileInput[0].files = event.dataTransfer.files
    let msg = ''

    for (let fileIdx = 0; fileIdx < event.dataTransfer.files.length; fileIdx++) {
      msg += event.dataTransfer.files[fileIdx].name + ' + '
    }
    p.style.color = ''
    p.style.fontWeight = 'bold'
    p.innerHTML = msg.slice(0, msg.length - 3)
  }

  const uploadAsFormData = (files) => {
    const newFormData = new window.FormData()

    for (const file of files) {
      newFormData.append('files', file, file.name)
    }
    console.log('Form Data to send: ' + newFormData.files)

    window.fetch('/upload', {
      method: 'POST',
      body: newFormData
    }).then(
      response => response.json()
    ).then(
      success => console.log(success)
    ).catch(
      error => console.log(error)
    )
  }

  function createTextureMapField (container, event) {
    const p = document.getElementById('drop_text')

    /* Abort on none-allowed files */
    if (checkFiles(event.dataTransfer.files, isFileMapAllowed) === false) {
      p.innerHTML = 'Allowed files: ' + uploadAllowedMapExt
      p.style.display = 'block'
      p.style.color = 'red'
      return
    }

    p.style.display = 'none'
    p.style.color = ''
    document.getElementById('texture-map-spacer').style.display = 'none'
    dropCounter += 1

    /* Store the dropped files in hidden input because files array is immutable */
    const f = document.createElement('input')
    f.type = 'file'
    f.name = 'texture_map_store_' + dropCounter
    f.style.display = 'none'
    f.files = event.dataTransfer.files
    /* add the hidden input to form */
    document.getElementById('reused_form').appendChild(f)

    /* Disable async uploads for now */
    if (f === null) {
      const uploadFilesAsync = () => uploadAsFormData(f.files)
      uploadFilesAsync()
    }

    /* Create a Texture Map Field from hidden template for each dropped file */
    for (let fileIdx = 0; fileIdx < event.dataTransfer.files.length; fileIdx++) {
      const filename = event.dataTransfer.files[fileIdx].name
      var textureNode = document.getElementById('texture-form-template').cloneNode(true)

      textureMapCounter += 1
      let mapTypeElem = null
      let mapTypeDescElem = null
      let channelElem = null
      textureNode.style.display = 'block'
      textureNode.id = 'texture_map_' + textureMapCounter

      /* Rename input elements with unique names */
      const t = ['texture_file_label', 'texture_file', 'texture_type', 'texture_channel', 'texture_material', 'texture_description']

      t.forEach(function (value) {
        const e = textureNode.getElementsByClassName(value)
        if (e.length === 0) {
          return
        }
        /* Create unique name */
        e[0].name = value + '_' + textureMapCounter

        if (value === 'texture_file') { e[0].value = filename };
        if (value === 'texture_file_label') { e[0].innerHTML = shortenFilename(filename) };
        if (value === 'texture_type') { mapTypeElem = e[0] };
        if (value === 'texture_description') { mapTypeDescElem = e[0] };
        if (value === 'texture_channel') { channelElem = e[0] }
      })

      /* Update texture type desc span on Map type <select> change event */
      if (mapTypeElem != null && mapTypeDescElem != null && channelElem != null) {
        mapTypeDescElem.innerHTML = textureMapDesc[0]
        channelElem.setAttribute('disabled', 'disabled')
        updateMapTypeDesc(mapTypeElem, mapTypeDescElem, channelElem)
      }

      /* Add the Texture Node input element */
      container.appendChild(textureNode)
    }
  };

  document.onreadystatechange = function () {
    if (document.readyState === 'complete') {
      const dropzone = document.getElementById('dropzone')
      const sceneFileDropzone = document.getElementById('scene-file-dropzone')
      const textureMapContainer = document.getElementById('texture-map-container')

      try {
      /* Test if our const where created by the Jinja template */
        if (uploadAllowedMapExt != null) {
          if (textureMapTypes != null) {
            if (textureMapDesc != null) {
              if (textureMapChannel != null) {
                if (sceneFileInputName != null) {
                  console.log('Tx Map constants created. Tx Maps Drag n Drop is getting ready.')
                }
              }
            }
          }
        }
      } catch (e) {
        console.error('Template did not declare necessary Constants. Texture Map creation not available!', e)
        return
      }

      /* Prevent accidental drop to the document */
      document.ondragover = function (event) {
        event.preventDefault()
      }
      document.ondrop = function (event) {
        event.preventDefault()
      }

      sceneFileDropzone.ondragover = function (event) {
        event.preventDefault()
        sceneFileDropzone.classList.add('entered')
      }

      sceneFileDropzone.ondragleave = function (event) {
        event.preventDefault()
        sceneFileDropzone.classList.remove('entered')
      }

      sceneFileDropzone.ondrop = function (event) {
        event.preventDefault()
        sceneFileDropzone.classList.remove('entered')
        updateSceneFileInput(event)
      }

      dropzone.ondragover = function (event) {
        event.preventDefault()
        dropzone.classList.add('entered')
      }

      dropzone.ondragleave = function (event) {
        event.preventDefault()
        dropzone.classList.remove('entered')
      }

      dropzone.ondrop = function (event) {
        event.preventDefault()
        dropzone.classList.remove('entered')
        createTextureMapField(textureMapContainer, event)
      }
      console.log('Tx Maps Drag n Drop ready.')
    }
  }
}

const fake = 'PassJStandardParse'
if (fake === null) {
  /* Will never be called, Jinja Template will call with necessary constants */
  dragDropUpload(null, null, null, null, null, null)
}
