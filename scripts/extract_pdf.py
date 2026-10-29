#!/usr/bin/env python3
"""Render a PDF into per-page PNGs and dump embedded text/images.

Usage:
    python extract_pdf.py <file.pdf> --out <dir> [--dpi 240] [--images]
"""
from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="把 PDF 渲染为逐页 PNG 并导出内嵌文本")
    ap.add_argument("pdf", help="输入 PDF 路径")
    ap.add_argument("--out", default="pdf_pages", help="输出目录（默认 pdf_pages）")
    ap.add_argument("--dpi", type=int, default=240, help="渲染 DPI，建议 200-300")
    ap.add_argument("--images", action="store_true", help="同时导出内嵌图片")
    args = ap.parse_args()

    try:
        import pymupdf  # type: ignore
    except Exception:
        print("[错误] 未安装 PyMuPDF，无法处理 PDF。安装: pip install PyMuPDF")
        return 2

    if not os.path.isfile(args.pdf):
        print(f"[错误] 找不到文件: {args.pdf}")
        return 2

    os.makedirs(args.out, exist_ok=True)
    img_dir = os.path.join(args.out, "embedded_images")
    if args.images:
        os.makedirs(img_dir, exist_ok=True)

    doc = pymupdf.open(args.pdf)
    page_count = doc.page_count
    print(f"文件: {os.path.basename(args.pdf)}   页数: {page_count}   渲染 DPI: {args.dpi}")

    for index in range(page_count):
        page = doc.load_page(index)
        stem = f"page_{index + 1:03d}"

        pix = page.get_pixmap(dpi=args.dpi)
        png_path = os.path.join(args.out, f"{stem}.png")
        pix.save(png_path)

        text = page.get_text()
        txt_path = os.path.join(args.out, f"{stem}.txt")
        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write(text)

        has_text_layer = bool(text.strip())
        print(f"  {stem}.png  文字层: {'有' if has_text_layer else '无（纯扫描件）'}  -> {txt_path}")

        if args.images:
            for img_index, info in enumerate(page.get_images(full=True), start=1):
                xref = info[0]
                try:
                    pix_img = pymupdf.Pixmap(doc, xref)
                    if pix_img.n > 4:
                        pix_img = pymupdf.Pixmap(pymupdf.csRGB, pix_img)
                    out_path = os.path.join(img_dir, f"{stem}_img{img_index}.png")
                    pix_img.save(out_path)
                    print(f"     内嵌图片 -> {out_path}")
                except Exception as exc:
                    print(f"     内嵌图片 xref={xref} 抽取失败: {exc}")

    doc.close()
    print("")
    print(f"完成。输出目录: {os.path.abspath(args.out)}")
    print("提示: 含文字层的页面可用 .txt 与识别结果交叉校验数字与符号。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
