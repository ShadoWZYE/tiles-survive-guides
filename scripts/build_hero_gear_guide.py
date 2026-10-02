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
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "docs" / "Tiles-Survive-Hero-Gear-Upgrade-Guide-EN-RU.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

def first_existing(*paths: str) -> str:
    for candidate in paths:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError("Install Segoe UI, Arial, or DejaVu Sans to build the guide.")


pdfmetrics.registerFont(TTFont("Segoe", first_existing(
    r"C:\Windows\Fonts\segoeui.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)))
pdfmetrics.registerFont(TTFont("Segoe-Bold", first_existing(
    r"C:\Windows\Fonts\segoeuib.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)))

NAVY = colors.HexColor("#102A4C")
NAVY_2 = colors.HexColor("#183B67")
BLUE = colors.HexColor("#237BC1")
CYAN = colors.HexColor("#21C4D6")
GOLD = colors.HexColor("#FFB62E")
ORANGE = colors.HexColor("#F47C36")
RED = colors.HexColor("#D94949")
INK = colors.HexColor("#132238")
MUTED = colors.HexColor("#52677F")
PALE = colors.HexColor("#EEF5FB")
PALE_BLUE = colors.HexColor("#DDEEF9")
PALE_GOLD = colors.HexColor("#FFF4D5")
WHITE = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#CFDAE6"))
    canvas.line(MARGIN, 12 * mm, PAGE_W - MARGIN, 12 * mm)
    canvas.setFont("Segoe", 7.4)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 7.5 * mm, "Tiles Survive client 2.6.100.261 | data extracted 18 Sep 2026 | EN / RU")
    canvas.drawRightString(PAGE_W - MARGIN, 7.5 * mm, f"{doc.page}")
    canvas.restoreState()


doc = BaseDocTemplate(
    str(OUT),
    pagesize=A4,
    leftMargin=MARGIN,
    rightMargin=MARGIN,
    topMargin=13 * mm,
    bottomMargin=16 * mm,
    title="Tiles Survive Hero Gear Upgrade Guide",
    author="Client-data guide",
)
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
doc.addPageTemplates([PageTemplate(id="guide", frames=[frame], onPage=footer)])

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleX", fontName="Segoe-Bold", fontSize=23, leading=26, textColor=NAVY, spaceAfter=2 * mm))
styles.add(ParagraphStyle(name="Deck", fontName="Segoe", fontSize=9.5, leading=13, textColor=MUTED, spaceAfter=4 * mm))
styles.add(ParagraphStyle(name="H1X", fontName="Segoe-Bold", fontSize=15, leading=18, textColor=NAVY, spaceBefore=2 * mm, spaceAfter=2 * mm))
styles.add(ParagraphStyle(name="H2X", fontName="Segoe-Bold", fontSize=11, leading=13, textColor=NAVY, spaceAfter=1.2 * mm))
styles.add(ParagraphStyle(name="BodyX", fontName="Segoe", fontSize=8.6, leading=11.4, textColor=INK))
styles.add(ParagraphStyle(name="BodySmall", fontName="Segoe", fontSize=7.6, leading=9.8, textColor=INK))
styles.add(ParagraphStyle(name="WhiteSmall", fontName="Segoe", fontSize=7.7, leading=10, textColor=WHITE))
styles.add(ParagraphStyle(name="WhiteHead", fontName="Segoe-Bold", fontSize=10.5, leading=12.5, textColor=WHITE))
styles.add(ParagraphStyle(name="Kicker", fontName="Segoe-Bold", fontSize=7.3, leading=9, textColor=CYAN, uppercase=True, tracking=1.1))
styles.add(ParagraphStyle(name="Callout", fontName="Segoe-Bold", fontSize=9.5, leading=12, textColor=NAVY))
styles.add(ParagraphStyle(name="TableHead", fontName="Segoe-Bold", fontSize=7.5, leading=9, textColor=WHITE, alignment=TA_LEFT))
styles.add(ParagraphStyle(name="TableCell", fontName="Segoe", fontSize=7.5, leading=9.2, textColor=INK))
styles.add(ParagraphStyle(name="TableCellBold", fontName="Segoe-Bold", fontSize=7.5, leading=9.2, textColor=INK))
styles.add(ParagraphStyle(name="CenterBig", fontName="Segoe-Bold", fontSize=19, leading=21, textColor=WHITE, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="CenterBigRU", fontName="Segoe-Bold", fontSize=16, leading=17, textColor=WHITE, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="BodyRU", fontName="Segoe", fontSize=7.9, leading=10.2, textColor=INK))
styles.add(ParagraphStyle(name="CenterSmall", fontName="Segoe", fontSize=7.5, leading=9, textColor=WHITE, alignment=TA_CENTER))


def p(text, style="BodyX"):
    text = text.replace("—", "-").replace("→", "-").replace("‑", "-")
    return Paragraph(text, styles[style])


def bullet(text, style="BodyX"):
    return Paragraph(f"<font color='#21A7BC'>&#8226;</font> {text}", styles[style])


story = []

# PAGE 1
story += [
    p("HERO GEAR FIELD GUIDE", "Kicker"),
    p("Upgrade requirements — including level 80+", "TitleX"),
    p("A practical route from ordinary gear to Superalloy. Figures below come from the installed English client and decoded configuration tables, not community estimates.", "Deck"),
]

headline = Table([
    [p("LEVEL 80", "CenterBig"), p("10 STARS", "CenterBig"), p("ASCEND", "CenterBig"), p("LEVEL 200", "CenterBig")],
    [p("Alloy level cap", "CenterSmall"), p("Alloy enhancement cap", "CenterSmall"), p("10 stages", "CenterSmall"), p("Superalloy cap", "CenterSmall")],
], colWidths=[doc.width/4]*4, rowHeights=[11*mm, 8*mm])
headline.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,-1), BLUE),
    ("BACKGROUND", (1,0), (1,-1), colors.HexColor("#4E56A6")),
    ("BACKGROUND", (2,0), (2,-1), ORANGE),
    ("BACKGROUND", (3,0), (3,-1), RED),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("GRID", (0,0), (-1,-1), 1, WHITE),
    ("LEFTPADDING", (0,0), (-1,-1), 4),
    ("RIGHTPADDING", (0,0), (-1,-1), 4),
]))
story += [headline, Spacer(1, 4*mm), p("The correct upgrade order", "H1X")]

steps = [
    ("1", "Obtain the correct Alloy piece", "Helmet, Armor and Greaves are separate. A Custom Alloy Gear Crate lets you choose one piece; 20 Alloy Gear Fragments craft one crate."),
    ("2", "Level it to 80", "Feed Gear Scraps into the item. Scrap values are 100, 400, 2,000 and 10,000 EXP. Any excess EXP is returned as scraps."),
    ("3", "Enhance it to 10 stars", "Enhancement consumes duplicate Legendary/Alloy gear. The client requires 25 duplicate pieces from 0 to 10 stars — 26 copies total including the equipped base piece."),
    ("4", "Complete all 10 Ascension stages", "Each stage records a cost of 3 eligible gear/material units. That is 30 units across the full track. The live selection screen determines which gear qualifies."),
    ("5", "Finish Ascension", "The piece becomes Superalloy while retaining level and Star Rating. Its level cap rises to 200 and its enhancement ladder also expands."),
]
step_rows = []
for n, title, desc in steps:
    step_rows.append([
        p(n, "CenterBig"),
        p(f"<b>{title}</b><br/><font color='#52677F'>{desc}</font>", "BodyX")
    ])
st = Table(step_rows, colWidths=[13*mm, doc.width-13*mm], rowHeights=[23*mm, 24*mm, 26*mm, 27*mm, 24*mm])
st.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,-1), NAVY_2),
    ("BACKGROUND", (1,0), (1,-1), PALE),
    ("BOX", (0,0), (-1,-1), 0.8, colors.HexColor("#C8D7E5")),
    ("INNERGRID", (0,0), (-1,-1), 0.5, colors.HexColor("#D5E1EC")),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("LEFTPADDING", (0,0), (0,-1), 2),
    ("RIGHTPADDING", (0,0), (0,-1), 2),
    ("LEFTPADDING", (1,0), (1,-1), 9),
    ("RIGHTPADDING", (1,0), (1,-1), 9),
]))
story += [st, Spacer(1, 3.2*mm)]

warning = Table([[p("IMPORTANT", "WhiteHead"), p("Do not plan around level 81 until the same piece is both level 80 and 10-star, then fully ascended. The normal Alloy item itself cannot level beyond 80.", "WhiteSmall")]], colWidths=[29*mm, doc.width-29*mm])
warning.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,0), RED),
    ("BACKGROUND", (1,0), (1,0), NAVY),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("LEFTPADDING", (0,0), (-1,-1), 8),
    ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ("TOPPADDING", (0,0), (-1,-1), 7),
    ("BOTTOMPADDING", (0,0), (-1,-1), 7),
]))
story += [warning]

story += [Spacer(1, 4*mm), p("When does level 80+ unlock?", "H1X")]
unlock = Table([
    [
        p("SERVER DAY 36", "CenterBig"),
        p("<b>Expected for your server: 7 October 2026</b><br/><font color='#52677F'>Server opened 2 September 2026. As of 19 September it is approximately day 18, leaving about 18 server days.</font>", "BodyX"),
    ],
    [
        p("TWO GATES", "WhiteHead"),
        p("<b>Star enhancement:</b> HQ 10 + server day 36.<br/><b>Superalloy Ascension:</b> server day 36 + the selected Alloy piece at level 80 and 10 stars.<br/><font color='#52677F'>No research or event-completion requirement appears in the client. Normally activates at reset; allow until the 8 October reset if refresh is delayed.</font>", "BodySmall"),
    ],
], colWidths=[38*mm, doc.width-38*mm], rowHeights=[22*mm, 25*mm])
unlock.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,0), ORANGE),
    ("BACKGROUND", (0,1), (0,1), NAVY_2),
    ("BACKGROUND", (1,0), (1,-1), PALE_GOLD),
    ("GRID", (0,0), (-1,-1), 0.7, colors.HexColor("#D1DCE6")),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("LEFTPADDING", (0,0), (-1,-1), 8),
    ("RIGHTPADDING", (0,0), (-1,-1), 8),
]))
story += [unlock]

# Force page 2 cleanly
story.append(PageBreak())
story += [
    p("POST-80 COSTS", "Kicker"),
    p("Superalloy: level 80 to 200", "TitleX"),
    p("The client stores EXP as the cost to move from the current level to the next. These intervals sum exactly to the level-200 cap.", "Deck"),
]

xp_data = [[p("LEVELS", "TableHead"), p("GEAR EXP", "TableHead"), p("RUNNING TOTAL", "TableHead"), p("10K SCRAPS EQUIV.", "TableHead")]]
rows = [
    ("80 → 100", 756000, 756000),
    ("100 → 120", 817600, 1573600),
    ("120 → 140", 880700, 2454300),
    ("140 → 160", 945300, 3399600),
    ("160 → 180", 1011700, 4411300),
    ("180 → 200", 1079400, 5490700),
]
for a, cost, total in rows:
    xp_data.append([p(a, "TableCellBold"), p(f"{cost:,}", "TableCell"), p(f"{total:,}", "TableCell"), p(f"{cost/10000:.2f}", "TableCell")])
xp_data.append([p("TOTAL 80 → 200", "TableCellBold"), p("5,490,700", "TableCellBold"), p("5,490,700", "TableCellBold"), p("549.07", "TableCellBold")])
xp = Table(xp_data, colWidths=[34*mm, 42*mm, 45*mm, 45*mm], repeatRows=1)
xp.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), NAVY),
    ("BACKGROUND", (0,1), (-1,-2), colors.white),
    ("BACKGROUND", (0,-1), (-1,-1), PALE_GOLD),
    ("GRID", (0,0), (-1,-1), 0.55, colors.HexColor("#C9D7E4")),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("TOPPADDING", (0,0), (-1,-1), 4),
    ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ("LEFTPADDING", (0,0), (-1,-1), 7),
]))
story += [xp, Spacer(1, 3*mm)]

exact = Table([[p("EXACT SCRAP MIX", "WhiteHead"), p("5,490,700 EXP = 549 × 10,000-EXP scraps + 7 × 100-EXP scraps. Use whatever mix you own; this is simply an exact equivalent.", "WhiteSmall")]], colWidths=[34*mm, doc.width-34*mm])
exact.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,0), ORANGE),
    ("BACKGROUND", (1,0), (1,0), NAVY_2),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("LEFTPADDING", (0,0), (-1,-1), 8),
    ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ("TOPPADDING", (0,0), (-1,-1), 7),
    ("BOTTOMPADDING", (0,0), (-1,-1), 7),
]))
story += [exact, Spacer(1, 2.5*mm), p("Star enhancement and Ascension", "H1X")]

two_cols = Table([
    [
        [
            p("Before Ascension", "H2X"),
            bullet("0 → 10 stars consumes <b>25 duplicate Alloy pieces</b>."),
            bullet("Special-stat slots unlock at <b>2, 4 and 6 stars</b>."),
            bullet("One selectable Alloy crate costs <b>20 fragments</b>."),
            bullet("Starting only from fragments: the base plus 25 duplicates equals <b>520 fragments</b>."),
        ],
        [
            p("After Ascension", "H2X"),
            bullet("The client expands the enhancement ladder from internal rank 10 to 110."),
            bullet("From preserved rank 10 to its internal cap: <b>245 Alloy-gear material units</b>."),
            bullet("Those are internal steps, <b>not proof of 100 visible stars</b>; the UI may group them."),
            bullet("Level and existing Star Rating are retained during conversion."),
        ],
    ]
], colWidths=[doc.width/2-2*mm, doc.width/2-2*mm], hAlign="LEFT")
two_cols.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,0), PALE_BLUE),
    ("BACKGROUND", (1,0), (1,0), PALE_GOLD),
    ("BOX", (0,0), (-1,-1), 0.7, colors.HexColor("#C7D7E5")),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("LEFTPADDING", (0,0), (-1,-1), 9),
    ("RIGHTPADDING", (0,0), (-1,-1), 9),
    ("TOPPADDING", (0,0), (-1,-1), 6),
    ("BOTTOMPADDING", (0,0), (-1,-1), 6),
]))
story += [two_cols, Spacer(1, 2.5*mm)]

stage_data = [[p("ASCENSION STAGE", "TableHead"), p("1", "TableHead"), p("2", "TableHead"), p("3", "TableHead"), p("4", "TableHead"), p("5", "TableHead"), p("6", "TableHead"), p("7", "TableHead"), p("8", "TableHead"), p("9", "TableHead"), p("10", "TableHead")],
              [p("Cumulative base-stat bonus", "TableCellBold"), p("2.5%", "TableCell"), p("5%", "TableCell"), p("7.5%", "TableCell"), p("10%", "TableCell"), p("15%", "TableCell"), p("17.5%", "TableCell"), p("20%", "TableCell"), p("22.5%", "TableCell"), p("25%", "TableCell"), p("30%", "TableCell")]]
stages = Table(stage_data, colWidths=[40*mm]+[12.6*mm]*10)
stages.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), NAVY),
    ("BACKGROUND", (0,1), (0,1), PALE_BLUE),
    ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#C8D7E5")),
    ("ALIGN", (1,0), (-1,-1), "CENTER"),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("TOPPADDING", (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
]))
story += [stages, Spacer(1, 2.5*mm), p("What to press in game", "H1X")]

how = Table([
    [p("A", "CenterBig"), p("Open the hero → Gear → select the Alloy piece. Level it to 80 with Gear Scraps.", "BodyX")],
    [p("B", "CenterBig"), p("Use Enhance / Star Rating and feed duplicates until it reaches 10 stars.", "BodyX")],
    [p("C", "CenterBig"), p("Open Ascend. Fill only the displayed eligible-material slots; each stage warns that selected materials are permanently consumed.", "BodyX")],
    [p("D", "CenterBig"), p("Complete stage 10. The item becomes Superalloy; continue leveling from 80 toward 200.", "BodyX")],
], colWidths=[12*mm, doc.width-12*mm], rowHeights=[11.5*mm]*4)
how.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,-1), BLUE),
    ("BACKGROUND", (1,0), (1,-1), PALE),
    ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#CEDBE7")),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("LEFTPADDING", (1,0), (1,-1), 8),
    ("RIGHTPADDING", (1,0), (1,-1), 8),
]))
story += [how, Spacer(1, 2*mm)]

notes = Table([[p("CONFIDENCE & LIMITS", "WhiteHead"), p("Confirmed from client tables: caps, EXP curve, duplicate counts, fragment recipe, stage count/cost and stat bonuses. The extracted Ascension table records 3 materials per stage but does not name the allowed item IDs; confirm the live selection list before sacrificing gear. Reforging is separate: it rerolls special stats with Reforge Hammers; Advanced Reforge unlocks after 200 total reforges and can lock stats with Shrink Film.", "WhiteSmall")]], colWidths=[36*mm, doc.width-36*mm])
notes.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,0), NAVY_2),
    ("BACKGROUND", (1,0), (1,0), NAVY),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("LEFTPADDING", (0,0), (-1,-1), 8),
    ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ("TOPPADDING", (0,0), (-1,-1), 7),
    ("BOTTOMPADDING", (0,0), (-1,-1), 7),
]))
story += [notes]

# PAGE 3 - RUSSIAN OVERVIEW
story.append(PageBreak())
story += [
    p("СПРАВОЧНИК ПО СНАРЯЖЕНИЮ ГЕРОЕВ", "Kicker"),
    p("Улучшение снаряжения: уровень 80+", "TitleX"),
    p("Практический путь от обычного снаряжения до Суперсплава. Все значения получены из установленного английского клиента и расшифрованных таблиц конфигурации, а не из оценок сообщества.", "Deck"),
]

headline_ru = Table([
    [p("80 УРОВЕНЬ", "CenterBigRU"), p("10 ЗВЕЗД", "CenterBigRU"), p("ВОЗНЕСТИ", "CenterBigRU"), p("200 УРОВЕНЬ", "CenterBigRU")],
    [p("Предел Сплава", "CenterSmall"), p("Предел усиления", "CenterSmall"), p("10 этапов", "CenterSmall"), p("Предел Суперсплава", "CenterSmall")],
], colWidths=[doc.width/4]*4, rowHeights=[11*mm, 8*mm])
headline_ru.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,-1), BLUE),
    ("BACKGROUND", (1,0), (1,-1), colors.HexColor("#4E56A6")),
    ("BACKGROUND", (2,0), (2,-1), ORANGE),
    ("BACKGROUND", (3,0), (3,-1), RED),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("GRID", (0,0), (-1,-1), 1, WHITE),
    ("LEFTPADDING", (0,0), (-1,-1), 4),
    ("RIGHTPADDING", (0,0), (-1,-1), 4),
]))
story += [headline_ru, Spacer(1, 4*mm), p("Правильный порядок улучшения", "H1X")]

steps_ru = [
    ("1", "Получите нужный предмет из Сплава", "Шлем, Броня и Поножи являются отдельными предметами. Сундук снаряжения из Сплава на выбор позволяет выбрать одну часть; из 20 фрагментов снаряжения из Сплава создаётся один сундук."),
    ("2", "Поднимите его до уровня 80", "Используйте Обломки снаряжения. Они дают 100, 400, 2 000 или 10 000 опыта. Лишний опыт возвращается в виде обломков."),
    ("3", "Усильте до 10 звёзд", "Усиление расходует дубликаты легендарного снаряжения или снаряжения из Сплава. От 0 до 10 звёзд требуется 25 дубликатов - всего 26 копий с учётом надетого базового предмета."),
    ("4", "Пройдите все 10 этапов Вознесения", "Каждый этап требует 3 подходящих предмета или материала - всего 30 единиц. Какие именно предметы подходят, показывает экран выбора в игре."),
    ("5", "Завершите Вознесение", "Предмет становится Суперсплавом, сохраняя уровень и звёздный рейтинг. Максимальный уровень повышается до 200, а шкала усиления расширяется."),
]
step_rows_ru = []
for n, title, desc in steps_ru:
    step_rows_ru.append([p(n, "CenterBig"), p(f"<b>{title}</b><br/><font color='#52677F'>{desc}</font>", "BodyRU")])
st_ru = Table(step_rows_ru, colWidths=[13*mm, doc.width-13*mm], rowHeights=[23*mm, 22*mm, 25*mm, 24*mm, 23*mm])
st_ru.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,-1), NAVY_2),
    ("BACKGROUND", (1,0), (1,-1), PALE),
    ("BOX", (0,0), (-1,-1), 0.8, colors.HexColor("#C8D7E5")),
    ("INNERGRID", (0,0), (-1,-1), 0.5, colors.HexColor("#D5E1EC")),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("LEFTPADDING", (0,0), (0,-1), 2),
    ("RIGHTPADDING", (0,0), (0,-1), 2),
    ("LEFTPADDING", (1,0), (1,-1), 9),
    ("RIGHTPADDING", (1,0), (1,-1), 9),
]))
story += [st_ru, Spacer(1, 3.2*mm)]

warning_ru = Table([[p("ВАЖНО", "WhiteHead"), p("Не планируйте переход на уровень 81, пока один и тот же предмет не достигнет уровня 80 и 10 звёзд, а затем не пройдёт полное Вознесение. Обычный предмет из Сплава не может подняться выше уровня 80.", "WhiteSmall")]], colWidths=[29*mm, doc.width-29*mm])
warning_ru.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,0), RED), ("BACKGROUND", (1,0), (1,0), NAVY),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7),
]))
story += [warning_ru, Spacer(1, 4*mm), p("Когда открываются уровни выше 80?", "H1X")]

unlock_ru = Table([
    [p("36-Й ДЕНЬ СЕРВЕРА", "CenterBig"), p("<b>Ожидаемая дата для вашего сервера: 7 октября 2026 г.</b><br/><font color='#52677F'>Сервер открылся 2 сентября 2026 г. На 19 сентября это примерно 18-й день, оставалось около 18 серверных дней.</font>", "BodyX")],
    [p("ДВА УСЛОВИЯ", "WhiteHead"), p("<b>Звёздное усиление:</b> Электростанция 10 + 36-й день сервера.<br/><b>Вознесение в Суперсплав:</b> 36-й день сервера + выбранный предмет из Сплава на уровне 80 и с 10 звёздами.<br/><font color='#52677F'>Требований по исследованиям или завершению события в клиенте нет. Обычно функция открывается после сброса; при задержке обновления подождите до сброса 8 октября.</font>", "BodySmall")],
], colWidths=[38*mm, doc.width-38*mm], rowHeights=[23*mm, 28*mm])
unlock_ru.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,0), ORANGE), ("BACKGROUND", (0,1), (0,1), NAVY_2),
    ("BACKGROUND", (1,0), (1,-1), PALE_GOLD),
    ("GRID", (0,0), (-1,-1), 0.7, colors.HexColor("#D1DCE6")),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
]))
story += [unlock_ru]

# PAGE 4 - RUSSIAN COSTS
story.append(PageBreak())
story += [
    p("ЗАТРАТЫ ПОСЛЕ 80-ГО УРОВНЯ", "Kicker"),
    p("Суперсплав: от уровня 80 до 200", "TitleX"),
    p("Клиент хранит опыт как стоимость перехода с текущего уровня на следующий. Сумма интервалов точно соответствует пределу 200-го уровня.", "Deck"),
]

xp_data_ru = [[p("УРОВНИ", "TableHead"), p("ОПЫТ СНАРЯЖЕНИЯ", "TableHead"), p("ОБЩИЙ ИТОГ", "TableHead"), p("ЭКВИВАЛЕНТ ПО 10K", "TableHead")]]
for a, cost, total in rows:
    xp_data_ru.append([p(a, "TableCellBold"), p(f"{cost:,}", "TableCell"), p(f"{total:,}", "TableCell"), p(f"{cost/10000:.2f}", "TableCell")])
xp_data_ru.append([p("ВСЕГО 80 - 200", "TableCellBold"), p("5,490,700", "TableCellBold"), p("5,490,700", "TableCellBold"), p("549.07", "TableCellBold")])
xp_ru = Table(xp_data_ru, colWidths=[34*mm, 48*mm, 42*mm, 42*mm], repeatRows=1)
xp_ru.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), NAVY), ("BACKGROUND", (0,1), (-1,-2), colors.white),
    ("BACKGROUND", (0,-1), (-1,-1), PALE_GOLD),
    ("GRID", (0,0), (-1,-1), 0.55, colors.HexColor("#C9D7E4")),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ("LEFTPADDING", (0,0), (-1,-1), 7),
]))
story += [xp_ru, Spacer(1, 3*mm)]

exact_ru = Table([[p("ТОЧНАЯ КОМБИНАЦИЯ", "WhiteHead"), p("5 490 700 опыта = 549 обломков по 10 000 опыта + 7 обломков по 100 опыта. Используйте любое сочетание, которое у вас есть; это лишь точный эквивалент.", "WhiteSmall")]], colWidths=[42*mm, doc.width-42*mm])
exact_ru.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,0), ORANGE), ("BACKGROUND", (1,0), (1,0), NAVY_2),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7),
]))
story += [exact_ru, Spacer(1, 2.5*mm), p("Звёздное усиление и Вознесение", "H1X")]

two_cols_ru = Table([[[
    p("До Вознесения", "H2X"),
    bullet("От 0 до 10 звёзд расходуется <b>25 дубликатов из Сплава</b>."),
    bullet("Ячейки особых параметров открываются на <b>2, 4 и 6 звёздах</b>."),
    bullet("Один выбираемый сундук из Сплава стоит <b>20 фрагментов</b>."),
    bullet("Если начинать только с фрагментов: база и 25 дубликатов стоят <b>520 фрагментов</b>."),
], [
    p("После Вознесения", "H2X"),
    bullet("Клиент расширяет внутреннюю шкалу усиления с ранга 10 до 110."),
    bullet("От сохранённого ранга 10 до внутреннего предела требуется <b>245 единиц материала из Сплава</b>."),
    bullet("Это внутренние этапы, а <b>не доказательство 100 видимых звёзд</b>; интерфейс может объединять их."),
    bullet("Уровень и существующий звёздный рейтинг сохраняются при преобразовании."),
]]], colWidths=[doc.width/2-2*mm, doc.width/2-2*mm], hAlign="LEFT")
two_cols_ru.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,0), PALE_BLUE), ("BACKGROUND", (1,0), (1,0), PALE_GOLD),
    ("BOX", (0,0), (-1,-1), 0.7, colors.HexColor("#C7D7E5")),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
    ("LEFTPADDING", (0,0), (-1,-1), 9), ("RIGHTPADDING", (0,0), (-1,-1), 9),
    ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
]))
story += [two_cols_ru, Spacer(1, 2.5*mm)]

stage_data_ru = [[p("ЭТАП ВОЗНЕСЕНИЯ", "TableHead")] + [p(str(i), "TableHead") for i in range(1, 11)],
                 [p("Суммарный бонус базовых параметров", "TableCellBold")] + [p(x, "TableCell") for x in ("2.5%", "5%", "7.5%", "10%", "15%", "17.5%", "20%", "22.5%", "25%", "30%")]]
stages_ru = Table(stage_data_ru, colWidths=[40*mm]+[12.6*mm]*10)
stages_ru.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), NAVY), ("BACKGROUND", (0,1), (0,1), PALE_BLUE),
    ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#C8D7E5")),
    ("ALIGN", (1,0), (-1,-1), "CENTER"), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
]))
story += [stages_ru, Spacer(1, 2.5*mm), p("Что нажимать в игре", "H1X")]

how_ru = Table([
    [p("A", "CenterBig"), p("Откройте героя - Снаряжение - выберите предмет из Сплава. Поднимите его до уровня 80 Обломками снаряжения.", "BodyX")],
    [p("B", "CenterBig"), p("Откройте Усиление / Звёздный рейтинг и расходуйте дубликаты до 10 звёзд.", "BodyX")],
    [p("C", "CenterBig"), p("Откройте Вознесение. Заполняйте только показанные ячейки подходящих материалов; выбранные предметы расходуются навсегда.", "BodyX")],
    [p("D", "CenterBig"), p("Завершите этап 10. Предмет станет Суперсплавом; продолжайте повышать уровень с 80 до 200.", "BodyX")],
], colWidths=[12*mm, doc.width-12*mm], rowHeights=[12.5*mm]*4)
how_ru.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,-1), BLUE), ("BACKGROUND", (1,0), (1,-1), PALE),
    ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#CEDBE7")),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("LEFTPADDING", (1,0), (1,-1), 8), ("RIGHTPADDING", (1,0), (1,-1), 8),
]))
story += [how_ru, Spacer(1, 2*mm)]

notes_ru = Table([[p("ТОЧНОСТЬ И ОГРАНИЧЕНИЯ", "WhiteHead"), p("По таблицам клиента подтверждены пределы, кривая опыта, число дубликатов, рецепт фрагментов, число и стоимость этапов, а также бонусы параметров. Таблица Вознесения указывает 3 материала на этап, но не называет допустимые ID предметов - проверяйте список выбора в игре перед расходованием снаряжения. Перековка отдельна: она меняет особые параметры Молотами перековки; Продвинутая перековка открывается после 200 перековок и позволяет фиксировать параметры Термоусадочной плёнкой.", "WhiteSmall")]], colWidths=[43*mm, doc.width-43*mm])
notes_ru.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (0,0), NAVY_2), ("BACKGROUND", (1,0), (1,0), NAVY),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7),
]))
story += [notes_ru]

doc.build(story)
print(OUT)
