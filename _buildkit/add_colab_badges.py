#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给全站 53 门课添加「一键在 Colab 打开」：
   ① 每个 notebook 顶部插入官方 Colab 徽章（新的第一个 markdown cell）
   ② 每门课 index.html 的每个模块卡片旁加一个小 Colab 按钮

纯附加、幂等（重复运行不会重复插入）、不改变任何已有学习内容。
仓库信息未知时用占位符 __GITHUB_USER__ / __GITHUB_REPO__ / __GITHUB_BRANCH__，
建好仓库后用 set_colab_repo.py 一次性替换。
"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER, REPO, BRANCH = "__GITHUB_USER__", "__GITHUB_REPO__", "__GITHUB_BRANCH__"
BADGE_IMG = "https://colab.research.google.com/assets/colab-badge.svg"


def colab_url(relpath):
    return f"https://colab.research.google.com/github/{USER}/{REPO}/blob/{BRANCH}/{relpath}"


def patch_notebook(path, relpath):
    nb = json.load(open(path, encoding="utf-8"))
    cells = nb["cells"]
    if cells and "colab.research.google.com" in "".join(cells[0].get("source", [])):
        return False  # 已插入过，幂等跳过
    badge_src = f"[![Open In Colab]({BADGE_IMG})]({colab_url(relpath)})"
    cells.insert(0, {"cell_type": "markdown", "metadata": {}, "source": [badge_src]})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    return True


CSS_ADD = """  .mod .modlink { display:block; text-decoration:none; color:inherit; }
  .mod .colabbtn { display:inline-flex; align-items:center; gap:5px; margin-top:12px;
                   font-size:.72rem; font-family:var(--mono); padding:4px 10px;
                   border-radius:999px; border:1px solid var(--border); color:var(--accent-2);
                   text-decoration:none; }
  .mod .colabbtn:hover { border-color:var(--accent); color:var(--accent); }
"""
CSS_ANCHOR = "  .mod .links span { color:var(--accent-2); }\n"

CARD_RE = re.compile(
    r'<a class="mod" href="([^"]+)">(.*?)</a>', re.S
)


def patch_index(path, course_dir):
    html = open(path, encoding="utf-8").read()
    if "colabbtn" in html:
        return False  # 已插入过，幂等跳过

    def repl(m):
        href, inner = m.group(1), m.group(2)
        modfolder = os.path.dirname(href)
        nbs = glob.glob(os.path.join(course_dir, modfolder, "*.ipynb"))
        assert len(nbs) == 1, f"{path}: {href} 下 notebook 数量 != 1 ({nbs})"
        relpath = os.path.relpath(nbs[0], ROOT)
        url = colab_url(relpath)
        return (
            '<div class="mod">\n'
            f'    <a class="modlink" href="{href}">{inner}</a>\n'
            f'    <a class="colabbtn" href="{url}" target="_blank" rel="noopener" '
            f'title="在 Colab 打开该模块的 notebook">▶ 在 Colab 打开</a>\n'
            "  </div>"
        )

    new_html, n = CARD_RE.subn(repl, html)
    assert n > 0, f"{path}: 没有匹配到任何模块卡片"
    assert CSS_ANCHOR in new_html, f"{path}: 找不到 CSS 锚点行"
    new_html = new_html.replace(CSS_ANCHOR, CSS_ANCHOR + CSS_ADD, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)
    return n


def main():
    n_nb = n_idx = 0
    for course_dir in sorted(glob.glob(os.path.join(ROOT, "C*_*"))):
        if not os.path.isdir(course_dir):
            continue
        idx = os.path.join(course_dir, "index.html")
        if os.path.exists(idx):
            r = patch_index(idx, course_dir)
            if r:
                n_idx += 1
        for nb_path in sorted(glob.glob(os.path.join(course_dir, "*", "*.ipynb"))):
            relpath = os.path.relpath(nb_path, ROOT)
            if patch_notebook(nb_path, relpath):
                n_nb += 1
    print(f"✅ notebook 徽章新插入 {n_nb} 个；index.html 新打补丁 {n_idx} 个"
          f"（占位符 {USER}/{REPO}@{BRANCH}，跑 set_colab_repo.py 替换成真实仓库）")


if __name__ == "__main__":
    main()
