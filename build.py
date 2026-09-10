#!/usr/bin/env python3
"""Сборщик сайта курса: markdown из _src/ → готовые HTML в фирменном стиле подкаста.

Запуск:  python3 build.py
Ничего, кроме стандартной библиотеки, не требуется.
"""
import html
import os
import re
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "_src")

# ─────────────────────────── разбор фронтматтера ───────────────────────────

def parse_front(text):
    """Шапка урока между строками --- : ключ: значение и списки через "- "."""
    if not text.startswith("---"):
        return {}, text
    end = text.index("\n---", 3)
    head, body = text[3:end], text[end + 4:]
    meta, key = {}, None
    for line in head.splitlines():
        if not line.strip():
            continue
        if line.lstrip().startswith("- ") and key:
            meta.setdefault(key, [])
            if not isinstance(meta[key], list):
                meta[key] = []
            meta[key].append(line.lstrip()[2:].strip())
        elif ":" in line:
            key, val = line.split(":", 1)
            key, val = key.strip(), val.strip()
            meta[key] = val if val else []
    return meta, body.lstrip("\n")

# ─────────────────────────── строчная разметка ───────────────────────────

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s

# ─────────────────────────── блочная разметка ───────────────────────────

def render(md):
    out, lines, i = [], md.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()

        if not s:
            i += 1
            continue

        # ::: контейнер заголовок … :::
        if s.startswith(":::"):
            parts = s[3:].strip().split(" ", 1)
            kind = parts[0]
            head = parts[1] if len(parts) > 1 else ""
            buf, i = [], i + 1
            while i < len(lines) and lines[i].strip() != ":::":
                buf.append(lines[i])
                i += 1
            i += 1
            out.append(container(kind, head, buf))
            continue

        # картинка отдельной строкой → figure с подписью
        m = re.match(r"^!\[(.*)\]\((.+)\)$", s)
        if m:
            cap = ('<figcaption>%s</figcaption>' % inline(m.group(1))) if m.group(1) else ""
            src = m.group(2)
            # кадра ещё нет на диске: честная заглушка вместо битой картинки
            local = os.path.normpath(os.path.join(ROOT, "l", src)) if src.startswith("..") else os.path.join(ROOT, src)
            if not os.path.exists(local):
                out.append('<div class="shot-todo"><b>Кадр экрана готовится</b>%s</div>'
                           % ('<span>%s</span>' % inline(m.group(1)) if m.group(1) else ""))
            else:
                out.append('<figure><img src="%s" alt="%s">%s</figure>'
                           % (html.escape(src), html.escape(m.group(1)), cap))
            i += 1
            continue

        # заголовки
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            lvl = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (lvl, inline(m.group(2)), lvl))
            i += 1
            continue

        # рубрика: строка вида «== ТЕКСТ»
        if s.startswith("== "):
            out.append('<p class="rubric">%s</p>' % inline(s[3:]))
            i += 1
            continue

        # горизонтальная линейка
        if s == "---":
            out.append('<div class="sep"></div>')
            i += 1
            continue

        # таблица
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            rows = [r for r in rows if not all(set(c) <= set("-: ") for c in r)]
            head = rows[0]
            body = rows[1:]
            # обёртка .tw: на телефоне широкая таблица прокручивается сама, не тянет страницу
            t = ['<div class="tw"><table class="kit"><tr>' + "".join("<th>%s</th>" % inline(c) for c in head) + "</tr>"]
            for r in body:
                # подпись колонки едет с ячейкой: на телефоне таблица разворачивается в карточки
                cells = []
                for n, c in enumerate(r):
                    lab = html.escape(head[n]) if n < len(head) else ""
                    cells.append('<td data-l="%s">%s</td>' % (lab, inline(c)))
                t.append("<tr>" + "".join(cells) + "</tr>")
            t.append("</table></div>")
            out.append("".join(t))
            continue

        # нумерованный список → шаги
        if re.match(r"^\d+\.\s", s):
            items = []
            # строка без номера, идущая следом, продолжает тот же шаг
            while i < len(lines) and lines[i].strip():
                cur = lines[i].strip()
                if re.match(r"^\d+\.\s", cur):
                    items.append(re.sub(r"^\d+\.\s", "", cur))
                elif items and not cur.startswith(("- ", ":::", "#", "|", "== ")):
                    items[-1] += " " + cur
                else:
                    break
                i += 1
            out.append('<ol class="steps">' + "".join("<li><span>%s</span></li>" % inline(x) for x in items) + "</ol>")
            continue

        # маркированный список
        if s.startswith("- "):
            items = []
            # строка без тире, идущая следом, продолжает тот же пункт
            while i < len(lines) and lines[i].strip():
                cur = lines[i].strip()
                if cur.startswith("- "):
                    items.append(cur[2:])
                elif items and not cur.startswith((":::", "#", "|", "== ")) and not re.match(r"^\d+\.\s", cur):
                    items[-1] += " " + cur
                else:
                    break
                i += 1
            out.append('<ul class="plain">' + "".join("<li>%s</li>" % inline(x) for x in items) + "</ul>")
            continue

        # абзац
        buf = []
        while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith((":::", "#", "- ", "|", "== ")) \
                and not re.match(r"^\d+\.\s", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        if not buf:            # ни одна ветка не подошла: не зацикливаемся, а пропускаем строку
            i += 1
            continue
        out.append("<p>%s</p>" % inline(" ".join(buf)))
    return "\n".join(out)


def container(kind, head, buf):
    """Врезки: грабли, заметка, цитата, промпт, терминал, цель, лид, ссылки."""
    if kind == "term":
        body = "\n".join(buf)
        body = html.escape(body, quote=False)
        # команды подсвечиваем: строка, начинающаяся с $
        body = re.sub(r"(?m)^(\$ .*)$", r"<b>\1</b>", body)
        body = re.sub(r"(?m)^(# .*)$", r"<i>\1</i>", body)
        cap = ('<span class="cap">%s</span>' % inline(head)) if head else ""
        return '<div class="term">%s%s</div>' % (body, cap)

    if kind == "prompt":
        body = html.escape("\n".join(buf), quote=False)
        return ('<div class="prompt"><div class="ph"><b>%s</b>'
                '<button type="button" data-copy>Скопировать</button></div>'
                '<pre>%s</pre></div>' % (inline(head or "Промпт"), body))

    if kind == "lead":
        return '<p class="lead">%s</p>' % inline(" ".join(x.strip() for x in buf if x.strip()))

    if kind == "goal":
        return ('<div class="goal"><b>%s</b><p>%s</p></div>'
                % (inline(head or "Что получится"), inline(" ".join(x.strip() for x in buf if x.strip()))))

    if kind in ("rake", "note", "q", "report"):
        inner = render("\n".join(buf))
        title = ("<b>%s</b>" % inline(head)) if head else ""
        return '<div class="%s">%s%s</div>' % (kind, title, inner)

    if kind == "links":
        items = []
        for ln in buf:
            m = re.match(r"^-?\s*\[(.+)\]\((.+?)\)(\s+alt)?$", ln.strip())
            if m:
                cls = ' class="alt"' if m.group(3) else ""
                items.append('<a href="%s"%s>%s</a>' % (html.escape(m.group(2)), cls, inline(m.group(1))))
        return '<div class="links">%s</div>' % "".join(items)

    if kind == "nums":
        cells = []
        for ln in buf:
            if "|" in ln:
                big, small = ln.split("|", 1)
                cells.append('<div><span class="num">%s</span><small>%s</small></div>'
                             % (inline(big.strip()), inline(small.strip())))
        return '<div class="nums">%s</div>' % "".join(cells)

    return render("\n".join(buf))

# ─────────────────────────── страницы ───────────────────────────

HEAD = """<!doctype html>
<html lang="ru">
<head>
<!-- собрано build.py, править надо _src/ -->
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="robots" content="noindex,nofollow">
<meta name="description" content="{descr}">
<link rel="stylesheet" href="{root}assets/style.css">
<link rel="icon" href="{root}assets/logo.png">
</head>
<body>"""

TOP = """<div class="top">
 <a class="home" href="{root}index.html"><img src="{root}assets/logo.png" alt=""><b>Автоматизация бизнеса с Клодом</b></a>
 <span>{right}</span>
</div>"""

FOOT = """<div class="foot">Личная программа обучения. Страница закрыта от поисковиков, ссылку не публикуем.<br>
Формат уроков подсмотрен у курса «AI Superpowers» (<a href="https://sfer.ai/edu/aisuperpowers3">sfer.ai</a>). Тексты, примеры и «грабли» здесь свои.</div>"""


def page(title, descr, right, body, root="", cls=""):
    return (HEAD.format(title=html.escape(title), descr=html.escape(descr), root=root)
            + '\n<div class="wrap%s">\n' % ((" " + cls) if cls else "")
            + TOP.format(root=root, right=html.escape(right)) + "\n"
            + body + "\n" + FOOT + "\n</div>\n"
            + '<script src="%sassets/app.js"></script>\n</body>\n</html>\n' % root)


def checklist_html(items, lesson_id):
    rows = []
    for n, text in enumerate(items, 1):
        cid = "%s-%02d" % (lesson_id, n)
        rows.append('<label><input type="checkbox" data-check="%s"><span>%s</span></label>' % (cid, inline(text)))
    return '<div class="check" data-lesson="%s">%s</div>' % (lesson_id, "".join(rows))


REPORT = """<div class="report">
 <b>Отчёт к созвону</b>
 <p>Отметьте сделанное выше, впишите, где застряли, и нажмите кнопку: текст скопируется, останется отправить его в мессенджер.</p>
 <textarea data-stuck placeholder="Где застрял, что непонятно"></textarea>
 <div class="row"><button type="button" data-report>Собрать отчёт</button><span class="ok" data-report-ok></span></div>
</div>"""


def build():
    lessons = []
    for name in sorted(os.listdir(os.path.join(SRC, "lessons"))):
        if not name.endswith(".md"):
            continue
        raw = open(os.path.join(SRC, "lessons", name), encoding="utf-8").read()
        meta, body = parse_front(raw)
        meta["slug"] = name[:-3]
        meta["body"] = body
        lessons.append(meta)

    os.makedirs(os.path.join(ROOT, "l"), exist_ok=True)

    # страницы уроков
    ready = [x for x in lessons if x.get("status", "ready") == "ready"]
    for idx, ls in enumerate(ready):
        num = ls["num"]
        lid = "l%s" % num
        parts = []
        parts.append('<div class="crumb"><i>УРОК %s</i><span>%s</span></div>' % (html.escape(num), inline(ls.get("time", ""))))
        parts.append("<h1>%s</h1>" % inline(ls["title"]))
        if ls.get("lead"):
            parts.append('<p class="lead">%s</p>' % inline(ls["lead"]))
        if ls.get("goal"):
            parts.append('<div class="goal"><b>Что получится</b><p>%s</p></div>' % inline(ls["goal"]))
        parts.append(render(ls["body"]))
        if ls.get("checklist"):
            parts.append('<h3>Чек-лист «сделано»</h3>')
            parts.append(checklist_html(ls["checklist"], lid))
            parts.append(REPORT)
        # переход между уроками
        prev_l = ready[idx - 1] if idx > 0 else None
        next_l = ready[idx + 1] if idx + 1 < len(ready) else None
        pager = ['<div class="pager">']
        if prev_l:
            pager.append('<a href="%s.html"><small>Предыдущий урок</small><b>%s. %s</b></a>'
                         % (prev_l["slug"], prev_l["num"], html.escape(prev_l["title"])))
        else:
            pager.append('<a href="../index.html"><small>Назад</small><b>К оглавлению</b></a>')
        if next_l:
            pager.append('<a class="next" href="%s.html"><small>Следующий урок</small><b>%s. %s</b></a>'
                         % (next_l["slug"], next_l["num"], html.escape(next_l["title"])))
        else:
            pager.append('<a class="next" href="../index.html"><small>Дальше</small><b>К оглавлению</b></a>')
        pager.append("</div>")
        parts.append("".join(pager))

        out = page("Урок %s. %s" % (num, ls["title"]), ls.get("goal", ""),
                   "Урок %s из 12" % num, "\n".join(parts), root="../")
        open(os.path.join(ROOT, "l", ls["slug"] + ".html"), "w", encoding="utf-8").write(out)

    # оглавление
    intro_meta, intro_body = parse_front(open(os.path.join(SRC, "index.md"), encoding="utf-8").read())
    toc = ['<div class="toc" data-toc>']
    for ls in lessons:
        if ls.get("status", "ready") == "ready":
            toc.append('<a href="l/%s.html" data-lesson-link="l%s"><i>%s</i><b>%s</b><span>%s</span></a>'
                        % (ls["slug"], ls["num"], html.escape(ls["num"]), inline(ls["title"]), inline(ls.get("goal", ""))))
        else:
            toc.append('<a class="soon"><i>%s</i><b>%s</b><span>%s</span><em>в работе</em></a>'
                        % (html.escape(ls["num"]), inline(ls["title"]), inline(ls.get("goal", ""))))
    toc.append("</div>")
    body = render(intro_body).replace("<!--TOC-->", "").replace("{{TOC}}", "")
    body = body.replace("<p>[оглавление]</p>", "".join(toc))
    out = page(intro_meta.get("title", "Автоматизация бизнеса с Клодом"),
               intro_meta.get("descr", ""), intro_meta.get("right", ""), body)
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(out)

    # база знаний: одной страницей из всех файлов _src/kb
    kb_parts = []
    kb_dir = os.path.join(SRC, "kb")
    if os.path.isdir(kb_dir):
        for name in sorted(os.listdir(kb_dir)):
            if name.endswith(".md"):
                meta, body = parse_front(open(os.path.join(kb_dir, name), encoding="utf-8").read())
                kb_parts.append(render(body))
    if kb_parts:
        out = page("База знаний курса", "Термины, цены, ссылки и шпаргалки к урокам",
                   "База знаний", "\n".join(kb_parts))
        open(os.path.join(ROOT, "kb.html"), "w", encoding="utf-8").write(out)

    print("Собрано: %d уроков (%d готовых), оглавление, база знаний"
          % (len(lessons), len(ready)))


if __name__ == "__main__":
    build()
