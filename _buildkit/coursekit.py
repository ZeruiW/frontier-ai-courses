#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""coursekit.py —— house-style 课程生成器（纯标准库）。

对标 C43/C39 等「极深」课程的既有版式，重建的生成器：
  - index.html（hero + pills + card + track/grid 模块卡片）
  - NN_讲解.html（topbar + meta-box + 本章地图 TOC + 编号 h2 + pager）
  - NN_xxx.ipynb（markdown/code cell，kernelspec=python3）
  - README.md / glossary.md / references.md / requirements.txt
  - assets/style.css（从既有课程复制，保证 md5 一致）

用法见 build_c48.py ~ build_c52.py。
"""

import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLE_SRC = os.path.join(ROOT, "C43_Data_Engineering_Course", "assets", "style.css")


# ────────────────────────────────────────────────────────────────────
# 行内内容 helper：返回原始 HTML 片段（P/DUAL 等不转义，便于内嵌 <strong>/<code>）
# ────────────────────────────────────────────────────────────────────

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def P(*paras):
    return "".join("  <p>%s</p>" % p.strip() for p in paras)


def H3(t):
    return "  <h3>%s</h3>" % t


def DUAL(plain, formal):
    return (
        '  <div class="dual">\n'
        '    <div class="plain"><h4>直白说</h4>  <p>%s</p></div>\n'
        '    <div class="formal"><h4>严谨说</h4>  <p>%s</p></div>\n'
        "  </div>" % (plain.strip(), formal.strip())
    )


def CALLOUT(kind, body, label=""):
    """kind ∈ intuition | warn | danger | paper"""
    inner = body if body.strip().startswith("<") else "<p>%s</p>" % body.strip()
    return (
        '  <div class="callout %s"><span class="label">%s</span>\n    %s\n  </div>'
        % (kind, label, inner)
    )


def ASCII(text):
    return '  <div class="ascii">%s</div>' % esc(text.strip("\n"))


def CODE(text, lang=""):
    return "  <pre><code>%s</code></pre>" % esc(text.strip("\n"))


def MATH(tex):
    return '  <div class="math-block">\\[%s\\]</div>' % tex


def TABLE(headers, rows):
    th = "".join("<th>%s</th>" % h for h in headers)
    trs = "".join(
        "\n      <tr>%s</tr>" % "".join("<td>%s</td>" % c for c in r) for r in rows
    )
    return (
        "  <table>\n    <thead><tr>%s</tr></thead>\n    <tbody>%s\n    </tbody>\n  </table>"
        % (th, trs)
    )


def UL(items):
    return "  <ul>\n%s\n  </ul>" % "\n".join("    <li>%s</li>" % i for i in items)


def OL(items):
    return "  <ol>\n%s\n  </ol>" % "\n".join("    <li>%s</li>" % i for i in items)


# ────────────────────────────────────────────────────────────────────
# 讲解 HTML
# ────────────────────────────────────────────────────────────────────

_LESSON_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{tab}</title>
<link rel="stylesheet" href="../assets/style.css">
<script>
  window.MathJax = {{ tex: {{ inlineMath: [['$','$'],['\\\\(','\\\\)']], displayMath: [['$$','$$'],['\\\\[','\\\\]']] }} }};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
</head>
<body>

<div class="topbar"><div class="inner">
  <a class="home" href="../index.html">⌂ 课程主页</a>
  <a href="../glossary.md">术语词典</a>
  <a href="../references.md">论文清单</a>
  <span class="spacer"></span>
  <span style="color:var(--fg-dim)">MODULE {num} / {total:02d}</span>
</div></div>

<div class="wrap">

  <h1>{h1}</h1>
  <p class="subtitle">{subtitle}</p>

  <div class="meta-box">
{meta}
  </div>

  <div class="toc">
    <h3>本章地图</h3>
    <ol>
{toc}
    </ol>
  </div>

{body}

{pager}

</div>
</body>
</html>
"""


def lesson(path, num, total, h1, subtitle, meta, sections, prev=None, nxt=None):
    """sections: [(anchor, 标题, body_html), ...]  meta: [(k, v), ...]
    prev/nxt: (href, 标题) 或 None"""
    meta_html = "\n".join(
        '    <div class="item"><div class="k">%s</div><div class="v">%s</div></div>' % kv
        for kv in meta
    )
    toc_html = "\n".join(
        '      <li><a href="#%s">%s</a></li>' % (a, t) for a, t, _ in sections
    )
    body = []
    for i, (anchor, title, html_body) in enumerate(sections, 1):
        body.append(
            "  <!-- ========================================================= -->\n"
            '  <h2 id="%s"><span class="num">%d</span>%s</h2>\n%s\n'
            % (anchor, i, title, html_body)
        )
    pager = ""
    if prev or nxt:
        parts = ['  <div class="pager">']
        if prev:
            parts.append(
                '    <a class="prev" href="%s"><div class="dir">← 上一模块</div><div class="t">%s</div></a>'
                % prev
            )
        if nxt:
            parts.append(
                '    <a class="next" href="%s"><div class="dir">下一模块 →</div><div class="t">%s</div></a>'
                % nxt
            )
        parts.append("  </div>")
        pager = "\n".join(parts)

    out = _LESSON_TMPL.format(
        tab=h1,
        num=num,
        total=total,
        h1=h1,
        subtitle=subtitle,
        meta=meta_html,
        toc=toc_html,
        body="\n".join(body),
        pager=pager,
    )
    _write(path, out)
    return visible_chars(out)


def visible_chars(html_text):
    t = re.sub(r"(?s)<script.*?</script>", "", html_text)
    t = re.sub(r"(?s)<style.*?</style>", "", t)
    t = re.sub(r"(?s)<!--.*?-->", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    return len(re.sub(r"\s+", "", t))


# ────────────────────────────────────────────────────────────────────
# index.html
# ────────────────────────────────────────────────────────────────────

_INDEX_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} · 前沿 AI 系统培训</title>
<link rel="stylesheet" href="assets/style.css">
<style>
  .hero {{ text-align:center; padding: 40px 0 24px; }}
  .hero h1 {{ font-size: 2.8rem; }}
  .hero .subtitle {{ font-size: 1.15rem; max-width: 640px; margin: 12px auto 0; }}
  .pills {{ display:flex; gap:10px; justify-content:center; flex-wrap:wrap; margin: 24px 0 8px; }}
  .pill {{ font-size:.8rem; padding:6px 14px; border-radius:999px; border:1px solid var(--border);
          background: var(--bg-card); color: var(--fg-soft); font-family: var(--mono); }}
  .grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(260px,1fr)); gap:18px; margin:32px 0; }}
  .mod {{ display:block; text-decoration:none; background:var(--bg-card); border:1px solid var(--border);
         border-radius: var(--radius); padding:20px 22px; transition: .15s; color:inherit; }}
  .mod:hover {{ border-color: var(--accent); transform: translateY(-3px); }}
  .mod .n {{ font-family:var(--mono); font-size:.8rem; color:var(--accent); font-weight:700; }}
  .mod h3 {{ margin:6px 0 8px; color:var(--fg); font-size:1.12rem; }}
  .mod p {{ margin:0; font-size:.88rem; color:var(--fg-dim); line-height:1.55; }}
  .mod .links {{ margin-top:14px; display:flex; gap:10px; font-size:.78rem; font-family:var(--mono); }}
  .mod .links span {{ color:var(--accent-2); }}
  .track {{ margin: 40px 0 8px; font-size:.78rem; text-transform:uppercase; letter-spacing:.08em;
           color:var(--fg-dim); font-weight:700; border-left:3px solid var(--accent); padding-left:10px; }}
</style>
</head>
<body>
<div class="wrap">

  <div class="hero">
    <h1>{title}</h1>
    <p class="subtitle">{subtitle}</p>
    <div class="pills">
{pills}
    </div>
  </div>

  <div class="card">
{howto}
  </div>

{tracks}

  <hr>
  <p style="text-align:center; color:var(--fg-dim); font-size:.9rem;">
    自学型研究课程 · 中文讲解，英文术语 · notebook 实践 + ✏️ 练习 assert 判分 · 配合 <code>jupyter lab</code> 使用
  </p>

</div>
</body>
</html>
"""


def index(path, title, subtitle, pills, howto, tracks):
    """tracks: [(track_name, [(href, 'MODULE 00', 标题, 描述), ...]), ...]"""
    pills_html = "\n".join('      <span class="pill">%s</span>' % p for p in pills)
    tr = []
    for name, mods in tracks:
        cards = []
        for href, n, h3, desc in mods:
            cards.append(
                '    <a class="mod" href="%s">\n'
                '      <div class="n">%s</div><h3>%s</h3>\n'
                "      <p>%s</p>\n"
                '      <div class="links"><span>📓 notebook</span><span>📄 讲解</span></div>\n'
                "    </a>" % (href, n, h3, desc)
            )
        tr.append(
            '  <div class="track">%s</div>\n  <div class="grid">\n%s\n  </div>'
            % (name, "\n".join(cards))
        )
    _write(
        path,
        _INDEX_TMPL.format(
            title=title,
            subtitle=subtitle,
            pills=pills_html,
            howto="    <strong>怎么用：</strong> " + howto,
            tracks="\n\n".join(tr),
        ),
    )


# ────────────────────────────────────────────────────────────────────
# notebook
# ────────────────────────────────────────────────────────────────────

def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(text)}


def code(text):
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": _lines(text),
    }


def _lines(text):
    t = text.strip("\n")
    return [l + "\n" for l in t.split("\n")[:-1]] + [t.split("\n")[-1]]


def notebook(path, cells):
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    _write(path, json.dumps(nb, ensure_ascii=False, indent=1))
    return len(cells)


# ────────────────────────────────────────────────────────────────────
# 杂项
# ────────────────────────────────────────────────────────────────────

def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def text_file(path, content):
    _write(path, content.strip() + "\n")


def install_assets(course_dir):
    os.makedirs(os.path.join(course_dir, "assets"), exist_ok=True)
    shutil.copyfile(STYLE_SRC, os.path.join(course_dir, "assets", "style.css"))


def report(course_dir):
    """构建后自检：打印每个产物的尺寸/可见字符/cell 数。"""
    print("\n== 自检 · %s ==" % os.path.basename(course_dir))
    ok = True
    for dirpath, _, files in sorted(os.walk(course_dir)):
        for fn in sorted(files):
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, course_dir)
            size = os.path.getsize(fp)
            if fn.endswith(".html") and fn != "index.html":
                v = visible_chars(open(fp, encoding="utf-8").read())
                # 00_overview 按既有课程惯例为轻量总览（~5-6K），其余讲解页要求 >=8000
                floor = 4800 if fn == "00_overview.html" else 8000
                flag = "" if v >= floor else "  ⚠️ <%d" % floor
                if v < floor:
                    ok = False
                print("  %-46s %7d B  可见 %6d 字%s" % (rel, size, v, flag))
            elif fn.endswith(".ipynb"):
                n = len(json.load(open(fp, encoding="utf-8"))["cells"])
                print("  %-46s %7d B  %3d cells" % (rel, size, n))
            elif fn in ("glossary.md", "references.md", "README.md", "index.html",
                        "requirements.txt"):
                print("  %-46s %7d B" % (rel, size))
    return ok
