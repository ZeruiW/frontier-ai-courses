import io, sys, contextlib, traceback, importlib
mods = sys.argv[1:]
fail = 0
for name in mods:
    m = importlib.import_module(name)
    ns = {"__name__": "__main__"}
    buf = io.StringIO(); skipped = []; err = None
    cells = [c for c in m.NB if c["cell_type"] == "code"]
    for i, c in enumerate(cells):
        src = "".join(c["source"])
        try:
            with contextlib.redirect_stdout(buf):
                exec(compile(src, f"{name}#cell{i}", "exec"), ns)
        except NotImplementedError:
            skipped.append((i, src))
        except Exception:
            err = (i, traceback.format_exc(limit=3)); break
    if not err:
        for i, src in skipped:
            try:
                with contextlib.redirect_stdout(buf):
                    exec(compile(src, f"{name}#cell{i}", "exec"), ns)
            except Exception:
                err = (i, "pass2\n" + traceback.format_exc(limit=3)); break
    if err:
        fail += 1
        print(f"❌ {name} cell[{err[0]}]\n{err[1]}")
    else:
        print(f"✅ {name} ({len(cells)} cells, {len(skipped)} 练习自测重跑)")
sys.exit(1 if fail else 0)
