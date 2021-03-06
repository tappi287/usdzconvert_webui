'use_strict'

function dragDropUpload (uploadAllowedMapExt, uploadAllowedSceneExt, textureMapDict, sceneFileInputName, Pickr) {
  var textureMapCounter = 0
  var dropCounter = 0
  var textureTypesDict = {}

  /* Create Map/Dict for fast access to Texture Map type and description */
  for (let i = 0; i < textureMapDict.texture_map_types.length; i++) {
    const texType = textureMapDict.texture_map_types[i]

    textureTypesDict[texType] = {}
    textureTypesDict[texType].desc = textureMapDict.texture_map_desc[i]
    textureTypesDict[texType].channel_available = textureMapDict.texture_map_channel[i]
  }

  function createPicker (inputElement, buttonElement) {
    const pickr = new Pickr({
      el: buttonElement,
      /* useAsButton: true, */
      default: null,
      theme: 'nano',

      components: {
        preview: true,
        opacity: true,
        hue: true,

        interaction: {
          hex: false,
          rgba: true,
          hsva: false,
          hsla: true,
          input: true,
          save: true,
          clear: true,
          cancel: true
        }
      }
    }).on('init', pickr => {
      if (pickr.getSelectedColor() !== null) {
        inputElement.value = pickr.getSelectedColor().toRGBA().toString(0)
      } else {
        inputElement.value = ''
      }
    }).on('show', pickr => {
      if (pickr.getSelectedColor() === null) {
        /* Set pickr to a color so it will show something meaningful upon show */
        pickr.setColor('rgba(135, 67, 67, 1)', true/* silent */)
      }
    }).on('save', (color, pickr) => {
      if (color !== null) {
        inputElement.value = color.toRGBA().toString(0)
      } else {
        inputElement.value = ''
      }
      pickr.hide()
    }).on('cancel', pickr => {
      pickr.hide()
    })
    return pickr
  }

  function getFileExtension (path) {
    var regexp = /\.([0-9a-z]+)(?:[?#]|$)/i
    var extension = path.match(regexp)
    return extension && extension[1]
  }

  function guessMapTypeByFileName (filename) {
    if (filename.match(/.*(metallic)|(metalness)|(specular)/i)) { return 'metallic' }
    if (filename.match(/.*(normal)|(bump)/i)) { return 'normal' }
    if (filename.match(/.*(emissiveColor)|(emissive)/i)) { return 'emissiveColor' }
    if (filename.match(/.*(roughness)|(rough)|(roughnes)/i)) { return 'roughness' }
    if (filename.match(/.*(occlusion)|(ao)/i)) { return 'occlusion' }
    if (filename.match(/.*(opacity)|(alpha)/i)) { return 'opacity' }
    if (filename.match(/.*(clearcoat)|(coat)/i)) { return 'clearcoat' }
    if (filename.match(/.*(clearcoatrough)|(clearcoatroughness)/i)) { return 'clearcoatRoughness' }
    return 'diffuseColor'
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
    /* Update Texture Map description and channel availability on Texture Type change */
    e.addEventListener('change', function (event) {
      /* Update channel <select> enabled/disabled */
      if (textureTypesDict[event.target.value].channel_available) {
        channelElem.removeAttribute('disabled')
      } else {
        channelElem.setAttribute('disabled', 'disabled')
      }

      /* Update Texture Map Type description */
      descElem.innerHTML = textureTypesDict[event.target.value].desc
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

    /* event = null means the add color button was pressed */
    /* Abort on none-allowed files */
    if (event !== null) {
      if (checkFiles(event.dataTransfer.files, isFileMapAllowed) === false) {
        p.innerHTML = 'Allowed files: ' + uploadAllowedMapExt
        p.style.display = 'block'
        p.style.color = 'red'
        return
      }
    }

    p.style.display = 'none'
    p.style.color = ''
    document.getElementById('texture-map-spacer').style.display = 'none'
    dropCounter += 1

    /* Store the dropped files in hidden input because files array is immutable */
    const form = document.forms.reused_form
    const f = 'none'
    if (event !== null) {
      const f = document.createElement('input')
      f.type = 'file'
      f.name = 'texture_map_store_' + dropCounter
      f.style.display = 'none'
      f.files = event.dataTransfer.files
      form.appendChild(f)
    } else {
      const _file = []
      _file.name = 'EmptyMap_' + textureMapCounter

      event = []
      event.dataTransfer = []
      event.dataTransfer.files = [_file]
    }

    /* Disable async uploads for now */
    if (f === null) {
      const uploadFilesAsync = () => uploadAsFormData(f.files)
      uploadFilesAsync()
    }

    /* Create a Texture Map Field from hidden template for each dropped file */
    for (const file of event.dataTransfer.files) {
      textureMapCounter += 1

      /* Clone Texture Map Entry template */
      var textureNode = document.getElementById('texture-form-template').cloneNode(true)
      textureNode.style.display = 'block'
      textureNode.id = textureMapDict.file_storage + textureMapCounter

      /* Prepare storage of relevant input elements */
      let mapTypeSelect = null; let mapTypeDescSpan = null; let channelSelect = null

      /* Color Picker */
      const colorInput = textureNode.getElementsByTagName('input').material_color
      const colorBtn = textureNode.getElementsByTagName('button').material_color
      colorInput.name = textureMapDict.material_color + '_' + textureMapCounter
      createPicker(colorInput, colorBtn)

      /* Rename input/select elements with unique names */
      textureMapDict.html_element_class_names.forEach(function (value) {
        /* querySelector does not work outside the document */
        const e = textureNode.getElementsByClassName(value)
        if (e.length === 0) { return }

        /* Create unique name */
        e[0].name = value + '_' + textureMapCounter

        if (value === textureMapDict.file) { e[0].value = file.name };
        if (value === textureMapDict.file_label) { e[0].innerHTML = shortenFilename(file.name) };
        if (value === textureMapDict.type) { mapTypeSelect = e[0] };
        if (value === textureMapDict.type_desc) { mapTypeDescSpan = e[0] };
        if (value === textureMapDict.channel) { channelSelect = e[0] };
      })

      /* Update texture type desc span on Map type <select> change event */
      if (mapTypeSelect != null && mapTypeDescSpan != null && channelSelect != null) {
        mapTypeSelect.value = guessMapTypeByFileName(file.name)
        mapTypeDescSpan.innerHTML = textureTypesDict[mapTypeSelect.value].desc
        if (!textureTypesDict[mapTypeSelect.value].channel_available) {
          channelSelect.setAttribute('disabled', 'disabled')
        }
        updateMapTypeDesc(mapTypeSelect, mapTypeDescSpan, channelSelect)
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
      const addColorButton = document.getElementById(textureMapDict.add_color_btn_id)

      try {
        /* Test if our const where created by the Jinja template */
        if (uploadAllowedMapExt != null) {
          if (textureMapDict != null) {
            if (sceneFileInputName != null) {
              console.log('Tx Map constants created. Tx Maps Drag n Drop is getting ready.')
            }
          }
        }
      } catch (e) {
        console.error('Template did not declare necessary constants. Texture Map creation not available!', e)
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

      addColorButton.onclick = function () {
        createTextureMapField(textureMapContainer, null)
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
