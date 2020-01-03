'use_strict'

function textureMapDragDrop (uploadAllowedExt, textureMapTypes, textureMapDesc, textureMapChannel) {
  var textureMapCounter = 0
  var dropCounter = 0

  function getFileExtension (path) {
    var regexp = /\.([0-9a-z]+)(?:[?#]|$)/i
    var extension = path.match(regexp)
    return extension && extension[1]
  }

  function isFileAllowed (fileExt) {
    if (uploadAllowedExt.indexOf(fileExt) === -1) {
      return false
    }
    return true
  }

  function checkFiles (files) {
    for (let fileIdx = 0; fileIdx < files.length; fileIdx++) {
      if (isFileAllowed(getFileExtension(files[fileIdx].name)) === false) {
        return false
      }
    }
    return true
  }

  function previewFile () {
    var preview = document.querySelector('img')
    var file = document.querySelector('input[type=file]').files[0]
    var reader = new FileReader()

    reader.onloadend = function () {
      preview.src = reader.result
    }

    if (file) {
      reader.readAsDataURL(file)
    } else {
      preview.src = ''
    }
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

  function createTextureMapField (container, event) {
    const p = document.getElementById('drop_text')

    /* Abort on none-allowed files */
    if (checkFiles(event.dataTransfer.files) === false) {
      p.innerHTML = 'Allowed files: ' + uploadAllowedExt
      p.style.display = 'block'
      p.style.color = 'red'
      return
    }

    p.style.display = 'none'
    p.style.color = ''
    dropCounter += 1

    /* Store the dropped files in hidden input because files array is immutable */
    const f = document.createElement('input')
    f.type = 'file'
    f.name = 'texture_map_store_' + dropCounter
    f.style.display = 'none'
    f.files = event.dataTransfer.files
    /* add the hidden input to form */
    document.getElementById('reused_form').appendChild(f)

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
      const textureMapContainer = document.getElementById('texture-map-container')

      try {
      /* Test if our const where created by the Jinja template */
        if (uploadAllowedExt != null) {
          if (textureMapTypes != null) {
            if (textureMapDesc != null) {
              if (textureMapChannel != null) {
                console.log('Tx Map constants created. Tx Maps Drag n Drop is getting ready.')
              }
            }
          }
        }
      } catch (e) {
        console.error('Template did not declare necessary Constants. Texture Map creation not available!', e)
        return
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
  textureMapDragDrop(null, null, null, null, null)
}
