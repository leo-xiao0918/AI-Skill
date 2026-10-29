#!/usr/bin/env python3
"""Assess exam-image quality and preprocess it before recognition.

Usage:
    python preprocess_image.py <image> --report-only
    python preprocess_image.py <image> --out <dir> [--deskew] [--denoise]
                               [--binarize] [--scale 2] [--auto]
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    import numpy as np
except Exception:
    np = None

try:
    from PIL import Image, ImageFilter
except Exception:
    Image = None
    ImageFilter = None


def _require_pillow() -> None:
    if Image is None:
        sys.exit("[错误] 未安装 Pillow，无法预处理。安装: pip install Pillow")


def np_gray(img):
    return np.asarray(img.convert("L"), dtype=np.float64)


def laplacian_var(a):
    """Variance of the Laplacian response; low values mean blurry."""
    if np is None:
        return None
    if a.shape[0] < 3 or a.shape[1] < 3:
        return None
    out = (a[0:-2, 1:-1] + a[1:-1, 0:-2] + a[1:-1, 2:] + a[2:, 1:-1]
           - 4.0 * a[1:-1, 1:-1])
    return float(out.var())


def line_height_px(a):
    """Estimate text line height from contiguous dark-row bands."""
    rows = (a < 200).sum(axis=1)
    bands, run = [], 0
    for value in rows:
        if value > 0:
            run += 1
        else:
            if run:
                bands.append(run)
            run = 0
    if run:
        bands.append(run)
    if not bands:
        return None
    bands.sort()
    return float(bands[len(bands) // 2])


def estimate_skew(gray):
    """Return the angle (degrees) that maximizes row-projection variance."""
    if np is None:
        return 0.0
    width, height = gray.size
    scale = min(1.0, 1200.0 / max(width, height))
    work = gray.resize((max(1, int(width * scale)), max(1, int(height * scale))),
                       Image.BILINEAR)
    best_angle, best_score = 0.0, -1.0
    for step in range(-10, 11):
        angle = step * 0.5
        rotated = work.rotate(angle, resample=Image.BILINEAR, expand=True, fillcolor=255)
        projection = (np.asarray(rotated, dtype=np.float64) < 200).sum(axis=1)
        score = float(projection.astype(np.float64).var())
        if score > best_score:
            best_score, best_angle = score, float(angle)
    return best_angle


def otsu_threshold(a):
    if np is None:
        return 128
    hist, _ = np.histogram(a.astype(np.uint8), bins=256, range=(0, 256))
    hist = hist.astype(np.float64)
    total = hist.sum()
    if total == 0:
        return 128
    weight_bg = np.cumsum(hist)
    weight_fg = total - weight_bg
    safe_bg = np.where(weight_bg == 0, 1, weight_bg)
    safe_fg = np.where(weight_fg == 0, 1, weight_fg)
    cum_sum = np.cumsum(hist * np.arange(256))
    mean_bg = cum_sum / safe_bg
    mean_fg = (cum_sum[-1] - cum_sum) / safe_fg
    variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
    return int(np.nanargmax(variance))


def quality_report(path, img, skew):
    a = np_gray(img) if np is not None else None
    dpi = img.info.get("dpi")
    report = [
        ("文件", os.path.basename(path)),
        ("尺寸", f"{img.size[0]} x {img.size[1]} px"),
        ("DPI", f"{dpi[0]:.0f}" if dpi else "未记录（无法判定）"),
        ("倾斜角(估算)", f"{skew:.1f}°" + ("（需纠斜）" if abs(skew) > 3 else "")),
    ]
    if a is not None:
        blur = laplacian_var(a)
        if blur is not None:
            verdict = "（偏模糊，建议去噪 + 放大）" if blur < 100 else "（可接受）"
            report.append(("清晰度(拉普拉斯方差)", f"{blur:.1f} {verdict}"))
        lh = line_height_px(a)
        if lh is not None:
            verdict = "（偏小，建议放大）" if lh < 20 else ""
            report.append(("文字行高(估算)", f"{lh:.0f} px {verdict}"))
        bright = a[a >= 200]
        if bright.size:
            report.append(("背景标准差", f"{float(bright.std()):.1f}"))
    return report


def preprocess(img, skew, deskew, denoise, binarize, scale):
    work = img.convert("L")

    if denoise:
        work = work.filter(ImageFilter.MedianFilter(size=3))

    if deskew and abs(skew) > 0.5:
        work = work.rotate(-skew, resample=Image.BICUBIC, expand=True, fillcolor=255)

    a = np_gray(work) if np is not None else None
    if a is not None:
        low, high = float(a.min()), float(a.max())
        if high - low > 1:
            stretched = (a - low) / (high - low) * 255.0
            work = Image.fromarray(stretched.astype("uint8"), mode="L")
            a = np_gray(work)

    if binarize and a is not None:
        threshold = otsu_threshold(a)
        mask = (a > threshold) * 255
        work = Image.fromarray(mask.astype("uint8"), mode="L")

    if scale and abs(scale - 1.0) > 1e-6:
        work = work.resize((max(1, int(work.size[0] * scale)),
                            max(1, int(work.size[1] * scale))), Image.LANCZOS)
    return work


def main() -> int:
    ap = argparse.ArgumentParser(description="评估并预处理试题图像")
    ap.add_argument("image")
    ap.add_argument("--out", default=None, help="输出目录；省略则只评估")
    ap.add_argument("--report-only", action="store_true", help="只打印质量报告")
    ap.add_argument("--deskew", action="store_true", help="纠斜")
    ap.add_argument("--denoise", action="store_true", help="中值滤波去噪")
    ap.add_argument("--binarize", action="store_true", help="二值化（仅纯黑白印刷体）")
    ap.add_argument("--scale", type=float, default=1.0, help="放大倍数，如 2")
    ap.add_argument("--auto", action="store_true", help="按质量报告自动决策处理步骤")
    args = ap.parse_args()

    _require_pillow()
    if np is None:
        print("[警告] 未安装 NumPy，清晰度与倾斜评估将跳过。安装: pip install numpy")

    if not os.path.isfile(args.image):
        print(f"[错误] 找不到文件: {args.image}")
        return 2

    img = Image.open(args.image)
    img.load()
    skew = estimate_skew(img.convert("L"))

    print("=== 质量报告 ===")
    for key, value in quality_report(args.image, img, skew):
        print(f"  {key}: {value}")

    if args.auto:
        a = np_gray(img) if np is not None else None
        blur = laplacian_var(a) if a is not None else None
        lh = line_height_px(a) if a is not None else None
        args.deskew = args.deskew or abs(skew) > 3
        args.denoise = args.denoise or (blur is not None and blur < 100)
        args.scale = args.scale if args.scale > 1 else (2.0 if (lh is not None and lh < 20) else 1.0)
        print("")
        print(f"自动决策: 纠斜={args.deskew} 去噪={args.denoise} 二值化={args.binarize} 放大={args.scale}x")

    if args.report_only or args.out is None:
        print("")
        print("仅评估模式，未写出文件。加 --out <dir> 执行预处理。")
        return 0

    os.makedirs(args.out, exist_ok=True)
    result = preprocess(img, skew, args.deskew, args.denoise, args.binarize, args.scale)

    base = os.path.splitext(os.path.basename(args.image))[0]
    out_path = os.path.join(args.out, f"{base}_pre.png")
    result.save(out_path)

    print("")
    print(f"已写出: {os.path.abspath(out_path)}")
    print(f"处理后尺寸: {result.size[0]} x {result.size[1]} px")
    print("下一步: 对处理后的图像重新执行识别。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
