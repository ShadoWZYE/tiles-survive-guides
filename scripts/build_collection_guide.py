from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / "docs"
OUTPUT.mkdir(parents=True, exist_ok=True)

NAVY = colors.HexColor("#102A4A")
BLUE = colors.HexColor("#214B78")
PALE_BLUE = colors.HexColor("#EAF3FA")
CYAN = colors.HexColor("#18C9C5")
ORANGE = colors.HexColor("#F4A340")
PALE_ORANGE = colors.HexColor("#FFF3DF")
INK = colors.HexColor("#17283D")
MUTED = colors.HexColor("#58708A")
LINE = colors.HexColor("#C8D7E6")
WHITE = colors.white


def first_existing(*paths: str) -> str:
    for candidate in paths:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError("Install Arial, Segoe UI, or DejaVu Sans to build the guide.")


pdfmetrics.registerFont(TTFont("GuideSans", first_existing(
    r"C:\Windows\Fonts\arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)))
pdfmetrics.registerFont(TTFont("GuideSans-Bold", first_existing(
    r"C:\Windows\Fonts\arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)))


class GuideDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str, locale: str):
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=17 * mm,
            rightMargin=17 * mm,
            topMargin=24 * mm,
            bottomMargin=18 * mm,
            title="Tiles Survive Collections Guide",
            author="Codex",
        )
        self.locale = locale
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(PageTemplate(id="guide", frames=[frame], onPage=self.draw_page))

    def draw_page(self, canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(NAVY)
        canvas.rect(0, height - 15 * mm, width, 15 * mm, stroke=0, fill=1)
        canvas.setFillColor(CYAN)
        canvas.rect(0, height - 15.8 * mm, width, 0.8 * mm, stroke=0, fill=1)
        canvas.setFont("GuideSans-Bold", 9)
        canvas.setFillColor(WHITE)
        canvas.drawString(17 * mm, height - 9.5 * mm, "TILES SURVIVE")
        canvas.setFont("GuideSans", 8)
        canvas.setFillColor(MUTED)
        if self.locale == "en":
            footer = "Client-data guide - build 2.6.100.261"
        elif self.locale == "ru":
            footer = "Гайд по данным клиента - сборка 2.6.100.261"
        else:
            footer = "Bilingual client-data guide - EN / RU - build 2.6.100.261"
        canvas.drawString(17 * mm, 9 * mm, footer)
        canvas.drawRightString(width - 17 * mm, 9 * mm, str(doc.page))
        canvas.restoreState()


def styles():
    sample = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=sample["Title"],
            fontName="GuideSans-Bold",
            fontSize=22,
            leading=25,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=4 * mm,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            fontName="GuideSans",
            fontSize=10,
            leading=14,
            textColor=MUTED,
            spaceAfter=5 * mm,
        ),
        "h2": ParagraphStyle(
            "H2",
            fontName="GuideSans-Bold",
            fontSize=14,
            leading=17,
            textColor=NAVY,
            spaceBefore=3 * mm,
            spaceAfter=2.5 * mm,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName="GuideSans",
            fontSize=9.3,
            leading=13.2,
            textColor=INK,
            spaceAfter=2.2 * mm,
        ),
        "small": ParagraphStyle(
            "Small",
            fontName="GuideSans",
            fontSize=7.6,
            leading=10.2,
            textColor=MUTED,
        ),
        "callout": ParagraphStyle(
            "Callout",
            fontName="GuideSans-Bold",
            fontSize=11,
            leading=15,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
        "cell": ParagraphStyle(
            "Cell",
            fontName="GuideSans",
            fontSize=8.3,
            leading=10.5,
            textColor=INK,
        ),
        "cell_bold": ParagraphStyle(
            "CellBold",
            fontName="GuideSans-Bold",
            fontSize=8.3,
            leading=10.5,
            textColor=INK,
        ),
        "head": ParagraphStyle(
            "Head",
            fontName="GuideSans-Bold",
            fontSize=8.2,
            leading=10,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
    }


def P(text: str, style):
    return Paragraph(text, style)


def callout(text: str, st):
    box = Table([[P(text, st["callout"])]], colWidths=[176 * mm])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE_ORANGE),
                ("BOX", (0, 0), (-1, -1), 1, ORANGE),
                ("LEFTPADDING", (0, 0), (-1, -1), 6 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
            ]
        )
    )
    return box


def data_table(headers, rows, widths, st, alignments=None):
    data = [[P(value, st["head"]) for value in headers]]
    for row in rows:
        data.append([P(str(value), st["cell_bold"] if i == 0 else st["cell"]) for i, value in enumerate(row)])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE_BLUE]),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.6 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.6 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
    ]
    if alignments:
        for col, alignment in enumerate(alignments):
            commands.append(("ALIGN", (col, 1), (col, -1), alignment))
    table.setStyle(TableStyle(commands))
    return table


def bullet_lines(lines, st):
    return [P(f"<font color='#18A6A2'>•</font> {line}", st["body"]) for line in lines]


def english_story():
    st = styles()
    story = [
        P("Collections: How to Obtain Better Items", st["title"]),
        P("Verified against the installed Tiles Survive Windows client. This guide covers Chief Profile Collections, not Hero Gear or Signature Gear.", st["subtitle"]),
        callout("Higher-quality Collection items are not separate random drops. Your six Common pieces evolve into better versions through Enhance.", st),
        Spacer(1, 4 * mm),
        P("Quality progression", st["h2"]),
        data_table(
            ["Quality", "Displayed levels", "Knife example"],
            [
                ("Common", "1-10", "Rusty Knife"),
                ("Uncommon", "11-25", "Sharp Knife"),
                ("Rare", "26-40", "Utility Survival Knife"),
                ("Epic", "41-60", "Elite Tactical Knife"),
                ("Legendary", "61-90", "Butcher's Blade"),
            ],
            [43 * mm, 42 * mm, 91 * mm],
            st,
            ["LEFT", "CENTER", "LEFT"],
        ),
        Spacer(1, 4 * mm),
        P("How progression works", st["h2"]),
        *bullet_lines(
            [
                "Obtain the six starting pieces through Collection-type missions at the Intel Post.",
                "Open Chief Profile - Collection, select a piece, and choose Enhance.",
                "Common levels 1-10 use General Parts only.",
                "From Uncommon onward, enhancement uses General Parts and Precision Blueprints.",
                "After level 10, each displayed level is split into five enhancement stages.",
            ],
            st,
        ),
        Spacer(1, 3 * mm),
        P("When the Enhance button appears", st["h2"]),
        data_table(
            ["Feature", "Client requirement"],
            [
                ("Collection cabinet", "Complete the Collection task chain at the Intel Post; Power Plant Lv. 12"),
                ("Enhance button", "Power Plant Lv. 16 AND State/server-open day 22"),
            ],
            [48 * mm, 128 * mm],
            st,
        ),
        Spacer(1, 2 * mm),
        P("For a State opened on 2 Sep 2026, day 22 is 23 Sep if opening day is counted as day 1. The button should appear after the day-22 server reset once Power Plant 16 is met; if the backend counts 22 completed days, allow until the 24 Sep reset.", st["small"]),
        Spacer(1, 2 * mm),
        P("First practical target", st["h2"]),
        data_table(
            ["Goal", "Per piece", "All six pieces"],
            [("Common 1 to Uncommon 11", "550 General Parts", "3,300 General Parts")],
            [70 * mm, 53 * mm, 53 * mm],
            st,
            ["LEFT", "CENTER", "CENTER"],
        ),
        PageBreak(),
        P("Where the materials come from", st["title"]),
        P("The client lists the following acquisition routes. An event or store may remain unavailable until your State reaches its server-age unlock.", st["subtitle"]),
        data_table(
            ["Material", "Configured sources"],
            [
                ("General Parts", "Hunting Field; Reservoir Raid; Arcadian Conquest; Infected Fiends"),
                ("Precision Blueprints", "Arcadian Conquest; Reservoir Store; Goldmine Store"),
            ],
            [48 * mm, 128 * mm],
            st,
        ),
        Spacer(1, 4 * mm),
        P("How to farm General Parts", st["h2"]),
        *bullet_lines(
            [
                "Tap the General Parts icon and choose Get More. The game will show only the sources currently open on your State.",
                "Hunting Field: participate while the alliance event is open and claim the personal/alliance reward tiers that contain General Parts.",
                "Reservoir Raid: participate in the match and collect its event rewards. Precision Blueprints are separately listed in the Reservoir Store.",
                "Arcadian Conquest: collect eligible event, milestone, ranking, or shop rewards when this cross-State feature opens.",
                "Infected Fiends: attack or rally the event targets and claim the associated rewards containing General Parts.",
                "The introductory Collection Intel missions can provide the starting unlock/tutorial rewards, but the four event routes above are the client's listed repeatable sources.",
            ],
            st,
        ),
        Spacer(1, 5 * mm),
        P("Why even upgrading is usually best", st["h2"]),
        P("Collections have a whole-set bonus. The next bonus activates only after every one of the six pieces reaches the required quality breakpoint.", st["body"]),
        data_table(
            ["All six pieces at", "Troop All Stats"],
            [
                ("Common", "+3%"),
                ("Uncommon", "+6%"),
                ("Rare", "+9%"),
                ("Epic", "+12%"),
                ("Legendary", "+15%"),
            ],
            [105 * mm, 71 * mm],
            st,
            ["LEFT", "CENTER"],
        ),
        Spacer(1, 5 * mm),
        callout("Recommended early plan: raise the lowest piece first until all six reach level 11. Do not wait for a Rare knife to drop - the Rusty Knife becomes the better version through enhancement.", st),
        Spacer(1, 3 * mm),
        P("A single advanced piece improves its own stats but does not advance the whole-set breakpoint. Verified in client build 2.6.100.261: function-open, Collection equipment, suit, and acquisition-route configuration tables.", st["small"]),
    ]
    return story


def russian_story():
    st = styles()
    story = [
        P("Коллекции: как получить предметы лучшего качества", st["title"]),
        P("Проверено по установленному Windows-клиенту Tiles Survive. Здесь рассматриваются Коллекции в профиле вождя, а не снаряжение героев или именное оружие.", st["subtitle"]),
        callout("Предметы более высокого качества не выпадают отдельно. Шесть обычных предметов превращаются в лучшие версии через улучшение.", st),
        Spacer(1, 4 * mm),
        P("Качество и уровни", st["h2"]),
        data_table(
            ["Качество", "Показываемые уровни", "Пример ножа"],
            [
                ("Обычное", "1-10", "Ржавый нож"),
                ("Необычное", "11-25", "Острый нож"),
                ("Редкое", "26-40", "Универсальный нож выживания"),
                ("Эпическое", "41-60", "Элитный тактический нож"),
                ("Легендарное", "61-90", "Клинок мясника"),
            ],
            [43 * mm, 50 * mm, 83 * mm],
            st,
            ["LEFT", "CENTER", "LEFT"],
        ),
        Spacer(1, 4 * mm),
        P("Как работает развитие", st["h2"]),
        *bullet_lines(
            [
                "Получите шесть начальных предметов в заданиях Коллекции на Посту разведки.",
                "Откройте Профиль вождя - Коллекция, выберите предмет и нажмите Улучшить.",
                "Для обычных уровней 1-10 нужны только Общие детали (General Parts).",
                "Начиная с необычного качества нужны Общие детали и Точные чертежи (Precision Blueprints).",
                "После 10-го уровня каждый отображаемый уровень разделён на пять этапов улучшения.",
            ],
            st,
        ),
        Spacer(1, 3 * mm),
        P("Когда появляется кнопка улучшения", st["h2"]),
        data_table(
            ["Функция", "Требование клиента"],
            [
                ("Раздел Коллекции", "Завершить цепочку заданий Коллекции на Посту разведки; Электростанция ур. 12"),
                ("Кнопка Улучшить", "Электростанция ур. 16 И 22-й день государства/сервера"),
            ],
            [48 * mm, 128 * mm],
            st,
        ),
        Spacer(1, 2 * mm),
        P("Если государство открылось 2 сентября 2026 г., 22-й день приходится на 23 сентября при учёте дня открытия как первого. Кнопка должна появиться после сброса 22-го дня при Электростанции 16; если сервер считает 22 полных суток, подождите до сброса 24 сентября.", st["small"]),
        Spacer(1, 2 * mm),
        P("Первая практическая цель", st["h2"]),
        data_table(
            ["Цель", "На один предмет", "На все шесть"],
            [("Обычный 1 - Необычный 11", "550 Общих деталей", "3 300 Общих деталей")],
            [70 * mm, 53 * mm, 53 * mm],
            st,
            ["LEFT", "CENTER", "CENTER"],
        ),
        PageBreak(),
        P("Где получать материалы", st["title"]),
        P("Клиент указывает следующие источники. Событие или магазин могут быть недоступны, пока государство не достигнет необходимого возраста.", st["subtitle"]),
        data_table(
            ["Материал", "Источники в клиенте"],
            [
                ("Общие детали", "Hunting Field; Reservoir Raid; Arcadian Conquest; Infected Fiends"),
                ("Точные чертежи", "Arcadian Conquest; Reservoir Store; Goldmine Store"),
            ],
            [48 * mm, 128 * mm],
            st,
        ),
        Spacer(1, 2 * mm),
        P("Названия источников оставлены на английском, чтобы их было легче найти в интерфейсе при разных языковых настройках.", st["small"]),
        Spacer(1, 4 * mm),
        P("Как добывать Общие детали", st["h2"]),
        *bullet_lines(
            [
                "Нажмите на значок Общих деталей и выберите Получить / Get More. Игра покажет только те источники, которые уже открыты в вашем государстве.",
                "Hunting Field: участвуйте в событии альянса и забирайте личные и общие награды, в которых указаны Общие детали.",
                "Reservoir Raid: участвуйте в матче и забирайте награды события. Точные чертежи отдельно указаны в Reservoir Store.",
                "Arcadian Conquest: после открытия режима забирайте доступные награды события, этапов, рейтинга или магазина.",
                "Infected Fiends: атакуйте цели события или собирайте ралли и забирайте награды с Общими деталями.",
                "Вводные задания Коллекции на Посту разведки дают стартовые предметы и обучающие награды, но четыре события выше являются повторяемыми источниками, указанными клиентом.",
            ],
            st,
        ),
        Spacer(1, 4 * mm),
        P("Почему лучше улучшать комплект равномерно", st["h2"]),
        P("У Коллекции есть бонус полного комплекта. Следующая ступень включается только тогда, когда все шесть предметов достигнут нужного качества.", st["body"]),
        data_table(
            ["Все шесть предметов", "Все параметры войск"],
            [
                ("Обычные", "+3%"),
                ("Необычные", "+6%"),
                ("Редкие", "+9%"),
                ("Эпические", "+12%"),
                ("Легендарные", "+15%"),
            ],
            [105 * mm, 71 * mm],
            st,
            ["LEFT", "CENTER"],
        ),
        Spacer(1, 5 * mm),
        callout("Рекомендуемый ранний план: сначала поднимайте самый отстающий предмет, пока все шесть не достигнут 11-го уровня. Не ждите выпадения редкого ножа - Ржавый нож станет лучшей версией после улучшения.", st),
        Spacer(1, 3 * mm),
        P("Один продвинутый предмет усиливает собственные параметры, но не открывает следующую ступень бонуса комплекта. Проверено в клиенте 2.6.100.261 по таблицам открытия функций, предметов Коллекции, комплектов и источников материалов.", st["small"]),
    ]
    return story


def build(filename: str, locale: str, story):
    path = OUTPUT / filename
    doc = GuideDocTemplate(str(path), locale)
    doc.build(story)
    return path


if __name__ == "__main__":
    combined_story = english_story() + [PageBreak()] + russian_story()
    combined = build("Tiles-Survive-Collections-Guide-EN-RU.pdf", "bi", combined_story)
    print(combined)
