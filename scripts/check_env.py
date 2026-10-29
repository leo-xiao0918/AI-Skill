#!/usr/bin/env python3
"""Probe the local environment for exam-question-restore dependencies.

Prints a capability matrix so the agent knows which preprocessing and
extraction steps are actually available on this machine.
"""
from __future__ import annotations

import importlib
import shutil
import sys

MODULES = [
    ("PIL", "Pillow", "图像缩放 / 去噪 / 格式转换", True),
    ("pymupdf", "PyMuPDF", "PDF 分页渲染与文本抽取", True),
    ("numpy", "NumPy", "像素运算、倾斜角估计", True),
    ("cv2", "OpenCV", "透视矫正、自适应去噪（可选增强）", False),
]


def probe_module(name: str):
    try:
        mod = importlib.import_module(name)
        return getattr(mod, "__version__", "已安装")
    except Exception:
        return None


def main() -> int:
    print(f"Python: {sys.version.split()[0]}")
    print("")
    print(f"{'依赖':<10}{'状态':<12}{'版本':<14}用途")
    print("-" * 72)

    missing_required = []
    for name, label, purpose, required in MODULES:
        ver = probe_module(name)
        if ver:
            status = "可用"
            print(f"{label:<10}{status:<12}{str(ver):<14}{purpose}")
        else:
            status = "缺失(必需)" if required else "缺失(可选)"
            print(f"{label:<10}{status:<12}{'—':<14}{purpose}")
            if required:
                missing_required.append(name)

    print("")
    tesseract = shutil.which("tesseract")
    if tesseract:
        print(f"Tesseract OCR: 可用 -> {tesseract}")
    else:
        print("Tesseract OCR: 未安装（文本兜底不可用；可改用 ocr-local 技能或纯多模态识别）")

    print("")
    print("能力判定:")
    if not missing_required:
        print("  - 图像预处理: 可用")
        print("  - PDF 抽取:   可用")
    else:
        for name in missing_required:
            pip_name = {"PIL": "Pillow", "pymupdf": "PyMuPDF", "numpy": "numpy"}[name]
            print(f"  - 缺少 {pip_name}，对应能力不可用。安装: pip install {pip_name}")
    print("  - 多模态视觉识别: 由宿主提供，是本技能的主力识别能力")
    print("  - 公式渲染: 浏览器原生 MathML Core，无需外部 JS/CSS")

    print("")
    if missing_required:
        print("结论：存在缺失的必需依赖，相关步骤将降级或不可用。")
        return 1
    print("结论：必需依赖齐备，可完整执行还原流程。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
