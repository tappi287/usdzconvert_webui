'use_strict'

function setupHoverPreviewImage (a, img, offset) {
  if (img === null) { return }
  if (a === null) { return }
  if (offset === null) { offset = false }

  a.onmouseover = function (event) {
    img.style.display = 'block'
    const aRect = a.getBoundingClientRect()
    let x = aRect.left
    if (offset === true) {
      x = aRect.left - (img.width / 2)
    }
    const y = aRect.bottom + 5
    img.style.left = x + 'px'
    img.style.top = y + 'px'
  }
  a.onmouseleave = function () {
    img.style.display = 'none'
  }
}

function setupImage (entryId) {
  /* Move preview image from it's nested position to document body */
  const img = document.getElementById('dl_img_' + entryId)
  if (img === null) { return null }
  document.body.appendChild(img)
  return document.getElementById('dl_img_' + entryId)
}

function downloads (dl) {
  document.onreadystatechange = function () {
    if (document.readyState === 'complete') {
      for (const entry in dl) {
        const entryId = dl[entry][0]
        /* File Text Link */
        const a = document.getElementById('dl_link_' + entryId)
        /* Preview Button */
        const b = document.getElementById('dl_pre_' + entryId)
        const img = setupImage(entryId)

        setupHoverPreviewImage(a, img)
        setupHoverPreviewImage(b, img, true)
      }
    }
  }
}

const fake = 'PassJStandardParse'
if (fake === null) {
  /* Will never be called, Jinja Template will call with necessary constants */
  downloads(null)
}
