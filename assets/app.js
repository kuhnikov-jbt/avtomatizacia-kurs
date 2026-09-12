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
      var m = d[a.getAttribute('data-lesson-link')];
      if (m && m.total && m.done >= m.total) a.classList.add('done');
      else if (m && m.done) {
        var mark = document.createElement('em');
        mark.textContent = m.done + ' из ' + m.total;
        a.appendChild(mark);
      }
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
