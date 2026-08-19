#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两遍执行 notebook 的 code cell —— 比 runnb.py 严格。

runnb.py 的漏洞：✏️ 练习的「自测 cell」会调用尚未实现的骨架函数，
抛出 NotImplementedError 后被整格 `continue` 跳过，
于是**练习的 assert 从来没有被真正执行过**（假通过）。

本脚本改成两遍：
  第一遍：按序执行全部 code cell，记录哪些 cell 因 NotImplementedError 被跳过。
          （执行过程中，📖 参考答案 cell 会把骨架函数重新定义为可用实现。）
  第二遍：按原顺序重跑第一遍被跳过的那些 cell —— 此时参考答案已生效，
          它们必须真正通过；任何失败都是真实缺陷。

用法: python3 runnb2.py <glob...>
"""
import io
import json
import sys
import glob
import contextlib
import traceback

fail = 0
total_nb = 0
total_code = 0
total_retried = 0

for pat in sys.argv[1:]:
    for path in sorted(glob.glob(pat)):
        total_nb += 1
        nb = json.load(open(path, encoding="utf-8"))
        ns = {"__name__": "__main__"}
        buf = io.StringIO()
        err = None
        skipped = []          # (index, source) —— 第一遍被 NotImplementedError 跳过的

        # ── 第一遍 ──
        for i, c in enumerate(nb["cells"]):
            if c["cell_type"] != "code":
                continue
            total_code += 1
            src = "".join(c["source"])
            try:
                with contextlib.redirect_stdout(buf):
                    exec(compile(src, f"{path}#cell{i}", "exec"), ns)
            except NotImplementedError:
                skipped.append((i, src))
            except Exception:
                err = (i, "pass1", traceback.format_exc(limit=3))
                break

        # ── 第二遍：重跑被跳过的 cell，此时参考答案已定义 ──
        if not err:
            for i, src in skipped:
                total_retried += 1
                try:
                    with contextlib.redirect_stdout(buf):
                        exec(compile(src, f"{path}#cell{i}", "exec"), ns)
                except Exception:
                    err = (i, "pass2(练习自测)", traceback.format_exc(limit=3))
                    break

        if err:
            fail += 1
            print(f"❌ {path}  cell[{err[0]}] {err[1]}\n{err[2]}")
        else:
            n = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
            print(f"✅ {path}  ({n} code cells, 第二遍重跑 {len(skipped)} 个练习自测)")

print(f"\n{total_nb} 个 notebook · {total_code} 个 code cell · "
      f"{total_retried} 个练习自测被真正验证")
print("全部通过" if not fail else f"{fail} 个 notebook 失败")
sys.exit(1 if fail else 0)
