#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GLM-5.3-Flash 完整测试套件
=========================
对运行中的 OpenAI 兼容服务执行多维度测试，并把「输入内容 + 输出结果 + 耗时 + 判定」
全部写入 Markdown 报告。

用法:
    BASE_URL=http://127.0.0.1:8000 MODEL=glm-5.3-flash \
        python3 scripts/run_test_suite.py [--out report.md] [--skip long_context,multimodal]

测试类别:
    basic_chat       基础问答（中英文）
    reasoning_effort 思考预算对比（low/high/max，GLM 专属）
    multi_turn       多轮对话 + clear_thinking
    tool_calling     工具调用（需服务端 --enable-auto-tool-choice）
    coding           代码生成能力
    long_context     长上下文召回（默认 8K tokens）
    multimodal       图像理解（GLM-5.3-Flash 原生多模态）
    performance      响应延迟/生成速度基准

环境变量:
    BASE_URL   服务地址（默认 http://127.0.0.1:8000）
    MODEL      模型名（默认 glm-5.3-flash）
    TIMEOUT    单请求超时秒数（默认 300）
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
MODEL = os.environ.get("MODEL", "glm-5.3-flash")
TIMEOUT = int(os.environ.get("TIMEOUT", "300"))


def chat(messages, max_tokens=512, extra=None, tools=None, timeout=TIMEOUT):
    """调用 /v1/chat/completions，返回 (ok, data_or_error, elapsed)"""
    payload = {"model": MODEL, "messages": messages, "max_tokens": max_tokens}
    if extra:
        payload.update(extra)
    if tools:
        payload["tools"] = tools
    req = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode("utf-8")), time.time() - t0
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")[:500]
        return False, f"HTTP {e.code}: {body}", time.time() - t0
    except Exception as e:  # 连接失败/超时
        return False, f"{type(e).__name__}: {e}", time.time() - t0


def extract(data):
    """从响应中提取文本、思维链、工具调用、用量"""
    msg = data["choices"][0]["message"]
    return {
        "content": msg.get("content") or "",
        "reasoning": msg.get("reasoning_content") or "",
        "tool_calls": msg.get("tool_calls") or [],
        "usage": data.get("usage") or {},
    }


class Report:
    def __init__(self, path):
        self.path = path
        self.lines = []
        self.passed = self.failed = self.skipped = 0

    def head(self):
        self.lines += [
            "# GLM-5.3-Flash 测试报告",
            "",
            f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 服务地址：`{BASE_URL}`",
            f"- 模型名称：`{MODEL}`",
            "",
            "---",
            "",
        ]

    def case(self, name, title, inputs, outputs, ok, note=""):
        icon = "✅ PASS" if ok else ("⏭️ SKIP" if ok is None else "❌ FAIL")
        if ok is True:
            self.passed += 1
        elif ok is None:
            self.skipped += 1
        else:
            self.failed += 1
        self.lines += [
            f"## [{icon}] {title}",
            "",
            f"**用例**: `{name}`" + (f" ｜ **备注**: {note}" if note else ""),
            "",
            "**输入：**",
            "",
            "```json",
            json.dumps(inputs, ensure_ascii=False, indent=2),
            "```",
            "",
            "**输出：**",
            "",
            "```json",
            json.dumps(outputs, ensure_ascii=False, indent=2),
            "```",
            "",
        ]

    def summary(self):
        total = self.passed + self.failed + self.skipped
        self.lines += [
            "---",
            "",
            "## 汇总",
            "",
            "| 指标 | 数量 |",
            "|------|------|",
            f"| 总用例 | {total} |",
            f"| 通过 | {self.passed} |",
            f"| 失败 | {self.failed} |",
            f"| 跳过 | {self.skipped} |",
            "",
        ]
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines))
        return self.failed == 0


# ---------------- 各测试类别 ----------------

def t_basic_chat(r):
    """基础问答：中英文各一题"""
    cases = [
        ("basic_chat_zh", "中文：自我介绍",
         [{"role": "user", "content": "请用一句话介绍你自己。"}],
         lambda o: len(o["content"]) > 5),
        ("basic_chat_en", "英文：一句话解释稀疏注意力",
         [{"role": "user", "content": "Explain sparse attention in one sentence."}],
         lambda o: len(o["content"]) > 5),
    ]
    for name, title, msgs, check in cases:
        ok, data, dt = chat(msgs)
        if ok:
            o = extract(data)
            passed = check(o)
            o["_elapsed_s"] = round(dt, 2)
            r.case(name, title, {"messages": msgs, "max_tokens": 512},
                   o, passed)
        else:
            r.case(name, title, {"messages": msgs}, {"error": data}, False,
                   note=f"耗时 {dt:.1f}s")


def t_reasoning_effort(r):
    """思考预算对比：同一问题，low/high/max 三档（GLM 专属参数）"""
    q = "9.11 和 9.9 哪个大？简要说明理由。"
    for level in ("low", "high", "max"):
        name = f"reasoning_effort_{level}"
        msgs = [{"role": "user", "content": q}]
        extra = {"chat_template_kwargs": {"reasoning_effort": level}}
        ok, data, dt = chat(msgs, extra=extra)
        if ok:
            o = extract(data)
            o["_elapsed_s"] = round(dt, 2)
            r.case(name, f"思考预算 reasoning_effort={level}", {"messages": msgs, "chat_template_kwargs": {"reasoning_effort": level}}, o, len(o["content"]) > 0)
        else:
            r.case(name, f"思考预算 reasoning_effort={level}", {"messages": msgs}, {"error": data}, False, note=f"耗时 {dt:.1f}s")


def t_multi_turn(r):
    """多轮对话 + clear_thinking"""
    msgs = [
        {"role": "user", "content": "记住数字 42，后面我会问。"},
        {"role": "assistant", "content": "好的，我记住 42 了。"},
        {"role": "user", "content": "刚才让你记住的数字是多少？只回答数字。"},
    ]
    ok, data, dt = chat(msgs, extra={"chat_template_kwargs": {"clear_thinking": True}})
    if ok:
        o = extract(data)
        o["_elapsed_s"] = round(dt, 2)
        r.case("multi_turn", "多轮对话（clear_thinking=true）",
               {"messages": msgs, "chat_template_kwargs": {"clear_thinking": True}},
               o, "42" in o["content"])
    else:
        r.case("multi_turn", "多轮对话（clear_thinking=true）", {"messages": msgs}, {"error": data}, False, note=f"耗时 {dt:.1f}s")


def t_tool_calling(r):
    """工具调用：查询天气（需服务端启用 --enable-auto-tool-choice）"""
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名，如 北京"}},
                "required": ["city"],
            },
        },
    }]
    msgs = [{"role": "user", "content": "北京现在天气怎么样？"}]
    ok, data, dt = chat(msgs, tools=tools)
    if ok:
        o = extract(data)
        o["_elapsed_s"] = round(dt, 2)
        called = any(tc.get("function", {}).get("name") == "get_weather" for tc in o["tool_calls"])
        r.case("tool_calling", "工具调用（get_weather）",
               {"messages": msgs, "tools": tools}, o, called,
               note="未触发工具调用时检查服务端是否加 --enable-auto-tool-choice")
    else:
        r.case("tool_calling", "工具调用（get_weather）", {"messages": msgs}, {"error": data}, False, note=f"耗时 {dt:.1f}s")


def t_coding(r):
    """代码能力：写快速排序"""
    msgs = [{"role": "user", "content": "用 Python 写一个快速排序函数，附简短注释。"}]
    ok, data, dt = chat(msgs, max_tokens=768)
    if ok:
        o = extract(data)
        o["_elapsed_s"] = round(dt, 2)
        r.case("coding", "代码生成（Python 快速排序）", {"messages": msgs, "max_tokens": 768}, o,
               "def" in o["content"] and ("quick" in o["content"].lower() or "排序" in o["content"] or "sort" in o["content"].lower()))
    else:
        r.case("coding", "代码生成（Python 快速排序）", {"messages": msgs}, {"error": data}, False, note=f"耗时 {dt:.1f}s")


def t_long_context(r):
    """长上下文召回：8K tokens 填充文本末尾藏一个关键词"""
    filler = ("人工智能正在改变软件工程的方方面面。"
              "从代码补全到自动化测试，大模型已经成为开发者的日常工具。") * 260
    secret = "紫金山"
    prompt = filler + f"\n\n问题：请从上面文本中找出隐藏的地名，只回答地名本身。（提示：{secret} 是一个地名）"
    msgs = [{"role": "user", "content": prompt}]
    ok, data, dt = chat(msgs, max_tokens=64, timeout=600)
    if ok:
        o = extract(data)
        o["_elapsed_s"] = round(dt, 2)
        r.case("long_context", "长上下文召回（约 8K tokens）",
               {"messages": [{"role": "user", "content": prompt[:200] + "……（填充约 8K tokens）……" + prompt[-120:]}], "max_tokens": 64},
               o, secret in o["content"])
    else:
        r.case("long_context", "长上下文召回（约 8K tokens）", {"messages": ["……（约 8K tokens 填充）……"]}, {"error": data}, False, note=f"耗时 {dt:.1f}s")


def t_multimodal(r):
    """多模态：图像描述（GLM-5.3-Flash 原生多模态）"""
    # 一张 2x2 纯红 PNG（base64）
    red_png = ("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAACp8Z5+AAAAFElEQVR4nGP8z8DAwMDAxMDAwMAAAA4EAQ3aZ5QpAAAAAElFTkSuQmCC")
    msgs = [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{red_png}"}},
        {"type": "text", "text": "这张图片主要是什么颜色？"},
    ]}]
    ok, data, dt = chat(msgs, max_tokens=128)
    if ok:
        o = extract(data)
        o["_elapsed_s"] = round(dt, 2)
        r.case("multimodal", "多模态（图像颜色识别）",
               {"messages": [{"role": "user", "content": "[图片: 2x2 纯红 PNG] 这张图片主要是什么颜色？"}]},
               o, "红" in o["content"] or "red" in o["content"].lower())
    else:
        r.case("multimodal", "多模态（图像颜色识别）", {"messages": ["[图片] 这张图片主要是什么颜色？"]}, {"error": data}, False, note=f"耗时 {dt:.1f}s")


def t_performance(r):
    """性能基准：3 次短问答，统计 TTFT 与生成速度"""
    lat = []
    for i in range(3):
        msgs = [{"role": "user", "content": f"从1数到5。（第{i+1}次）"}]
        ok, data, dt = chat(msgs, max_tokens=64)
        if not ok:
            r.case("performance", "性能基准（3 次短问答）", {"messages": msgs}, {"error": data}, False)
            return
        o = extract(data)
        out_tok = o["usage"].get("completion_tokens", 0)
        speed = round(out_tok / dt, 1) if dt > 0 else 0
        lat.append({"round": i + 1, "elapsed_s": round(dt, 2),
                    "completion_tokens": out_tok, "tok_per_s": speed})
    avg = round(sum(x["tok_per_s"] for x in lat) / len(lat), 1)
    r.case("performance", "性能基准（3 次短问答）",
           {"messages": [{"role": "user", "content": "从1数到5。"}], "rounds": 3},
           {"rounds": lat, "avg_tok_per_s": avg}, avg > 0)


TESTS = {
    "basic_chat": t_basic_chat,
    "reasoning_effort": t_reasoning_effort,
    "multi_turn": t_multi_turn,
    "tool_calling": t_tool_calling,
    "coding": t_coding,
    "long_context": t_long_context,
    "multimodal": t_multimodal,
    "performance": t_performance,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=f"test-report-{datetime.now():%Y%m%d-%H%M%S}.md")
    ap.add_argument("--skip", default="", help="逗号分隔，跳过的测试类别")
    args = ap.parse_args()
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}

    r = Report(args.out)
    r.head()
    for name, fn in TESTS.items():
        if name in skip:
            r.case(name, f"{name}（已跳过）", {}, {"skipped": True}, None)
            continue
        print(f"==> 运行测试: {name}", flush=True)
        try:
            fn(r)
        except Exception as e:
            r.case(name, f"{name}（异常）", {}, {"exception": f"{type(e).__name__}: {e}"}, False)

    ok = r.summary()
    print(f"\n==> 报告已写入: {args.out}")
    print(f"==> 通过 {r.passed} / 失败 {r.failed} / 跳过 {r.skipped}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
