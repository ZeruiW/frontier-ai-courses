#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 add_colab_badges.py 留下的占位符换成真实的 GitHub 仓库信息。

用法：
    python3 set_colab_repo.py <github_user> <repo> [branch]

例：
    python3 set_colab_repo.py zerui-x ai-courses
    python3 set_colab_repo.py zerui-x ai-courses develop

默认分支是 main。这是一次性的占位符填充：只替换尚未处理过的 `__GITHUB_USER__` /
`__GITHUB_REPO__` / `__GITHUB_BRANCH__` 三个 token，跑第二次不会重复替换（已替换的
文件不会再匹配到占位符，脚本会照实报告 0 处），不会破坏已经填好的内容。
如果后续要整体换成另一个仓库地址，用编辑器/命令行工具批量替换旧的 user/repo/branch 字符串即可。
"""
import glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 与 add_colab_badges.py 里的占位符完全一致（那边是字面量 token，不是正则）：
# f"https://colab.research.google.com/github/{USER}/{REPO}/blob/{BRANCH}/{relpath}"
PLACEHOLDERS = ("__GITHUB_USER__", "__GITHUB_REPO__", "__GITHUB_BRANCH__")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    user, repo = sys.argv[1], sys.argv[2]
    branch = sys.argv[3] if len(sys.argv) > 3 else "main"
    replacements = dict(zip(PLACEHOLDERS, (user, repo, branch)))

    n_files = n_hits = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "C*_*", "*", "*.ipynb"))) + \
                sorted(glob.glob(os.path.join(ROOT, "C*_*", "index.html"))):
        text = open(path, encoding="utf-8").read()
        new_text, k = text, 0
        for token, value in replacements.items():
            k += new_text.count(token)
            new_text = new_text.replace(token, value)
        if k:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text)
            n_files += 1
            n_hits += k
    print(f"✅ 已替换 {n_hits} 处占位符 -> github.com/{user}/{repo}/blob/{branch}/"
          f"（覆盖 {n_files} 个文件）")


if __name__ == "__main__":
    main()
