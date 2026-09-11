/* Замок курса: страница приезжает зашифрованной, пароль превращается в ключ и открывает её.
   Ключ запоминается в браузере, поэтому пароль спрашивается один раз, а не на каждом уроке. */
(function () {
  var STORE = 'kurs-key';
  var box = document.querySelector('script[data-lock]');
  if (!box) return;
  var L = JSON.parse(box.textContent);

  var gate = document.querySelector('.gate');
  var form = document.querySelector('[data-gate]');
  var field = document.querySelector('[data-gate-pass]');
  var err = document.querySelector('[data-gate-err]');
  var slot = document.querySelector('[data-app]');

  function bytes(b64) {
    var raw = atob(b64), a = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) a[i] = raw.charCodeAt(i);
    return a;
  }
  function b64(buf) {
    var a = new Uint8Array(buf), s = '';
    for (var i = 0; i < a.length; i++) s += String.fromCharCode(a[i]);
    return btoa(s);
  }

  function derive(pass) {
    return crypto.subtle.importKey('raw', new TextEncoder().encode(pass), 'PBKDF2', false, ['deriveBits'])
      .then(function (base) {
        return crypto.subtle.deriveBits(
          { name: 'PBKDF2', salt: bytes(L.s), iterations: L.n, hash: 'SHA-256' }, base, 256);
      });
  }

  function unlock(rawKey) {
    return crypto.subtle.importKey('raw', rawKey, 'AES-GCM', false, ['decrypt'])
      .then(function (key) {
        return crypto.subtle.decrypt({ name: 'AES-GCM', iv: bytes(L.i) }, key, bytes(L.d));
      })
      .then(function (plain) {
        var page = JSON.parse(new TextDecoder().decode(plain));
        document.title = page.t;
        slot.innerHTML = page.h;
        if (gate) gate.parentNode.removeChild(gate);
        var s = document.createElement('script');
        s.src = L.r + 'assets/app.js';
        document.body.appendChild(s);
      });
  }

  // ключ с прошлого раза: пароль спрашивать не надо
  var saved = null;
  try { saved = localStorage.getItem(STORE); } catch (e) {}
  if (saved) {
    unlock(bytes(saved)).catch(function () {
      try { localStorage.removeItem(STORE); } catch (e) {}   // пароль сменили — спросим заново
      ask();
    });
  } else {
    ask();
  }

  function ask() {
    if (gate) gate.classList.add('ready');
    if (field) field.focus();
  }

  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var pass = (field.value || '').trim();
      if (!pass) return;
      err.textContent = '';
      form.classList.add('busy');
      derive(pass).then(function (rawKey) {
        return unlock(rawKey).then(function () {
          try { localStorage.setItem(STORE, b64(rawKey)); } catch (e) {}
        });
      }).catch(function () {
        form.classList.remove('busy');
        err.textContent = 'Пароль не подошёл. Проверьте раскладку и попробуйте ещё раз.';
        field.select();
      });
    });
  }
})();
