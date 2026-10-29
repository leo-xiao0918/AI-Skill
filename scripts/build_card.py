#!/usr/bin/env python3
"""Assemble a single-file HTML exam card plus a Markdown source from question.json.

Usage:
    python build_card.py --json question.json --out 试题卡.html [--md 试题卡.md]
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.normpath(
    os.path.join(HERE, "..", "assets", "exam_card_template.html")
)

BLOCK_MATH = re.compile(r"\$\$(.+?)\$\$", re.S)
INLINE_MATH = re.compile(r"(?<!\$)\$([^$\n]+?)\$(?!\$)")
UNCERTAIN = re.compile(r"⟦\?(.*?)\?⟧", re.S)

_missing_mathml: list[str] = []


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _as_text(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "\n".join(str(v) for v in value)
    return str(value)


def _math_html(tex: str, mathml_map: dict, display: bool) -> str:
    key = tex.strip()
    mapped = mathml_map.get(key) or mathml_map.get(tex)
    if mapped:
        if display and 'display="block"' not in mapped:
            mapped = mapped.replace("<math", '<math display="block"', 1)
        return mapped
    _missing_mathml.append(key)
    shown = html.escape(f"$${key}$$" if display else f"${key}$", quote=False)
    return f'<code class="missing">{shown}</code>'


def render_text(text: str, mathml_map: dict) -> str:
    """Escape text, substitute formulas with MathML, and mark uncertain spans."""
    blocks: list[str] = []

    def _block(match):
        blocks.append(_math_html(match.group(1), mathml_map, True))
        return f"\x00B{len(blocks) - 1}\x00"

    inlines: list[str] = []

    def _inline(match):
        inlines.append(_math_html(match.group(1), mathml_map, False))
        return f"\x00I{len(inlines) - 1}\x00"

    text = BLOCK_MATH.sub(_block, str(text))
    text = INLINE_MATH.sub(_inline, text)
    text = html.escape(text, quote=False)

    for index, markup in enumerate(blocks):
        token = f"\x00B{index}\x00"
        text = text.replace(token, f'<div class="formula-block">{markup}</div>')
    for index, markup in enumerate(inlines):
        text = text.replace(f"\x00I{index}\x00", markup)

    text = UNCERTAIN.sub(
        lambda m: f'<span class="uncertain">{m.group(1)}</span>', text
    )
    return text


def parse_md_table(text: str):
    rows = []
    for line in str(text).strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        rows.append([cell.strip() for cell in line.split("|")])

    header, body = None, []
    for row in rows:
        joined = "".join(row)
        if joined and set(joined) <= set("-: "):
            continue
        if header is None:
            header = row
        else:
            body.append(row)
    return header, body


def render_table(entry, mathml_map: dict) -> str:
    if isinstance(entry, dict):
        header = entry.get("header") or []
        body = entry.get("rows") or []
    else:
        header, body = parse_md_table(entry)

    out = ["<table>"]
    if header:
        out.append("<thead><tr>")
        for cell in header:
            out.append(f"<th>{render_text(str(cell), mathml_map)}</th>")
        out.append("</tr></thead>")
    if body:
        out.append("<tbody>")
        for row in body:
            out.append("<tr>")
            for cell in row:
                out.append(f"<td>{render_text(str(cell), mathml_map)}</td>")
            out.append("</tr>")
        out.append("</tbody>")
    out.append("</table>")
    return "".join(out)


def render_figure(fig: dict, base_dir: str, mathml_map: dict) -> str:
    caption = fig.get("caption") or fig.get("id") or "图"
    out = ['<div class="figure">']

    svg = fig.get("svg")
    image = fig.get("image")

    if svg:
        out.append(str(svg))
    elif image:
        path = image if os.path.isabs(image) else os.path.join(base_dir, image)
        if os.path.isfile(path):
            mime = mimetypes.guess_type(path)[0] or "image/png"
            with open(path, "rb") as handle:
                encoded = base64.b64encode(handle.read()).decode("ascii")
            alt = html.escape(str(caption), quote=True)
            out.append(f'<img src="data:{mime};base64,{encoded}" alt="{alt}">')
        else:
            out.append(f'<p class="missing">[图片缺失：{html.escape(str(image))}]</p>')
    else:
        out.append('<p class="missing">[未提供图形]</p>')

    position = fig.get("position")
    suffix = f"（位置：{html.escape(str(position))}）" if position else ""
    out.append(f'<div class="fig-cap">{html.escape(str(caption))}{suffix}</div>')
    out.append("</div>")
    return "".join(out)


def render_question(question: dict, mathml_map: dict, base_dir: str) -> str:
    out = ['<section class="question">']

    head = []
    number = question.get("number")
    if number:
        head.append(f'<span class="q-num">第 {html.escape(str(number))} 题</span>')
    for tag in (question.get("type"), question.get("score")):
        if tag:
            head.append(f'<span class="q-tag">{html.escape(str(tag))}</span>')
    if head:
        out.append(f'<div class="q-head">{"".join(head)}</div>')

    stem = _as_list(question.get("stem"))
    if stem:
        out.append('<div class="stem">')
        for para in stem:
            out.append(f"<p>{render_text(str(para), mathml_map)}</p>")
        out.append("</div>")

    options = _as_list(question.get("options"))
    if options:
        out.append('<ul class="options">')
        for option in options:
            out.append(f"<li>{render_text(str(option), mathml_map)}</li>")
        out.append("</ul>")

    for table in _as_list(question.get("tables")):
        out.append(render_table(table, mathml_map))

    for figure in _as_list(question.get("figures")):
        out.append(render_figure(figure, base_dir, mathml_map))

    answer = question.get("answer")
    if answer:
        out.append(
            f'<div class="answer"><strong>答案：</strong>'
            f'{render_text(_as_text(answer), mathml_map)}</div>'
        )
    else:
        out.append(
            '<div class="answer"><strong>答案：</strong>'
            '<span class="missing">原卷未提供</span></div>'
        )

    solution = question.get("solution")
    if solution:
        out.append(
            f'<div class="solution"><strong>解析：</strong>'
            f'{render_text(_as_text(solution), mathml_map)}</div>'
        )
    else:
        out.append(
            '<div class="solution"><strong>解析：</strong>'
            '<span class="missing">原卷未提供</span></div>'
        )

    uncertain = _as_list(question.get("uncertain"))
    if uncertain:
        out.append('<div class="pending"><h2>本题待确认</h2><ol>')
        for item in uncertain:
            out.append(f"<li>{render_text(str(item), mathml_map)}</li>")
        out.append("</ol></div>")

    out.append("</section>")
    return "".join(out)


def render_pending(items: list) -> str:
    if not items:
        return '<div class="pending"><h2>待确认项</h2><p>无。全部条目已通过识别校验。</p></div>'
    out = ['<div class="pending"><h2>待确认项</h2><ol>']
    for item in items:
        out.append(f"<li>{html.escape(str(item), quote=False)}</li>")
    out.append("</ol></div>")
    return "".join(out)


def to_markdown(data: dict) -> str:
    lines = [f"# {data.get('title', '试题还原卡')}", ""]
    source = data.get("source")
    if source:
        lines += [f"> 来源：{source}", ""]

    for question in data.get("questions", []):
        number = question.get("number")
        tags = " / ".join(str(t) for t in (question.get("type"), question.get("score")) if t)
        head = f"## 第 {number} 题" if number else "## 题目"
        if tags:
            head += f"（{tags}）"
        lines += [head, ""]

        for para in _as_list(question.get("stem")):
            lines += [str(para), ""]

        for option in _as_list(question.get("options")):
            lines += [f"- {option}", ""]

        for table in _as_list(question.get("tables")):
            if isinstance(table, dict):
                header = table.get("header") or []
                rows = table.get("rows") or []
                if header:
                    lines.append("| " + " | ".join(str(c) for c in header) + " |")
                    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
                for row in rows:
                    lines.append("| " + " | ".join(str(c) for c in row) + " |")
            else:
                lines.append(str(table))
            lines.append("")

        for figure in _as_list(question.get("figures")):
            caption = figure.get("caption") or figure.get("id") or "图"
            image = figure.get("image")
            if image:
                lines.append(f"![{caption}]({image})")
            else:
                lines.append(f"> 图：{caption}（内联 SVG 矢量图，见 HTML 版本）")
            if figure.get("position"):
                lines.append(f"> 位置：{figure['position']}")
            lines.append("")

        if question.get("answer"):
            lines += [f"**答案：** {question['answer']}", ""]
        if question.get("solution"):
            lines += [f"**解析：** {question['solution']}", ""]

        for item in _as_list(question.get("uncertain")):
            lines += [f"- 待确认：{item}", ""]

    pending = data.get("pending") or []
    if pending:
        lines += ["---", "", "## 待确认项", ""]
        for item in pending:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="由 question.json 生成单文件 HTML 试题卡与 Markdown 源文件")
    ap.add_argument("--json", required=True, help="结构化识别结果 question.json")
    ap.add_argument("--out", default="试题卡.html", help="输出 HTML 路径")
    ap.add_argument("--md", default=None, help="输出 Markdown 路径（默认与 HTML 同名）")
    args = ap.parse_args()

    if not os.path.isfile(args.json):
        print(f"[错误] 找不到文件: {args.json}")
        return 2

    with open(args.json, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    base_dir = os.path.dirname(os.path.abspath(args.json))
    mathml_map = data.get("mathml") or {}

    body_parts = []
    pending = list(data.get("pending") or [])

    for question in data.get("questions", []):
        body_parts.append(render_question(question, mathml_map, base_dir))
        number = question.get("number")
        for item in _as_list(question.get("uncertain")):
            prefix = f"第 {number} 题：" if number else ""
            pending.append(f"{prefix}{item}")

    if not data.get("questions"):
        body_parts.append('<p class="missing">[未识别到任何题目]</p>')

    if not os.path.isfile(TEMPLATE_PATH):
        print(f"[错误] 找不到模板: {TEMPLATE_PATH}")
        return 2

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as handle:
        template = handle.read()

    rendered = (template
                .replace("{{TITLE}}", html.escape(str(data.get("title", "试题还原卡"))))
                .replace("{{SOURCE}}", html.escape(str(data.get("source", "未标注"))))
                .replace("{{BODY}}", "\n".join(body_parts))
                .replace("{{PENDING}}", render_pending(pending)))

    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(rendered)

    md_path = args.md or os.path.splitext(args.out)[0] + ".md"
    md_dir = os.path.dirname(os.path.abspath(md_path))
    os.makedirs(md_dir, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(to_markdown(data))

    print(f"HTML 试题卡: {os.path.abspath(args.out)}")
    print(f"Markdown 源: {os.path.abspath(md_path)}")
    print(f"题目数: {len(data.get('questions', []))}    待确认项: {len(pending)}")

    if _missing_mathml:
        print("")
        print(f"[警告] 有 {len(set(_missing_mathml))} 个公式未提供 MathML，已降级为 LaTeX 原文显示：",
              file=sys.stderr)
        for key in sorted(set(_missing_mathml)):
            print(f"   - {key}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
