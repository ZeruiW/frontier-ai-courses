#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""顺序执行 notebook 的 code cell，报告第一个失败。用法: python3 runnb.py <glob...>"""
import io
import json
import sys
import glob
import contextlib
import traceback

fail = 0
for pat in sys.argv[1:]:
    for path in sorted(glob.glob(pat)):
        nb = json.load(open(path, encoding="utf-8"))
        ns = {"__name__": "__main__"}
        buf = io.StringIO()
        err = None
        for i, c in enumerate(nb["cells"]):
            if c["cell_type"] != "code":
                continue
            src = "".join(c["source"])
            try:
                with contextlib.redirect_stdout(buf):
                    exec(compile(src, f"{path}#cell{i}", "exec"), ns)
            except NotImplementedError:
                continue  # ✏️ 练习骨架，学习者填写；自测 cell 由参考答案覆盖后再跑
            except Exception:
                err = (i, traceback.format_exc(limit=3))
                break
        if err:
            fail += 1
            print(f"❌ {path}  cell[{err[0]}]\n{err[1]}")
        else:
            n = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
            print(f"✅ {path}  ({n} code cells)")
print(f"\n{'全部通过' if not fail else str(fail) + ' 个 notebook 失败'}")
sys.exit(1 if fail else 0)
