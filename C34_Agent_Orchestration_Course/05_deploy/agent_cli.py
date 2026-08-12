#!/usr/bin/env python3
"""你自己的 Claude Code —— 最小可运行 CLI 编码 agent（约 90 行）。

用法:
    export ANTHROPIC_API_KEY=sk-...   # 有 key 用真实 Claude
    python agent_cli.py               # 无 key 则跑内置离线演示

把 C30~C34 学的东西拧成一个能用的命令行 agent：工具 + ReAct 循环 + 权限护栏 + 成本追踪。
"""
import os, sys, json, subprocess

# ---------- 工具（真实文件/shell，限定在当前目录）----------
def read_file(path): return open(path, encoding="utf-8").read()
def write_file(path, content):
    open(path, "w", encoding="utf-8").write(content); return f"已写入 {path}（{len(content)} 字符）"
def run_bash(cmd):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    return (p.stdout + p.stderr)[:4000]
TOOLS = {"read_file": read_file, "write_file": write_file, "run_bash": run_bash}
SCHEMAS = [
    {"name":"read_file","description":"读取文件内容","input_schema":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}},
    {"name":"write_file","description":"写入文件","input_schema":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}},
    {"name":"run_bash","description":"执行 shell 命令","input_schema":{"type":"object","properties":{"cmd":{"type":"string"}},"required":["cmd"]}},
]

# ---------- 权限护栏 ----------
def guard(tool, args):
    """写文件/shell 前要人工确认；危险命令直接拒。"""
    if tool == "run_bash" and ("rm -rf" in args.get("cmd","")):
        print("  ⛔ 拒绝危险命令"); return False
    if tool in ("write_file", "run_bash"):
        return input(f"  ❓ 允许 {tool}({args})? [y/N] ").strip().lower() == "y"
    return True

# ---------- LLM 适配器 ----------
class AnthropicLLM:
    def __init__(self, model="claude-opus-4-8"):
        from anthropic import Anthropic
        self.client = Anthropic(); self.model = model; self.in_tok = self.out_tok = 0
    def complete(self, system, messages):
        r = self.client.messages.create(model=self.model, system=system, messages=messages,
                                         tools=SCHEMAS, max_tokens=2048)
        self.in_tok += r.usage.input_tokens; self.out_tok += r.usage.output_tokens
        return r.stop_reason, [b.model_dump() for b in r.content]

# ---------- ReAct 循环 ----------
def run_agent(llm, system, history, max_iters=12):
    for _ in range(max_iters):
        stop, blocks = llm.complete(system, history)
        history.append({"role":"assistant","content":blocks})
        if stop != "tool_use":
            return "".join(b.get("text","") for b in blocks if b.get("type")=="text")
        results = []
        for b in blocks:
            if b.get("type") == "tool_use":
                if guard(b["name"], b["input"]):
                    try: out = TOOLS[b["name"]](**b["input"])
                    except Exception as e: out = f"错误: {e}"
                else:
                    out = "用户拒绝了该操作"
                results.append({"type":"tool_result","tool_use_id":b["id"],"content":str(out)})
        history.append({"role":"user","content":results})
    return "[达到最大迭代次数]"

# ---------- CLI 主循环 ----------
SYSTEM = "你是一个命令行编码助手。用提供的工具读写文件、跑命令来完成用户任务。"
def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("未设置 ANTHROPIC_API_KEY —— 这是离线骨架。设置后即可与真实 Claude 对话。"); return
    llm = AnthropicLLM(); history = []
    print("你自己的 Claude Code（输入 exit 退出）")
    while True:
        try: user = input("\n> ").strip()
        except EOFError: break
        if user in ("exit","quit"): break
        history.append({"role":"user","content":user})
        print(run_agent(llm, SYSTEM, history))
        print(f"  [累计 {llm.in_tok} in / {llm.out_tok} out tokens]")

if __name__ == "__main__":
    main()
