function validatePassword (pswd, confirmPswd) {
  function validate () {
    if (pswd.value !== confirmPswd.value) {
      confirmPswd.setCustomValidity("Passwords don't match")
      confirmPswd.parentElement.parentElement.classList.add('invalid')
    } else {
      confirmPswd.setCustomValidity('')
      confirmPswd.parentElement.parentElement.classList.remove('invalid')
    }
  }

  pswd.addEventListener('input', function (event) {
    validate()
  })
  confirmPswd.addEventListener('input', function (event) {
    validate()
  })
}

function setupInputs () {
  var inputs = document.forms.host.getElementsByTagName('input')
  var pswd = inputs.pswd
  var confirmPswd = inputs.confirm_pswd

  if (pswd !== null && confirmPswd !== null) {
    console.log('Setting up Password validation')
    validatePassword(pswd, confirmPswd)
  }
}

document.onreadystatechange = function () {
  if (document.readyState === 'complete') {
    setupInputs()
  }
}
