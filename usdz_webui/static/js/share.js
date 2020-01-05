'use_strict'

function validateUrlInput (value) {
  /* Only allow A-Z 0-9 - _ characters */
  return value.replace(/[^A-Za-z0-9-_]/i, '').toLowerCase()
}

function validateFileNameInput (value) {
  /* Only allow A-Z 0-9 - _ . characters */
  return value.replace(/[^A-Za-z0-9-_.]/i, '')
}

function previewFile (file) {
  var preview = document.getElementById('share-preview-image')
  var reader = new window.FileReader()

  reader.onloadend = function () {
    preview.src = reader.result
  }

  if (file) {
    reader.readAsDataURL(file)
  } else {
    preview.src = ''
  }
}

function dropPreviewImage (event, inputs) {
  const p = document.getElementById('share-img-drop-text')

  p.style.display = 'none'

  if (event.dataTransfer.files[0] == null) {
    return
  }
  if (inputs.preview_image_store != null) {
    inputs.preview_image_store.remove()
  }
  const f = document.createElement('input')
  f.type = 'file'
  f.name = 'preview_image_store'
  f.style.display = 'none'
  f.files = event.dataTransfer.files
  document.forms.share.appendChild(f)

  previewFile(event.dataTransfer.files[0])
}

function sharePage (baseUrl) {
  console.log('BaseUrl: ' + baseUrl)

  function updateUrl (a, urlStore, urlInput) {
    const validValue = validateUrlInput(urlInput.value)
    urlInput.value = validValue

    a.href = baseUrl + '/' + validValue
    a.innerHTML = baseUrl + '/' + validValue
    urlStore.value = baseUrl + '/' + validValue
  }

  function setupInputs (inputs) {
    const a = document.getElementById('remote_url')
    const shareName = inputs.share_folder
    const fileInput = inputs.filename
    const urlInput = inputs.remote_url

    /* Validate input value while typing and update remote url */
    shareName.addEventListener('input', function (event) {
      updateUrl(a, urlInput, event.target)
    })
    fileInput.addEventListener('input', function (event) {
      event.target.value = validateFileNameInput(event.target.value)
    })

    /* Validate input values upon load */
    updateUrl(a, urlInput, shareName)
    fileInput.value = validateFileNameInput(fileInput.value)
  }

  document.onreadystatechange = function () {
    if (document.readyState === 'complete') {
      const inputs = document.forms.share.getElementsByTagName('input')
      const imgPreviewZone = document.getElementById('share-img-dropzone')
      const submitBtn = document.getElementById('submit-button')

      setupInputs(inputs)

      /* Prevent accidental drop to the document */
      document.ondragover = function (event) {
        event.preventDefault()
      }
      document.ondrop = function (event) {
        event.preventDefault()
      }

      /* Preview image drop */
      imgPreviewZone.ondragover = function (event) {
        event.preventDefault()
        imgPreviewZone.classList.add('entered')
      }

      imgPreviewZone.ondragleave = function (event) {
        event.preventDefault()
        imgPreviewZone.classList.remove('entered')
      }

      imgPreviewZone.ondrop = function (event) {
        event.preventDefault()
        imgPreviewZone.classList.remove('entered')
        dropPreviewImage(event, inputs)
      }

      /* Prevent submit button turbo mode Race conditions */
      document.forms.share.addEventListener('submit', function (event) {
        submitBtn.setAttribute('disabled', 'disabled')
        submitBtn.style.backgroundColor = 'grey'
        submitBtn.innerHTML = 'upload in progress'
      })
    }
  }
}

const fake = 'PassJStandardParse'
if (fake === null) {
  /* Will never be called, Jinja Template will call with necessary constants */
  sharePage(null)
}
