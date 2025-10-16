// static/script.js
document.addEventListener('click', function(e){
  // Edit laptop populate
  if(e.target && e.target.classList.contains('edit-laptop')){
    var tr = e.target.closest('tr');
    var id = tr.dataset.id;
    document.getElementById('laptopFormId').value = id;
    document.getElementById('lf_name').value = tr.dataset.name || '';
    document.getElementById('lf_studentID').value = tr.dataset.studentid || '';
    document.getElementById('lf_phone').value = tr.dataset.phone || '';
    document.getElementById('lf_serial').value = tr.dataset.serial || '';
    document.getElementById('lf_make').value = tr.dataset.make || '';
    document.getElementById('lf_model').value = tr.dataset.model || '';
    window.scrollTo(0,0);
  }

  // Clear laptop form
  if(e.target && e.target.id === 'laptopClear'){
    var fields = ['laptopFormId','lf_name','lf_studentID','lf_phone','lf_serial','lf_make','lf_model'];
    fields.forEach(function(id){ var el = document.getElementById(id); if(el) el.value = ''; });
  }

  // Open record for sign in/out
  if(e.target && e.target.classList.contains('open-record')){
    var id = e.target.getAttribute('data-id');
    var signed = e.target.getAttribute('data-signed') === '1' || e.target.getAttribute('data-signed') === 'true' || e.target.getAttribute('data-signed') === 'True';
    var signModalEl = document.getElementById('signModal');
    var signModal = new bootstrap.Modal(signModalEl, {});
    var info = "";
    var tr = e.target.closest('tr');
    if(tr){
      info = "Serial: " + (tr.dataset.serial || '') + " — Student: " + (tr.querySelector('td') ? tr.querySelector('td').innerText : '');
    }
    document.getElementById('signModalInfo').innerText = info;
    document.getElementById('sign_id').value = id;
    var action = signed ? 'signout' : 'signin';
    document.getElementById('sign_action').value = action;
    var btn = document.getElementById('signActionBtn');
    btn.innerText = signed ? 'Sign Out' : 'Sign In';
    btn.disabled = false;
    signModal.show();
  }
});

// AJAX sign form submit
document.addEventListener('submit', function(e){
  if(e.target && e.target.id === 'signForm'){
    e.preventDefault();
    var form = e.target;
    var btn = document.getElementById('signActionBtn');
    btn.disabled = true;
    fetch(form.action, {
      method: 'POST',
      headers: { 'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(new FormData(form))
    }).then(function(res){ return res.json(); })
    .then(function(data){
      if(data && data.ok){
        location.reload();
      } else {
        alert('Action failed.');
        btn.disabled = false;
      }
    }).catch(function(err){
      console.error(err);
      alert('Network error.');
      btn.disabled = false;
    });
  }
});
