"""Build a polished Chinese PDF from docs/AI_SSD_TEST_PLAN.md."""

from __future__ import annotations

import argparse
import html
import math
import re
from pathlib import Path

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    ListFlowable,
    ListItem,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


PAGE_SIZE = landscape(A4)
PAGE_W, PAGE_H = PAGE_SIZE
LEFT, RIGHT, TOP, BOTTOM = 14 * mm, 14 * mm, 15 * mm, 13 * mm
CONTENT_W = PAGE_W - LEFT - RIGHT
FENCE = chr(96) * 3

NAVY = HexColor("#0B1F33")
NAVY_2 = HexColor("#123653")
TEAL = HexColor("#00A6A6")
CYAN = HexColor("#2CC5D2")
BLUE = HexColor("#2878D0")
ORANGE = HexColor("#F59E42")
INK = HexColor("#17212B")
MUTED = HexColor("#617080")
LINE = HexColor("#D9E2EA")
PALE = HexColor("#F4F8FB")
PALE_TEAL = HexColor("#EAF8F7")
WHITE = colors.white

FONT = "DengXian"
FONT_BOLD = "DengXian-Bold"


def register_fonts() -> None:
    pairs = [
        ("C:/Windows/Fonts/Deng.ttf", "C:/Windows/Fonts/Dengb.ttf"),
        ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc"),
        ("C:/Windows/Fonts/simsun.ttc", "C:/Windows/Fonts/simhei.ttf"),
    ]
    for regular, bold in pairs:
        if Path(regular).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont(FONT, regular))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, bold))
            pdfmetrics.registerFontFamily(
                FONT, normal=FONT, bold=FONT_BOLD, italic=FONT, boldItalic=FONT_BOLD
            )
            return
    raise FileNotFoundError("No supported Chinese font found")


def clean(value: str) -> str:
    for mark in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"):
        value = value.replace(mark, "-")
    return value.replace("\u00a0", " ")


def inline(value: str) -> str:
    """Convert the small Markdown subset used by the source into ReportLab XML."""
    value = clean(value.strip())
    tokens: list[str] = []

    def stash(match: re.Match[str]) -> str:
        tokens.append(match.group(1))
        return f"@@CODE{len(tokens) - 1}@@"

    value = re.sub(r"\x60([^\x60]+)\x60", stash, value)
    value = html.escape(value, quote=False)
    value = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<font color="#2878D0"><u>\1</u></font>',
        value,
    )
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    for idx, code in enumerate(tokens):
        styled = (
            '<font color="#0B6F76" backColor="#EAF8F7">'
            f"&nbsp;{html.escape(clean(code), quote=False)}&nbsp;</font>"
        )
        value = value.replace(f"@@CODE{idx}@@", styled)
    return value


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=base["BodyText"],
        fontName=FONT,
        fontSize=8.8,
        leading=13.2,
        textColor=INK,
        spaceAfter=5,
        wordWrap="CJK",
    )
    styles = {
        "Body": body,
        "Heading1": ParagraphStyle(
            "Heading1",
            parent=base["Heading1"],
            fontName=FONT_BOLD,
            fontSize=17,
            leading=22,
            textColor=NAVY,
            spaceBefore=9,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "Heading2": ParagraphStyle(
            "Heading2",
            parent=base["Heading2"],
            fontName=FONT_BOLD,
            fontSize=12.2,
            leading=16,
            textColor=BLUE,
            spaceBefore=8,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "Heading3": ParagraphStyle(
            "Heading3",
            parent=base["Heading3"],
            fontName=FONT_BOLD,
            fontSize=10.2,
            leading=14,
            textColor=NAVY_2,
            spaceBefore=6,
            spaceAfter=4,
            keepWithNext=True,
        ),
    }
    styles["TableHeader"] = ParagraphStyle(
        "TableHeader",
        parent=body,
        fontName=FONT_BOLD,
        fontSize=7,
        leading=9,
        textColor=WHITE,
        alignment=TA_CENTER,
        spaceAfter=0,
    )
    styles["TableCell"] = ParagraphStyle(
        "TableCell", parent=body, fontSize=6.8, leading=9.1, spaceAfter=0
    )
    styles["TableSmall"] = ParagraphStyle(
        "TableSmall", parent=body, fontSize=5.8, leading=7.5, spaceAfter=0
    )
    styles["TableCaption"] = ParagraphStyle(
        "TableCaption",
        parent=body,
        fontName=FONT_BOLD,
        fontSize=8.5,
        leading=11,
        textColor=NAVY_2,
        spaceBefore=4,
        spaceAfter=4,
    )
    styles["Code"] = ParagraphStyle(
        "Code",
        parent=body,
        fontSize=7.1,
        leading=10.2,
        textColor=HexColor("#183247"),
        spaceAfter=0,
        wordWrap="CJK",
    )
    styles["ListBody"] = ParagraphStyle(
        "ListBody",
        parent=body,
        fontSize=8.3,
        leading=11.4,
        spaceAfter=0,
    )
    styles["CoverTitle"] = ParagraphStyle(
        "CoverTitle",
        parent=base["Title"],
        fontName=FONT_BOLD,
        fontSize=30,
        leading=40,
        textColor=WHITE,
        alignment=TA_LEFT,
    )
    styles["CoverSub"] = ParagraphStyle(
        "CoverSub",
        parent=body,
        fontSize=12,
        leading=18,
        textColor=HexColor("#CFEAF0"),
    )
    styles["CoverMeta"] = ParagraphStyle(
        "CoverMeta",
        parent=body,
        fontSize=8.5,
        leading=12,
        textColor=HexColor("#B8CDD9"),
    )
    styles["MetricNumber"] = ParagraphStyle(
        "MetricNumber",
        parent=body,
        fontName=FONT_BOLD,
        fontSize=22,
        leading=26,
        textColor=WHITE,
        alignment=TA_CENTER,
    )
    styles["MetricLabel"] = ParagraphStyle(
        "MetricLabel",
        parent=body,
        fontSize=8,
        leading=10,
        textColor=HexColor("#D7E9EF"),
        alignment=TA_CENTER,
    )
    styles["TOCTitle"] = ParagraphStyle(
        "TOCTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=25,
        spaceBefore=4,
        spaceAfter=12,
    )
    styles["Callout"] = ParagraphStyle(
        "Callout",
        parent=body,
        fontSize=9,
        leading=13.5,
        textColor=NAVY_2,
        leftIndent=3,
        rightIndent=3,
    )
    return styles


class ReportDoc(BaseDocTemplate):
    def __init__(self, filename: str, **kwargs):
        super().__init__(filename, **kwargs)
        frame = Frame(
            LEFT,
            BOTTOM,
            CONTENT_W,
            PAGE_H - TOP - BOTTOM,
            id="main",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates([PageTemplate(id="report", frames=[frame], onPage=draw_page)])
        self._heading_seq = 0

    def beforeDocument(self) -> None:
        self._heading_seq = 0

    def afterFlowable(self, flowable: Flowable) -> None:
        if not isinstance(flowable, Paragraph):
            return
        if flowable.style.name not in {"Heading1", "Heading2", "Heading3"}:
            return
        level = {"Heading1": 0, "Heading2": 1, "Heading3": 2}[flowable.style.name]
        title = flowable.getPlainText()
        self._heading_seq += 1
        key = f"section-{self._heading_seq}"
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(title, key, level=level, closed=False)
        self.notify("TOCEntry", (level, title, self.page, key))


def draw_page(canvas, doc) -> None:
    canvas.saveState()
    if doc.page == 1:
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
        canvas.setFillColor(NAVY_2)
        canvas.circle(PAGE_W - 42 * mm, PAGE_H - 20 * mm, 66 * mm, fill=1, stroke=0)
        canvas.setFillColor(TEAL)
        canvas.circle(PAGE_W - 18 * mm, PAGE_H - 4 * mm, 32 * mm, fill=1, stroke=0)
        canvas.setFillColor(CYAN)
        canvas.setFillAlpha(0.18)
        canvas.circle(PAGE_W - 75 * mm, 18 * mm, 46 * mm, fill=1, stroke=0)
        canvas.setFillAlpha(1)
        canvas.setStrokeColor(HexColor("#23506D"))
        canvas.setLineWidth(0.5)
        for idx in range(9):
            x = PAGE_W - 90 * mm + idx * 11 * mm
            canvas.line(x, 0, x + 40 * mm, PAGE_H)
        canvas.restoreState()
        return

    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.55)
    canvas.line(LEFT, PAGE_H - 10 * mm, PAGE_W - RIGHT, PAGE_H - 10 * mm)
    canvas.setFont(FONT_BOLD, 7.2)
    canvas.setFillColor(NAVY_2)
    canvas.drawString(LEFT, PAGE_H - 7.5 * mm, "MLPerf Storage 场景驱动的 AI SSD 测试方案")
    canvas.setFont(FONT, 6.8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(
        PAGE_W - RIGHT, PAGE_H - 7.5 * mm, "Training · Checkpointing · KV Cache · VectorDB"
    )
    canvas.line(LEFT, 8 * mm, PAGE_W - RIGHT, 8 * mm)
    canvas.drawString(LEFT, 4.8 * mm, "内部测试设计 · v1.0 · 2026-08-02")
    canvas.drawRightString(PAGE_W - RIGHT, 4.8 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


class ScenarioMap(Flowable):
    def __init__(self, width: float):
        super().__init__()
        self.width, self.height = width, 67 * mm

    def draw(self) -> None:
        c = self.canv
        c.setFillColor(PALE)
        c.roundRect(0, 0, self.width, self.height, 5, fill=1, stroke=0)
        c.setFont(FONT_BOLD, 11)
        c.setFillColor(NAVY)
        c.drawString(8 * mm, self.height - 11 * mm, "测试覆盖地图")
        cards = [
            ("Training", "16 Cases", "大文件 · 小文件 · Parquet", BLUE),
            ("Checkpoint", "9 Cases", "8B · 70B · 405B · 1T", ORANGE),
            ("KV Cache", "22 Cases", "Tier-2 · TP · Prefill/Decode", TEAL),
            ("VectorDB", "16 Cases", "HNSW · DISKANN · AISAQ", NAVY_2),
        ]
        gap = 4 * mm
        card_w = (self.width - 16 * mm - gap * 3) / 4
        y = 13 * mm
        for idx, (name, count, desc, accent) in enumerate(cards):
            x = 8 * mm + idx * (card_w + gap)
            c.setFillColor(WHITE)
            c.roundRect(x, y, card_w, 34 * mm, 4, fill=1, stroke=0)
            c.setFillColor(accent)
            c.roundRect(x, y + 29 * mm, card_w, 5 * mm, 4, fill=1, stroke=0)
            c.rect(x, y + 29 * mm, card_w, 2.5 * mm, fill=1, stroke=0)
            c.setFillColor(NAVY)
            c.setFont(FONT_BOLD, 10)
            c.drawString(x + 5 * mm, y + 22 * mm, name)
            c.setFillColor(accent)
            c.setFont(FONT_BOLD, 13)
            c.drawString(x + 5 * mm, y + 13 * mm, count)
            c.setFillColor(MUTED)
            c.setFont(FONT, 6.8)
            c.drawString(x + 5 * mm, y + 6 * mm, desc)


class ProcessFlow(Flowable):
    def __init__(self, width: float):
        super().__init__()
        self.width, self.height = width, 58 * mm

    def arrow(self, x1: float, y1: float, x2: float, y2: float) -> None:
        c = self.canv
        c.setStrokeColor(HexColor("#86A7BA"))
        c.setFillColor(HexColor("#86A7BA"))
        c.setLineWidth(1)
        c.line(x1, y1, x2, y2)
        angle, size = math.atan2(y2 - y1, x2 - x1), 3
        pts = [
            (x2, y2),
            (x2 - size * math.cos(angle - math.pi / 6), y2 - size * math.sin(angle - math.pi / 6)),
            (x2 - size * math.cos(angle + math.pi / 6), y2 - size * math.sin(angle + math.pi / 6)),
        ]
        path = c.beginPath()
        path.moveTo(*pts[0])
        path.lineTo(*pts[1])
        path.lineTo(*pts[2])
        path.close()
        c.drawPath(path, fill=1, stroke=0)

    def node(self, number: int, label: str, x: float, y: float, w: float, accent) -> None:
        c = self.canv
        c.setFillColor(PALE_TEAL if accent == TEAL else HexColor("#EDF4FB"))
        if accent == ORANGE:
            c.setFillColor(HexColor("#FFF5E8"))
        c.roundRect(x, y, w, 15 * mm, 4, fill=1, stroke=0)
        c.setFillColor(accent)
        c.circle(x + 6 * mm, y + 7.5 * mm, 3.2 * mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 6.8)
        c.drawCentredString(x + 6 * mm, y + 7.5 * mm - 2.3, str(number))
        c.setFillColor(NAVY)
        c.setFont(FONT_BOLD, 7.1)
        c.drawString(x + 11 * mm, y + 7.5 * mm - 2.5, label)

    def draw(self) -> None:
        labels = [
            "选择 Case 与 DUT",
            "数据量/容量检查",
            "数据生成/预处理",
            "运行前快照",
            "预热确认",
            "3 次正式运行",
            "应用结果验证",
            "SSD/主机监控验证",
            "SLA/回归判定",
            "归档产物",
        ]
        gap = 4 * mm
        w = (self.width - gap * 4) / 5
        top, bottom = 36 * mm, 8 * mm
        for idx in range(5):
            x = idx * (w + gap)
            if idx:
                self.arrow(x - gap + 1 * mm, top + 7.5 * mm, x - 1 * mm, top + 7.5 * mm)
            self.node(idx + 1, labels[idx], x, top, w, TEAL if idx < 3 else BLUE)
        self.arrow(self.width - w / 2, top, self.width - w / 2, bottom + 15 * mm)
        for pos in range(5):
            idx = 5 + pos
            x = (4 - pos) * (w + gap)
            if pos:
                self.arrow(x + w + gap - 1 * mm, bottom + 7.5 * mm, x + w + 1 * mm, bottom + 7.5 * mm)
            self.node(idx + 1, labels[idx], x, bottom, w, ORANGE if idx >= 8 else BLUE)


def cover(styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    numbers = []
    labels = []
    for number, label in [
        ("18", "可追踪测试需求"),
        ("72", "工作负载测试 Case"),
        ("4+1", "AI 场景族 + 混合负载"),
        ("1 s", "Windows 设备监控"),
    ]:
        numbers.append(Paragraph(number, styles["MetricNumber"]))
        labels.append(Paragraph(label, styles["MetricLabel"]))
    metrics = Table(
        [numbers, labels],
        colWidths=[42 * mm] * 4,
        rowHeights=[25 * mm, 10 * mm],
        hAlign="LEFT",
    )
    metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#143B56")),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#39647C")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#39647C")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return [
        Spacer(1, 32 * mm),
        Paragraph("MLPerf Storage 场景驱动的<br/>AI SSD 测试方案", styles["CoverTitle"]),
        Spacer(1, 6 * mm),
        Paragraph("Training · Checkpointing · KV Cache Offloading · VectorDB", styles["CoverSub"]),
        Spacer(1, 22 * mm),
        metrics,
        Spacer(1, 27 * mm),
        Paragraph(
            "版本 1.0　|　2026-08-02　|　Windows 单盘资格、规模化验证与混合负载设计",
            styles["CoverMeta"],
        ),
        Spacer(1, 3 * mm),
        Paragraph(
            "核心原则：业务指标与物理 I/O 双重验证，Pass / Fail / Invalid 三态判定",
            styles["CoverMeta"],
        ),
        PageBreak(),
    ]


def toc(styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    contents = TableOfContents()
    contents.levelStyles = [
        ParagraphStyle(
            "TOCLevel1", fontName=FONT_BOLD, fontSize=9.4, leading=14, textColor=NAVY, spaceBefore=3
        ),
        ParagraphStyle(
            "TOCLevel2", fontName=FONT, fontSize=8, leading=11, leftIndent=7 * mm, textColor=MUTED
        ),
        ParagraphStyle(
            "TOCLevel3", fontName=FONT, fontSize=7.3, leading=10, leftIndent=14 * mm, textColor=MUTED
        ),
    ]
    note = Table(
        [[Paragraph(
            "<b>阅读说明</b><br/>本报告以 AI 工作负载为中心。协议、PLP、Sanitize 和固件测试仅作为可选健康门禁，不进入 72 个核心 Case。",
            styles["Callout"],
        )]],
        colWidths=[CONTENT_W],
    )
    note.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE_TEAL),
                ("BOX", (0, 0), (-1, -1), 0.7, HexColor("#A9D9D5")),
                ("LINEBEFORE", (0, 0), (0, -1), 4, TEAL),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return [
        Paragraph("目录", styles["TOCTitle"]),
        note,
        Spacer(1, 6 * mm),
        contents,
        PageBreak(),
        ScenarioMap(CONTENT_W),
        Spacer(1, 7 * mm),
    ]


def closing_panel(styles: dict[str, ParagraphStyle]) -> Flowable:
    title = Paragraph(
        '<font color="#FFFFFF"><b>完成判定</b>　测试结果只有同时满足以下三类证据，才可进入产品结论。</font>',
        styles["Callout"],
    )
    cards = [
        Paragraph(
            '<b><font color="#2878D0">正确性</font></b><br/>无数据错误、无缺 rank/trial、Recall 与 AU 达到门槛',
            styles["Callout"],
        ),
        Paragraph(
            '<b><font color="#00A6A6">性能</font></b><br/>吞吐、tokens/s、QPS 与尾延迟满足已批准 SLA',
            styles["Callout"],
        ),
        Paragraph(
            '<b><font color="#F59E42">可追溯性</font></b><br/>DUT 命中、配置、监控、原始产物和 verdict 完整',
            styles["Callout"],
        ),
    ]
    panel = Table(
        [[title, "", ""], cards],
        colWidths=[CONTENT_W / 3] * 3,
        rowHeights=[17 * mm, 31 * mm],
    )
    panel.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0), NAVY_2),
                ("BACKGROUND", (0, 1), (-1, 1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 1), (-1, 1), 0.6, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return panel


def visual_len(value: str) -> float:
    plain = re.sub(r"<[^>]+>", "", value)
    return sum(1.9 if ord(char) > 255 else 1.0 for char in plain)


def widths(headers: list[str], rows: list[list[str]]) -> list[float]:
    scores: list[float] = []
    for idx, header in enumerate(headers):
        longest = visual_len(header)
        for row in rows[:40]:
            if idx < len(row):
                longest = max(longest, min(visual_len(row[idx]), 46))
        scores.append(max(5.0, math.sqrt(longest) * 2.6))
    for idx, header in enumerate(headers):
        key = clean(header).lower()
        if "case" in key or "tr id" in key:
            scores[idx] = max(scores[idx], 12)
        if "priority" in key or "频率" in key or key in {"状态", "profile"}:
            scores[idx] = min(scores[idx], 7)
        if "requirement" in key or "目的" in key or "判定" in key:
            scores[idx] *= 1.13
    total = sum(scores)
    return [CONTENT_W * score / total for score in scores]


def table_parts(
    headers: list[str],
    rows: list[list[str]],
    styles: dict[str, ParagraphStyle],
    caption: str | None = None,
) -> list[Flowable]:
    count = len(headers)
    cell_style = styles["TableSmall"] if count >= 7 else styles["TableCell"]
    data = [[Paragraph(inline(cell), styles["TableHeader"]) for cell in headers]]
    for row in rows:
        row = (row + [""] * count)[:count]
        data.append([Paragraph(inline(cell), cell_style) for cell in row])
    table = LongTable(data, colWidths=widths(headers, rows), repeatRows=1, hAlign="LEFT", splitByRow=1)
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY_2),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.2),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 3.5),
    ]
    for row_idx in range(1, len(data)):
        if row_idx % 2 == 0:
            commands.append(("BACKGROUND", (0, row_idx), (-1, row_idx), PALE))
    if headers and (headers[0].lower().startswith("case") or headers[0].lower().startswith("tr id")):
        commands.extend(
            [
                ("FONTNAME", (0, 1), (0, -1), FONT_BOLD),
                ("TEXTCOLOR", (0, 1), (0, -1), NAVY_2),
                ("BACKGROUND", (0, 1), (0, -1), HexColor("#EDF4F8")),
            ]
        )
    table.setStyle(TableStyle(commands))
    output: list[Flowable] = []
    if caption:
        output.append(Paragraph(caption, styles["TableCaption"]))
    output.extend([table, Spacer(1, 4 * mm)])
    return output


def requirement_parts(
    headers: list[str], rows: list[list[str]], styles: dict[str, ParagraphStyle]
) -> list[Flowable]:
    groups = [
        ([0, 1, 2, 3, 9, 10], "表 4A　需求定义、目标与优先级"),
        ([0, 4, 5, 6, 7, 8], "表 4B　前置条件、刺激、观测与判定"),
    ]
    output: list[Flowable] = []
    for indices, caption in groups:
        sub_headers = [headers[idx] for idx in indices]
        sub_rows = [[row[idx] if idx < len(row) else "" for idx in indices] for row in rows]
        output.extend(table_parts(sub_headers, sub_rows, styles, caption))
    return output


def code_box(lines: list[str], styles: dict[str, ParagraphStyle]) -> Flowable:
    formatted = []
    for line in lines:
        line = clean(line).replace("\t", "    ")
        leading = len(line) - len(line.lstrip(" "))
        formatted.append("&nbsp;" * leading + (html.escape(line.lstrip(" "), quote=False) or "&nbsp;"))
    paragraph = Paragraph("<br/>".join(formatted), styles["Code"])
    box = Table([[paragraph]], colWidths=[CONTENT_W])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F0F5F8")),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("LINEBEFORE", (0, 0), (0, -1), 3.5, BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return box


def parse_table(lines: list[str], start: int) -> tuple[list[str], list[list[str]], int]:
    block, idx = [], start
    while idx < len(lines) and lines[idx].strip().startswith("|"):
        block.append(lines[idx].strip())
        idx += 1

    def split(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    headers = split(block[0])
    data_start = 2 if len(block) > 1 and all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in split(block[1])
    ) else 1
    return headers, [split(line) for line in block[data_start:]], idx


def parse_markdown(source: str, styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    lines = source.splitlines()
    story: list[Flowable] = []
    idx, paragraph, skipped_title = 0, [], False

    def flush() -> None:
        nonlocal paragraph
        if paragraph:
            story.append(Paragraph(inline(" ".join(part.strip() for part in paragraph)), styles["Body"]))
            paragraph = []

    while idx < len(lines):
        stripped = lines[idx].strip()
        if not stripped:
            flush()
            idx += 1
            continue
        if stripped.startswith("# "):
            flush()
            skipped_title = True
            idx += 1
            continue
        if skipped_title and re.match(r"^\*\*(版本|日期|定位|核心输出)\*\*", stripped):
            idx += 1
            continue
        heading = re.match(r"^(#{2,4})\s+(.+)$", stripped)
        if heading:
            flush()
            level = len(heading.group(1)) - 1
            if heading.group(2).startswith("13. Definition of Done"):
                story.append(PageBreak())
            story.append(Paragraph(inline(heading.group(2)), styles[f"Heading{level}"]))
            idx += 1
            continue
        if stripped.startswith(FENCE):
            flush()
            language = stripped[3:].strip().lower()
            idx += 1
            block = []
            while idx < len(lines) and not lines[idx].strip().startswith(FENCE):
                block.append(lines[idx])
                idx += 1
            idx += 1
            if language == "mermaid":
                story.extend([ProcessFlow(CONTENT_W), Spacer(1, 3 * mm)])
            else:
                story.extend([code_box(block, styles), Spacer(1, 4 * mm)])
            continue
        if stripped.startswith("|"):
            flush()
            headers, rows, idx = parse_table(lines, idx)
            if headers and headers[0] == "TR ID" and len(headers) == 11:
                story.extend(requirement_parts(headers, rows, styles))
            else:
                story.extend(table_parts(headers, rows, styles))
            continue
        list_match = re.match(r"^(-|\d+\.)\s+(.+)$", stripped)
        if list_match:
            flush()
            ordered = list_match.group(1) != "-"
            items = []
            while idx < len(lines):
                match = re.match(r"^(-|\d+\.)\s+(.+)$", lines[idx].strip())
                if not match or ((match.group(1) != "-") != ordered):
                    break
                item_value = int(match.group(1)[:-1]) if ordered else None
                items.append(
                    ListItem(
                        Paragraph(inline(match.group(2)), styles["ListBody"]),
                        leftIndent=4 * mm,
                        bottomPadding=1,
                        value=item_value,
                    )
                )
                idx += 1
            list_args = {
                "bulletType": "1" if ordered else "bullet",
                "leftIndent": 7 * mm,
                "bulletFontName": FONT_BOLD,
                "bulletFontSize": 7.5,
                "bulletColor": TEAL,
                "spaceAfter": 4,
            }
            if ordered:
                list_args["start"] = int(list_match.group(1)[:-1])
            story.append(
                ListFlowable(items, **list_args)
            )
            continue
        if stripped.startswith(">"):
            flush()
            quote = stripped.lstrip(">").strip()
            box = Table([[Paragraph(inline(quote), styles["Callout"])]], colWidths=[CONTENT_W])
            box.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), PALE_TEAL),
                        ("LINEBEFORE", (0, 0), (0, -1), 4, TEAL),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.extend([box, Spacer(1, 3 * mm)])
            idx += 1
            continue
        paragraph.append(stripped)
        idx += 1
    flush()
    return story


def build(source: Path, output: Path) -> None:
    register_fonts()
    rl_config.warnOnMissingFontGlyphs = 1
    styles = make_styles()
    story: list[Flowable] = []
    story.extend(cover(styles))
    story.extend(toc(styles))
    story.extend(parse_markdown(source.read_text(encoding="utf-8"), styles))
    story.extend([Spacer(1, 10 * mm), closing_panel(styles)])
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = ReportDoc(
        str(output),
        pagesize=PAGE_SIZE,
        leftMargin=LEFT,
        rightMargin=RIGHT,
        topMargin=TOP,
        bottomMargin=BOTTOM,
        title="MLPerf Storage 场景驱动的 AI SSD 测试方案",
        author="AI SSD Test Engineering",
        subject="Training, Checkpointing, KV Cache Offloading and VectorDB test matrix",
        creator="Codex / ReportLab",
    )
    doc.multiBuild(story)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.source.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
