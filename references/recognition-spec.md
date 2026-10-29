# 识别规范

## 1. 公式：LaTeX 与 MathML 双表示

每个公式必须同时产出两段内容：

1. **LaTeX 源** — 写入 Markdown 与 `question.json` 的 `latex` 字段，供二次编辑。
2. **MathML 串** — 供 HTML 原生渲染，无需任何外部库。

HTML 中的最终形态固定为：

```html
<math display="inline"><semantics>
  <mrow>…</mrow>
  <annotation encoding="application/x-tex">LaTeX 源</annotation>
</semantics></math>
```

行内公式用 `display="inline"`，独立成行的公式用 `display="block"`。

### 常用结构映射

| 语义 | LaTeX | MathML |
|---|---|---|
| 分数 | `\frac{a}{b}` | `<mfrac><mi>a</mi><mi>b</mi></mfrac>` |
| 平方根 | `\sqrt{x}` | `<msqrt><mi>x</mi></msqrt>` |
| n 次根 | `\sqrt[n]{x}` | `<mroot><mi>x</mi><mi>n</mi></mroot>` |
| 下标 | `x_i` | `<msub><mi>x</mi><mi>i</mi></msub>` |
| 上标 | `x^2` | `<msup><mi>x</mi><mn>2</mn></msup>` |
| 上下标 | `x_i^2` | `<msubsup><mi>x</mi><mi>i</mi><mn>2</mn></msubsup>` |
| 求和 | `\sum_{i=1}^{n}` | `<munderover><mo>∑</mo>…</munderover>` |
| 极限 | `\lim_{x\to 0}` | `<munder><mo>lim</mo>…</munder>` |
| 矩阵 | `\begin{matrix}…\end{matrix}` | `<mtable><mtr><mtd>…</mtd></mtr></mtable>` |
| 括号 | `\left(…\right)` | `<mo>(</mo><mrow>…</mrow><mo>)</mo>` |

元素类型约定：变量用 `<mi>`，数字用 `<mn>`，运算符与括号用 `<mo>`，文字说明用 `<mtext>`。

## 2. 符号对照表

### 希腊字母

- 小写：α β γ δ ε ζ η θ ι κ λ μ ν ξ π ρ σ τ υ φ χ ψ ω
- 大写：Γ Δ Θ Λ Ξ Π Σ Φ Ψ Ω

MathML 中直接把字符放入 `<mi>`，例如 `<mi>α</mi>`。单位与缩写须加 `mathvariant="normal"` 以保持正体，例如 `<mi mathvariant="normal">m</mi>`。

### 单位

| 含义 | LaTeX | MathML 要点 |
|---|---|---|
| 米每秒 | `\mathrm{m/s}` | `<mfrac>` 包裹两个正体 `<mi>` |
| 千克 | `\mathrm{kg}` | 正体 `<mi>` |
| 摄氏度 | `\mathrm{^\circ C}` | `<msup>` 加 `<mo>∘</mo>` |
| 摩尔每升 | `\mathrm{mol/L}` | 正体组合 |

### 化学式

- 水：LaTeX `\mathrm{H_2O}`；MathML `<msub><mi mathvariant="normal">H</mi><mn>2</mn></msub><mi mathvariant="normal">O</mi>`
- 离子电荷：Ca²⁺ 用 `<msup><mi mathvariant="normal">Ca</mi><mrow><mn>2</mn><mo>+</mo></mrow></msup>`
- 箭头：`→` 用 `<mo>→</mo>`；可逆 `⇌` 用 `<mo>⇌</mo>`；气体逸出 `↑`；沉淀 `↓`
- 反应条件写在箭头上下，用 `<munder>` 或 `<mover>` 包裹箭头

### 其他高频符号

`≤ ≥ ≠ ≈ ± × ÷ ∠ ⊥ ∥ ∵ ∴ ∈ ⊂ ∪ ∩ → ⇒ ⇔ ∞ ∂ ∇`

## 3. 表格还原

- 保留原始行列数、表头与对齐方式。
- Markdown 输出为标准管道表格；HTML 输出为 `<table>`，表头用 `<thead>`。
- 单元格内的公式同样走 MathML 渲染。
- 合并单元格用 `colspan` / `rowspan` 表达，并在待确认清单注明「合并关系由版式推断」。

## 4. 图形重建

优先顺序固定为：**内联 SVG 矢量重建 > 原图切片保留**。

### 几何图

用 SVG 的 `<line>`、`<circle>`、`<path>`、`<polygon>` 绘制；顶点用字母标注（`<text>`）；直角标记用小方块；等长标记用短横线。

### 函数图像

绘制带箭头的坐标轴、刻度与刻度标签；用 `<path>` 描出曲线；渐近线用 `stroke-dasharray` 画虚线；关键点标注坐标。

### 电路图

使用标准符号：电阻为矩形、电源为长短线组、开关为折线、导线为直线、电表为圆圈内加字母；导线交叉相连处画实心点。

### 无法矢量化的部分

- 把该区域从原图裁切保存为 `figures/<id>.png`。
- 在 `question.json` 中以 `image` 字段引用，并在 `position` 说明其位于题干哪一段之后。
- 在待确认清单列出，注明「该图未能矢量化，保留原图切片」。

## 5. 置信度标注

| 级别 | 含义 | 处理方式 |
|---|---|---|
| 高 | 字符与结构清晰无疑义 | 直接采用 |
| 中 | 大体可辨，个别细节存疑 | 采用，并在备注说明存疑点 |
| 低 | 部分字符模糊或版式歧义 | 采用推断值，用 `⟦?…?⟧` 包裹该片段并列入待确认清单 |
| 不可识别 | 完全无法辨认 | 留 `⟦?⟧` 占位（不含内容），列入待确认清单，绝不猜测 |

标记约定：`⟦?…?⟧` 表示「包裹的内容存疑」，`⟦?⟧` 表示「此处完全无法辨认」。两者在 HTML 中均渲染为醒目高亮，在 Markdown 中保留原样。

## 6. question.json 结构定义

```json
{
  "title": "试题还原卡",
  "source": "原卷文件名或来源说明",
  "mathml": {
    "x^2+1": "<math display=\"inline\"><semantics><mrow>…</mrow><annotation encoding=\"application/x-tex\">x^2+1</annotation></semantics></math>"
  },
  "questions": [
    {
      "number": "12",
      "type": "单选题",
      "score": "4 分",
      "stem": ["已知 $x^2+1=0$，求 $x$ 的值。"],
      "options": ["A. $1$", "B. $-1$", "C. $0$", "D. 无实数解"],
      "tables": [],
      "figures": [
        { "id": "fig1", "caption": "图 1", "position": "题干之后", "svg": "<svg …>…</svg>" }
      ],
      "answer": "D",
      "solution": "由 $x^2=-1$ 可知实数范围内无解。",
      "uncertain": ["选项 C 的下标疑似 0，待确认"]
    }
  ],
  "pending": ["第 12 题题干第 2 行的 α 系数辨认不清"]
}
```

字段说明：

- `stem` 为段落数组，每个元素是一段文字；行内公式以 `$…$` 包裹，独立公式以 `$$…$$` 包裹。
- `mathml` 是 LaTeX 串到 MathML 串的映射表，`build_card.py` 据此把 `$…$` 替换为可渲染的 MathML。
- `figures[].svg` 与 `figures[].image` 二选一；`image` 为相对 `question.json` 的图片路径。
- `uncertain` 与 `pending` 中的条目渲染为页脚待确认清单。
