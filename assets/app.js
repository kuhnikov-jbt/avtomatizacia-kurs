/* Галочки, отчёт к созвону и копирование промптов. Всё живёт в браузере ученика. */
(function () {
  var KEY = 'kurs-progress';

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; }
  }
  function save(data) {
    try { localStorage.setItem(KEY, JSON.stringify(data)); } catch (e) {}
  }

  // ── страница урока: галочки ─────────────────────────────────────────────
  var box = document.querySelector('.check');
  if (box) {
    var lesson = box.getAttribute('data-lesson');
    var data = load();
    var marks = data[lesson] || (data[lesson] = { items: {} });
    if (!marks.items) marks.items = {};

    var inputs = box.querySelectorAll('input[data-check]');

    function sync(input) {
      input.closest('label').classList.toggle('done', input.checked);
    }
    function total() {
      var n = 0;
      inputs.forEach(function (i) { if (i.checked) n++; });
      return n;
    }
    function store() {
      marks.done = total();
      marks.total = inputs.length;
      marks.at = new Date().toISOString().slice(0, 10);
      save(data);
    }

    inputs.forEach(function (input) {
      var id = input.getAttribute('data-check');
      input.checked = !!marks.items[id];
      sync(input);
      input.addEventListener('change', function () {
        marks.items[id] = input.checked;
        sync(input);
        store();
      });
    });
    store();

    // ── кнопка «собрать отчёт» ────────────────────────────────────────────
    var btn = document.querySelector('[data-report]');
    if (btn) {
      btn.addEventListener('click', function () {
        var title = document.querySelector('h1').textContent.trim();
        var crumb = document.querySelector('.crumb i');
        // заголовок собранного текста: у урока свой, у отдельной страницы задаётся в data-title
        var head = btn.getAttribute('data-title');
        var lines = [];
        lines.push(head ? head
                        : 'Отчёт по уроку: ' + (crumb ? crumb.textContent.trim() + '. ' : '') + title);
        lines.push('Дата: ' + new Date().toLocaleDateString('ru-RU'));
        lines.push('Сделано: ' + total() + ' из ' + inputs.length);
        lines.push('');
        inputs.forEach(function (i) {
          lines.push((i.checked ? '[x] ' : '[ ] ') + i.nextElementSibling.textContent.trim());
        });
        var stuck = document.querySelector('[data-stuck]');
        if (stuck && stuck.value.trim()) {
          lines.push('');
          lines.push((btn.getAttribute('data-stuck-label') || 'Где застрял') + ': ' + stuck.value.trim());
        }
        var text = lines.join('\n');
        var ok = document.querySelector('[data-report-ok]');
        function done(msg) { if (ok) { ok.textContent = msg; setTimeout(function () { ok.textContent = ''; }, 4000); } }

        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(function () { done('Отчёт скопирован, вставляйте в сообщение'); },
                                                   function () { fallback(); });
        } else { fallback(); }

        function fallback() {
          if (stuck) {
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
            document.body.appendChild(ta);
            ta.select();
            try { document.execCommand('copy'); done('Отчёт скопирован, вставляйте в сообщение'); }
            catch (e) { done('Скопировать не удалось, выделите текст вручную'); }
            document.body.removeChild(ta);
          }
        }
      });
    }
  }

  // ── оглавление: отметка пройденных уроков ───────────────────────────────
  var links = document.querySelectorAll('[data-lesson-link]');
  if (links.length) {
    var d = load();
    links.forEach(function (a) {
      // в черновике ссылка на урок сводит сразу несколько подуроков: ключи через пробел
      var keys = a.getAttribute('data-lesson-link').split(' ');
      var done = 0, total = 0;
      keys.forEach(function (k) {
        var x = d[k];
        if (x) { done += x.done || 0; total += x.total || 0; }
      });
      if (a.hasAttribute('data-total')) total = +a.getAttribute('data-total');
      var m = (done || total) && keys.some(function (k) { return d[k]; }) ? { done: done, total: total } : null;
      if (m && m.total && m.done >= m.total) a.classList.add('done');
      else if (m && m.done) {
        var mark = document.createElement('em');
        mark.textContent = m.done + ' из ' + m.total;
        a.appendChild(mark);
      }
    });
  }

  // ── страница урока в черновике: отчёт по галочкам всех подуроков ─────────
  var hub = document.querySelector('[data-hub-items]');
  var hubBtn = document.querySelector('[data-report]');
  if (hub && hubBtn && !box) {
    hubBtn.addEventListener('click', function () {
      var subs = JSON.parse(hub.textContent), d = load(), all = 0, got = 0, rows = [];
      Object.keys(subs).forEach(function (k) {
        var items = (d[k] && d[k].items) || {};
        rows.push('');
        rows.push(subs[k].t);
        subs[k].c.forEach(function (c) {
          all++; if (items[c[0]]) got++;
          rows.push((items[c[0]] ? '[x] ' : '[ ] ') + c[1]);
        });
      });
      var crumb = document.querySelector('.crumb i');
      var lines = ['Отчёт по уроку: ' + (crumb ? crumb.textContent.trim() + '. ' : '') + document.querySelector('h1').textContent.trim(),
                   'Дата: ' + new Date().toLocaleDateString('ru-RU'),
                   'Сделано: ' + got + ' из ' + all].concat(rows);
      var stuck = document.querySelector('[data-stuck]');
      if (stuck && stuck.value.trim()) { lines.push(''); lines.push('Где застрял: ' + stuck.value.trim()); }
      var text = lines.join('\n'), ok = document.querySelector('[data-report-ok]');
      function done(msg) { if (ok) { ok.textContent = msg; setTimeout(function () { ok.textContent = ''; }, 4000); } }
      function fallback() {
        var ta = document.createElement('textarea');
        ta.value = text; ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
        document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); done('Отчёт скопирован, вставляйте в сообщение'); }
        catch (e) { done('Скопировать не удалось, выделите текст вручную'); }
        document.body.removeChild(ta);
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () { done('Отчёт скопирован, вставляйте в сообщение'); }, fallback);
      } else { fallback(); }
    });
  }

  // ── кнопки «скопировать» у промптов ─────────────────────────────────────
  document.querySelectorAll('[data-copy]').forEach(function (b) {
    b.addEventListener('click', function () {
      var pre = b.closest('.prompt').querySelector('pre');
      var text = pre.textContent;
      function ok() { var old = b.textContent; b.textContent = 'Скопировано'; setTimeout(function () { b.textContent = old; }, 2000); }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(ok, sel);
      } else { sel(); }
      function sel() {
        var r = document.createRange();
        r.selectNodeContents(pre);
        var s = window.getSelection();
        s.removeAllRanges();
        s.addRange(r);
        try { document.execCommand('copy'); ok(); } catch (e) { b.textContent = 'Выделено, нажмите Ctrl+C'; }
      }
    });
  });
})();
