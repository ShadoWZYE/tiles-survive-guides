"""Build the combined EN/RU VeD Reservoir Raid command plan.
Run with Python and reportlab. Output path is configurable; assets are optional.
"""
from pathlib import Path
import argparse
import json
from html import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak, Flowable

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=ROOT/'docs/reports/Tiles-Survive-Reservoir-Raid-VeD-Battle-Plan-EN-RU.pdf')
args = parser.parse_args()
args.output.parent.mkdir(parents=True, exist_ok=True)
font_dir = Path('C:/Windows/Fonts')
if (font_dir/'segoeui.ttf').exists():
    regular, bold = font_dir/'segoeui.ttf', font_dir/'segoeuib.ttf'
else:
    regular = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    bold = regular.with_name('DejaVuSans-Bold.ttf')
pdfmetrics.registerFont(TTFont('Body', str(regular)))
pdfmetrics.registerFont(TTFont('Bold', str(bold)))
NAVY=colors.HexColor('#12304B'); INK=colors.HexColor('#162B3A'); PALE=colors.HexColor('#EFF4F8')
W=182*mm
ST={
 'title':ParagraphStyle('title',fontName='Bold',fontSize=21,leading=25,textColor=NAVY,spaceAfter=10),
 'h':ParagraphStyle('h',fontName='Bold',fontSize=12,leading=15,textColor=NAVY,spaceBefore=9,spaceAfter=6),
 'body':ParagraphStyle('body',fontName='Body',fontSize=9.5,leading=13,textColor=INK,spaceAfter=6),
 'cell':ParagraphStyle('cell',fontName='Body',fontSize=8.4,leading=11,textColor=INK),
 'head':ParagraphStyle('head',fontName='Bold',fontSize=8.4,leading=11,textColor=colors.white),
 'small':ParagraphStyle('small',fontName='Body',fontSize=8,leading=10.5,textColor=INK,spaceAfter=5),
}
def p(text,style='body'): return Paragraph(text,ST[style])
def table(headers,rows,widths):
    data=[[p(x,'head') for x in headers]]+[[p(str(x),'cell') for x in r] for r in rows]
    t=Table(data,colWidths=[v*mm for v in widths],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#C4D0DA')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    return t

# Green/yellow status was explicitly confirmed by the commander.
groups=[
 ('S',[('ChaosGoblin',14.93),('Artur',13.96),('Wanderlust',13.36),('Yildiz',12.80)],
  'Strike / central','Ударная / центр',
  'ChaosGoblin + Wanderlust help Solar; Artur + Yildiz help Helipad. After capture, respond to contested treatment centers.',
  'ChaosGoblin + Wanderlust помогают на солнечной; Artur + Yildiz - на площадке. После захвата помогают центрам под атакой.',
  'T+15: all four to Central on command. ChaosGoblin anchors; Artur leads attacks; Wanderlust/Yildiz reinforce or intercept.',
  'T+15: четверо в центр по команде. ChaosGoblin - гарнизон; Artur - атаки; Wanderlust/Yildiz - подкрепления и перехват.'),
 ('A',[('Salman',12.87),('Luke',10.53),('Avalon',8.98),('Shikiiigami',8.72)],'Treatment 1 / SW','Центр 1 / ЮЗ',
  'Salman anchors Treatment 1; Luke reports; Avalon and Shikiiigami reinforce. Shikiiigami can cover Plant 1 on call.',
  'Salman держит центр 1; Luke докладывает; Avalon и Shikiiigami усиливают. Shikiiigami помогает заводу 1 по команде.',
  'Hold Treatment 1 throughout. Move only after R4 names relief.', 'Держать центр 1 весь бой. Уходить только после назначенной R4 замены.'),
 ('B',[('Loki',12.13),('Sattow',11.43),('Hammy',9.08)],'Treatment 2 / NE','Центр 2 / СВ',
  'Loki anchors Treatment 2; Sattow reinforces and reports; Hammy reinforces / scouts Plant 2.',
  'Loki держит центр 2; Sattow усиливает и докладывает; Hammy усиливает / следит за заводом 2.',
  'Hold Treatment 2 throughout. Move only after R4 names relief.', 'Держать центр 2 весь бой. Уходить только после назначенной R4 замены.'),
 ('C',[('LadyGroz',11.26),('Filin',7.52),('Wróżka Nerwuska1',6.43)],'Solar / NW','Солнечная / СЗ',
  'LadyGroz captures/anchors Solar; Filin supports; Wróżka Nerwuska1 scouts and prepares to hold.',
  'LadyGroz захватывает солнечную; Filin помогает; Wróżka Nerwuska1 разведывает и готовится держать.',
  'T+15: LadyGroz + Filin to Dev Compound only after Wróżka confirms Solar relief. If relief is unsafe, stay and ask S for help.',
  'T+15: LadyGroz + Filin в комплекс после подтверждения смены Wróżka. Если удержание опасно, остаться и запросить S.'),
 ('D',[('Martyku',10.22),('Bruklin88',7.72),('Mortisha',6.81)],'Helipad / SE','Площадка / ЮВ',
  'Martyku captures/anchors Helipad; Bruklin88 supports; Mortisha scouts and prepares to hold.',
  'Martyku захватывает площадку; Bruklin88 помогает; Mortisha разведывает и готовится держать.',
  'T+15: Martyku + Bruklin88 to Munitions only after Mortisha confirms relief. If heavily contested, request S.',
  'T+15: Martyku + Bruklin88 на военный завод после смены Mortisha. При сильном сопротивлении запросить S.'),
 ('P1',[('Lexxiii',9.46),('CaptMac',7.14)],'Plant 1 / SW','Завод 1 / ЮЗ',
  'Lexxiii anchors Plant 1; CaptMac reinforces and watches the SW approach.',
  'Lexxiii держит завод 1; CaptMac усиливает и следит за подходом с ЮЗ.',
  'Hold. CaptMac can collect SW tanks only when the garrison is safe and R4 releases them.',
  'Держать. CaptMac собирает на ЮЗ только при безопасном гарнизоне и разрешении R4.'),
 ('P2',[('Баламут',9.02),('IBRAHIM Zain',6.62)],'Plant 2 / NE','Завод 2 / СВ',
  'Баламут anchors Plant 2; IBRAHIM Zain reinforces and watches the NE approach.',
  'Баламут держит завод 2; IBRAHIM Zain усиливает и следит за подходом с СВ.',
  'Hold. IBRAHIM Zain can collect NE tanks only when safe and released.',
  'Держать. IBRAHIM Zain собирает на СВ только при безопасном гарнизоне и разрешении.'),
 ('P3',[('HoloCrow',8.59),('monika',5.86)],'Plant 3 / NW','Завод 3 / СЗ',
  'HoloCrow anchors Plant 3; monika reinforces and watches the NW approach.',
  'HoloCrow держит завод 3; monika усиливает и следит за подходом с СЗ.',
  'Hold. monika can collect NW tanks only when safe and released.',
  'Держать. monika собирает на СЗ только при безопасном гарнизоне и разрешении.'),
 ('P4',[('KayKat',8.53),('ryan',8.42)],'Plant 4 / SE','Завод 4 / ЮВ',
  'KayKat anchors Plant 4; ryan reinforces and watches the SE approach.',
  'KayKat держит завод 4; ryan усиливает и следит за подходом с ЮВ.',
  'Hold. ryan can collect SE tanks only when safe and released.',
  'Держать. ryan собирает на ЮВ только при безопасном гарнизоне и разрешении.'),
 ('G',[('4uzhaya',6.00),('Xaroth',5.79),('Yesimemily',5.66),('Bulik',5.54)],'Collection / support','Сбор / поддержка',
  '4uzhaya: NW/Solar; Xaroth: NE/Treatment 2; Yesimemily: SW/Treatment 1; Bulik: SE/Helipad. Reinforce and scout before tanks.',
  '4uzhaya: СЗ/солнечная; Xaroth: СВ/центр 2; Yesimemily: ЮЗ/центр 1; Bulik: ЮВ/площадка. До волн - помощь и разведка.',
  'T+25/35/45: gather in assigned quadrant; confirm actual spawn. If no tank, reinforce. Report enemy collectors; avoid stronger solo fights.',
  'T+25/35/45: собирать в своем секторе, проверив появление. Нет точки - усиливать. Докладывать врага; не биться в одиночку с сильным.'),
 ('HQ',[('TheShadowWZYE',6.84)],'Commander','Командир',
  'Lead calls, count attendance, track score and incoming rallies. Support the nearest safe objective with main march.',
  'Команды, явка, счет и ралли врага. Основной марш - помощь ближайшему безопасному объекту.',
  'Keep command visibility. Coordinate S and substitutes. Backup commander: Artur, subject to pre-battle acceptance.',
  'Контролировать карту, S и запасных. Заместитель: Artur, после подтверждения перед боем.'),
]
reserves=[
 ('Blockbuster',12.49,'1','First call: fifth S combat march, or replace missing Treatment/utility anchor','Первый вызов: пятый боевой марш S, либо замена якоря центра/полезного объекта'),
 ('Icemind',9.20,'2','Treatment support; replace Luke/Sattow/Avalon/Hammy','Помощь центрам; замена Luke/Sattow/Avalon/Hammy'),
 ('hellolleh',8.38,'3','Plant support; replace an absent P squad member','Помощь заводам; замена отсутствующего в P'),
 ('Purplerockchick',8.37,'4','Solar/Helipad relief; C or D support','Смена на солнечной/площадке; помощь C или D'),
 ('Peacheybites!',7.62,'5','Plant relief and tank escort','Смена на заводах и прикрытие сбора'),
 ('KORAK',7.15,'6','Plant relief and tank escort','Смена на заводах и прикрытие сбора'),
 ('Eden Ivy',6.29,'7','G collection/support replacement','Замена в G: сбор и поддержка'),
 ('SWATIRAQ7',5.79,'8','G collection/support replacement','Замена в G: сбор и поддержка'),
]
chat_en='''[VeD] RR: follow TheShadowWZYE. S: ChaosGoblin, Artur, Wanderlust, Yildiz - mobile help, then Central T+15. A: Salman, Luke, Avalon, Shikiiigami - Treatment 1. B: Loki, Sattow, Hammy - Treatment 2. C: LadyGroz, Filin, Wróżka Nerwuska1 - Solar; LadyGroz+Filin to Dev T+15 after relief. D: Martyku, Bruklin88, Mortisha - Helipad; Martyku+Bruklin88 to Munitions T+15 after relief. P1: Lexxiii/CaptMac. P2: Баламут/IBRAHIM Zain. P3: HoloCrow/monika. P4: KayKat/ryan. G: 4uzhaya NW, Xaroth NE, Yesimemily SW, Bulik SE - support, then tanks T+25/35/45. Anchors stay until relieved. Main march for assigned combat; extra marches only if useful. Heal constantly. No solo feeding or kill chasing. Report target, enemy count and rally ETA. Reserves: enter only on call after T+5 if a slot is free. Timers start with preparation; live countdown wins.'''
chat_ru='''[VeD] RR: командует TheShadowWZYE. S: ChaosGoblin, Artur, Wanderlust, Yildiz - помощь, затем центр T+15. A: Salman, Luke, Avalon, Shikiiigami - центр 1. B: Loki, Sattow, Hammy - центр 2. C: LadyGroz, Filin, Wróżka Nerwuska1 - солнечная; LadyGroz+Filin в комплекс T+15 после смены. D: Martyku, Bruklin88, Mortisha - площадка; Martyku+Bruklin88 на военный завод T+15 после смены. P1: Lexxiii/CaptMac. P2: Баламут/IBRAHIM Zain. P3: HoloCrow/monika. P4: KayKat/ryan. G: 4uzhaya СЗ, Xaroth СВ, Yesimemily ЮЗ, Bulik ЮВ - помощь, затем сбор T+25/35/45. Гарнизоны стоят до замены. Основной марш - на свою боевую цель; дополнительные только с пользой. Лечить постоянно. Не атаковать сильных в одиночку, не гоняться за убийствами. Доклад: цель, число врагов, время прибытия ралли. Запасные входят по команде после T+5 при свободном месте. T считается от начала подготовки; таймер игры важнее.'''
chat_en = chat_en.replace('Reserves: enter only', 'Reserves: Blockbuster first; enter only')
chat_ru = chat_ru.replace('Запасные входят', 'Blockbuster - первая замена. Запасные входят')
assert len(chat_en)<=1000 and len(chat_ru)<=1000
players=[x for g in groups for x in g[1]]
assert len(players)==30 and len(set(n for n,_ in players))==30
assert len(reserves)==8 and not set(n for n,_ in players)&set(r[0] for r in reserves)

class Map(Flowable):
    def __init__(self,ru): Flowable.__init__(self); self.width=W; self.height=90*mm; self.ru=ru
    def draw(self):
        c=self.canv; h=self.height
        c.setFillColor(PALE);c.roundRect(0,0,W,h,8,fill=1,stroke=0)
        def box(x,y,a,b):
            c.setFillColor(colors.white);c.setStrokeColor(colors.HexColor('#AABCCC'));c.roundRect(x*mm,y*mm,52*mm,29*mm,5,fill=1,stroke=1)
            c.setFillColor(NAVY);c.setFont('Bold',9);c.drawString((x+3)*mm,(y+22)*mm,a)
            c.setFont('Body',8)
            for i,line in enumerate(b): c.drawString((x+3)*mm,(y+16-i*5)*mm,line)
        box(5,55,'NW / СЗ' if self.ru else 'NW',['Завод 3 (P3)','Солнечная (C)','Комплекс (C, T+15)'] if self.ru else ['Plant 3 (P3)','Solar (C)','Dev (C, T+15)'])
        box(125,55,'NE / СВ' if self.ru else 'NE',['Центр 2 (B)','Завод 2 (P2)'] if self.ru else ['Treatment 2 (B)','Plant 2 (P2)'])
        box(5,5,'SW / ЮЗ' if self.ru else 'SW',['Центр 1 (A)','Завод 1 (P1)'] if self.ru else ['Treatment 1 (A)','Plant 1 (P1)'])
        box(125,5,'SE / ЮВ' if self.ru else 'SE',['Завод 4 (P4)','Площадка (D)','Военный (D, T+15)'] if self.ru else ['Plant 4 (P4)','Helipad (D)','Munitions (D, T+15)'])
        c.setFillColor(NAVY);c.circle(W/2,h/2,17*mm,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont('Bold',9)
        c.drawCentredString(W/2,h/2+3*mm,'ЦЕНТР / S' if self.ru else 'CENTRAL / S');c.setFont('Body',9);c.drawCentredString(W/2,h/2-4*mm,'T+15')
        c.setStrokeColor(colors.HexColor('#007B9A'));c.setDash(3,2)
        for x,y in [(65,65),(116,65),(65,25),(116,25)]: c.circle(x*mm,y*mm,5*mm,fill=0,stroke=1)
        c.setDash()

story=[]
def title(x): story.append(p(x,'title'))
def h(x): story.append(p(x,'h'))
def body(x): story.append(p(x))
def page(): story.append(PageBreak())
for ru in (False,True):
    if ru: page()
    title('[VeD] Reservoir Raid' if not ru else '[VeD] Рейд на резервуар')
    body('R4 command plan | 4 October 2026 | English version' if not ru else 'План командования R4 | 4 октября 2026 | Русская версия')
    body('<b>Commander: TheShadowWZYE. 30 starters + 8 confirmed substitutes.</b> Allocate the strongest available march by the roster below. Group labels remain the same in both languages.' if not ru else '<b>Командир: TheShadowWZYE. 30 основных + 8 подтвержденных запасных.</b> Использовать сильнейший доступный марш по распределению ниже. Обозначения групп одинаковы в обоих языках.')
    h('Battle objective and opening' if not ru else 'Цель боя и старт')
    body('Win by Alliance Water. A/B hold both Treatment Centers; P1-P4 capture or probe their Plants; C/D take Solar/Helipad with S support. Empty objectives: capture immediately. A defended objective stronger than your pair: report, preserve troops and request a coordinated attack. R4 may concede a remote Plant to protect the major income buildings.' if not ru else 'Победа определяется союзной водой. A/B держат оба центра; P1-P4 берут или проверяют заводы; C/D берут солнечную/площадку с помощью S. Пустую точку брать сразу. Если защита сильнее вашей пары - доклад, сохранение войск и запрос общей атаки. R4 может отдать дальний завод ради основных доходных зданий.')
    story.append(Map(ru))
    story.append(Spacer(1,7))
    body('Map follows the Discord reference orientation. Blue dashed circles indicate possible tank gathering areas, not permanent buildings. Actual spawns must be scouted; quadrant boundaries and distances are schematic. Use building names and live map pins for orders.' if not ru else 'Ориентация соответствует карте из Discord. Синие пунктирные круги - возможные районы сбора водосборников, не постоянные здания. Появление проверять разведкой; границы секторов и расстояния условные. В командах использовать названия зданий и метки игры.')
    h('Power-based allocation' if not ru else 'Распределение по силе')
    body('S concentrates four high-power marches (12.80-14.93M). Salman/Loki anchor Treatment 1/2. LadyGroz/Martyku lead the later utility captures. Lower-power players have active collection, reinforcement and scouting duties. Power is an allocation proxy: hero skills, formation, march capacity and rally bonuses must be checked by the squad leads.' if not ru else 'S объединяет четыре сильных марша (12.80-14.93M). Salman/Loki держат центры 1/2. LadyGroz/Martyku ведут захват объектов второго этапа. Игроки меньшей силы собирают, усиливают и разведывают. Сила - ориентир: лидеры проверяют навыки героев, формацию, вместимость и бонусы ралли.')
    body('T+0 is the start of preparation: battle opens T+3. If your screen counts from combat start, use 12 minutes to Central and 22/32/42 minutes to tank waves. Follow the live countdown if it differs.' if not ru else 'T+0 - начало подготовки: бой открывается T+3. Если экран считает от начала боя, до центра 12 минут, до волн сбора 22/32/42. При расхождении следовать таймеру игры.')
    page()
    title('Complete starter allocation' if not ru else 'Все основные участники')
    body('Names are copied from the screenshots; power is Highest Team Power in millions. First listed member leads each group, except G (4uzhaya coordinates collection) and HQ. Each starter appears exactly once. Roles below refer to the main march.' if not ru else 'Ники переписаны со скриншотов; сила - Highest Team Power в миллионах. Первый в списке ведет группу; в G сбор координирует 4uzhaya. Каждый основной участник указан один раз. Ниже задачи основного марша.')
    rows=[]
    for g in groups:
        code,members,en,rus,open_en,open_ru,next_en,next_ru=g
        names='<br/>'.join(f'{escape(n)} <b>{v:.2f}M</b>' for n,v in members)
        rows.append([f'<b>{code}</b><br/>{rus if ru else en}',names,(open_ru if ru else open_en)+'<br/><b>T+15:</b> '+(next_ru if ru else next_en).replace('T+15: ','')])
    story.append(table(['Группа' if ru else 'Group','Игрок / сила' if ru else 'Player / power','Старт и последующие действия' if ru else 'Opening and later orders'],rows,[27,55,100]))
    page()
    title('Substitutes and battle clock' if not ru else 'Запасные и тайминг')
    body('30 starters are confirmed, so there is no free seat if all enter. Maximum 30 inside. Call a substitute at T+5 or later only for an absent/departed participant and available seat. Eight substitutes are identified; the UI displays 10 but the other two are unverified and are not allocated. R4 announces exactly who enters and whom they replace; confirm in chat.' if not ru else 'Подтверждены 30 основных: при полной явке свободных мест нет. Внутри максимум 30. Запасной входит на T+5 или позже только вместо отсутствующего/вышедшего и при свободном месте. Определены восемь запасных; интерфейс показывает 10, но еще двое не подтверждены и не распределены. R4 называет входящего и заменяемого; подтвердить в чате.')
    story.append(table(['Порядок' if ru else 'Priority','Запасной / сила' if ru else 'Substitute / power','Назначение при входе' if ru else 'Assignment on entry'],[[r[2],f'{escape(r[0])} <b>{r[1]:.2f}M</b>',r[4] if ru else r[3]] for r in reserves],[18,58,106]))
    body('Priority is a default for an open seat. A missing critical role takes precedence. Blockbuster joins S by default; if a Treatment anchor is absent, send Blockbuster there first and rebuild S from remaining leaders.' if not ru else 'Порядок - для свободного места. Замена критической роли важнее очереди. Blockbuster обычно идет в S; если нет якоря центра, сначала направить его туда, затем собрать S из остальных лидеров.')
    body('<b>Blockbuster correction:</b> 12.49M is sixth strongest in the supplied roster. If participant selection is still editable, promote Blockbuster to S and move Bulik to reserves; G then has three starters and HQ covers SE scouting until support is released. If registration is closed, client rules prohibit changing participants: retain the registered 30 and call Blockbuster first at T+5 or later when a seat is available. A UI count of 10 reserves does not raise the 30-player limit.' if not ru else '<b>Исправление по Blockbuster:</b> 12.49M - шестой по силе марш в составе. Если выбор участников еще доступен, перевести Blockbuster в S, а Bulik в запас; в G остаются трое, HQ следит за ЮВ до освобождения поддержки. Если регистрация закрыта, правила клиента запрещают менять участников: сохранить зарегистрированные 30 и первой вызвать Blockbuster на T+5 или позже при свободном месте. Счетчик 10 запасных не увеличивает лимит 30 игроков.')
    body('<b>When she enters:</b> if an S member is missing, replace that member; if Salman/Loki/LadyGroz/Martyku is missing, take that anchor and its later task. Otherwise she becomes fifth S member and R4 covers the vacant support/collection role with a released nearby march. Never leave a Treatment Center unanchored to add a fifth fighter to Central.' if not ru else '<b>После входа:</b> если нет игрока S - заменить его; если нет Salman/Loki/LadyGroz/Martyku - принять его гарнизон и дальнейшую задачу. Иначе стать пятой в S, а R4 закрывает пустую роль поддержки/сбора свободным маршем рядом. Не оставлять центр водоочистки без якоря ради пятого бойца в центре карты.')
    h('Clock and exact command sequence' if not ru else 'Часы и порядок команд')
    timeline=[
      ('T+0-3','Count starters; assign live pins; confirm squad leads and backup commander.','Проверить явку, поставить метки, подтвердить лидеров и заместителя.'),
      ('T+3','Opening objectives unlock. S assists C/D then the contested Treatment Center.','Стартовые объекты открыты. S помогает C/D, затем центру под атакой.'),
      ('T+5','Call substitutes only for available seats.','Вызвать запасных только на свободные места.'),
      ('T+12-14','Confirm C/D relief and identify enemy Central lead. S regroups; A/B remain.','Подтвердить смену C/D и разведать центр. S собирается; A/B остаются.'),
      ('T+15','S: Central; C: Dev; D: Munitions, once opening garrisons are relieved.','S: центр; C: комплекс; D: военный, после смены стартовых гарнизонов.'),
      ('T+23/33/43','G scouts assigned quadrants; R4 releases safe P supports if needed.','G проверяет сектора; R4 при необходимости освобождает помощников P.'),
      ('T+25/35/45','Tank waves: 3 / 3 / 4 spawns. G calls actual locations and gathers.','Волны: 3 / 3 / 4 точки. G сообщает реальные места и собирает.'),
      ('T+50-60','Protect income; timed flips only if score recovery requires them. Scoring ends T+60.','Защищать доход; захваты по времени при отставании. Подсчет заканчивается T+60.'),
    ]
    story.append(table(['Время' if ru else 'Time','Действия R4' if ru else 'R4 action'],[[a,c if ru else b] for a,b,c in timeline],[29,153]))
    page()
    title('R4 orders during the fight' if not ru else 'Команды R4 в бою')
    commands=[
      ('HOLD / ДЕРЖАТЬ','Hold the named main-march garrison. Reinforce; no rotation until a replacement confirms arrival.','Держать названный гарнизон основным маршем. Усиливать; не уходить до прибытия замены.'),
      ('RELIEF / СМЕНА','Name outgoing and incoming player. Incoming reports IN, then outgoing recalls and heals. A weak replacement needs extra cover.','Назвать уходящего и замену. Замена пишет НА МЕСТЕ; затем уходящий возвращает марш и лечит. Слабую замену прикрыть.'),
      ('RALLY / РАЛЛИ','Name leader, target, joiners and launch time. Joiners confirm march availability. Check rally capacity/bonuses; highest power alone is not proof of best rally lead.','Назвать лидера, цель, участников и время запуска. Участники подтверждают марш. Проверить лимит/бонусы; сила сама по себе не доказывает лучший выбор лидера.'),
      ('HIT / УДАР','For a planned attack wave, specify arrival time, not merely launch time. Hit a defended point only with adequate support.','Для общей атаки задавать время прибытия, а не только отправки. Защищенную точку атаковать с достаточной поддержкой.'),
      ('REINFORCE / УСИЛИТЬ','Name target and players. Send best available useful march; check capacity. After taking a point, establish the anchor and fill defense.','Назвать цель и игроков. Отправить лучший полезный доступный марш, проверить лимит. После захвата поставить якорь и заполнить защиту.'),
      ('TANK / СБОР','Name quadrant and live pin. Collectors acknowledge; escort if contested. Empty quadrant: report and reinforce nearby instead of waiting.','Назвать сектор и метку. Сборщики подтверждают; при споре дать прикрытие. Нет точки - доклад и помощь рядом вместо ожидания.'),
      ('RESET / ПЕРЕСБОР','Recall, heal and regroup at the named location. Stop isolated repeat attacks.','Вернуть войска, вылечить и собраться у названной метки. Прекратить одиночные повторные атаки.'),
    ]
    story.append(table(['Команда' if ru else 'Call','Действие' if ru else 'Action'],[[a,c if ru else b] for a,b,c in commands],[36,146]))
    h('Decision rules for the commander' if not ru else 'Решения командира')
    body('<b>Central heavily defended:</b> scout first. Keep A/B income; establish Munitions/Dev if feasible, then rally with S and released supports. Do not empty both Treatment Centers. If capture remains unrealistic, defend the two Treatments, utility buffs and viable Plants, and contest tanks.' if not ru else '<b>Центр сильно защищен:</b> сначала разведка. Сохранить доход A/B; по возможности взять военный/комплекс, затем ралли S с освобожденной поддержкой. Не опустошать оба центра. Если захват нереален, держать два центра, полезные объекты и доступные заводы, бороться за сбор.')
    body('<b>Utility relief too weak:</b> keep the original anchor until support arrives; postpone Dev/Munitions rotation. <b>Two rallies incoming:</b> prioritize the higher-value vulnerable objective and call reinforcements before impact. <b>Behind:</b> arrange two concurrent pressure targets; strike where reports show weaker defense. <b>Ahead:</b> keep major income stable and intercept tank collectors.' if not ru else '<b>Смена на полезном объекте слаба:</b> оставить якорь до помощи; отложить переход к комплексу/военному. <b>Два ралли врага:</b> сначала усилить более доходную уязвимую цель до удара. <b>Отстаем:</b> давить две цели одновременно; бить туда, где разведка показывает слабую защиту. <b>Ведем:</b> держать основной доход и перехватывать сборщиков.')
    body('Report: TARGET - HELD/CONTESTED/LOST - ENEMY COUNT - RALLY ETA - HELP NEEDED. Example: Treatment 2 - held - 4 enemy marches - rally arrives 00:40 - need S pair. Only HQ changes assignments; group leads report and execute. If HQ disconnects, Artur takes calls once the agreed handover is announced.' if not ru else 'Доклад: ЦЕЛЬ - ДЕРЖИМ/БОЙ/ПОТЕРЯ - ВРАГОВ - ПРИБЫТИЕ РАЛЛИ - НУЖНА ПОМОЩЬ. Пример: центр 2 - держим - 4 марша - ралли через 00:40 - нужна пара S. Только HQ меняет назначения; лидеры докладывают и выполняют. При отключении HQ Artur принимает команды после объявленной согласованной передачи.')
    page()
    title('Mechanics and alliance message' if not ru else 'Правила и сообщение альянсу')
    objs=[
      ('Central / Центральный резервуар','T+15','1,800','9,000 / 4,500'),
      ('Treatment x2 / Водоочистка x2','T+3','1,200 each / каждый','6,000 / 3,000'),
      ('Plants x4 / Заводы x4','T+3','600 each / каждый','3,000 / 1,500'),
      ('Solar / Солнечная','T+3','240','1,200 / 600'),
      ('Helipad / Площадка','T+3','240','1,200 / 600'),
      ('Munitions / Военный','T+15','240','1,200 / 600'),
      ('Dev / Комплекс','T+15','240','1,200 / 600'),
    ]
    story.append(table(['Объект' if ru else 'Objective','Открытие' if ru else 'Open','Вода/мин' if ru else 'Water/min','Захват: 1-й / повтор' if ru else 'Capture: first / repeat'],objs,[67,23,42,50]))
    body('Standard control time: 180 seconds; Solar halves it. Helipad halves relocation cooldown. Client Munitions parameters: +20% damage and +20% defense. Dev launches Infected at enemy-held buildings; check its live skill readiness and target through the controller. Kills earn Solo Water, not Alliance Water.' if not ru else 'Удержание для контроля: 180 секунд; солнечная сокращает вдвое. Площадка сокращает откат телепорта вдвое. Параметры военного в клиенте: +20% урона и +20% защиты. Комплекс отправляет зараженных на здания врага; оператор проверяет готовность навыка и цель. Убийства дают личную, не союзную воду.')
    body('Before entry, recall marches/scouts and remove Comms Outpost reinforcements. Healing in RR costs no resources; hospital capacity is unlimited and troops do not die. Heal continuously and check timers. Early exit blocks return for 10 minutes. Maintain a usable march for emergencies if capacity permits; do not send a weak spare into a strong defense just to fill a slot.' if not ru else 'До входа вернуть марши/разведку и убрать подкрепления из пункта связи. Лечение в RR не требует ресурсов; госпиталь без лимита, войска не погибают. Лечить постоянно и следить за таймерами. Ранний выход закрывает вход на 10 минут. По возможности иметь полезный марш для экстренной помощи; не отправлять слабый запасной в сильную защиту ради заполнения места.')
    h('Copy-paste message - '+str(len(chat_ru if ru else chat_en))+(' символов' if ru else ' characters'))
    story.append(p(escape(chat_ru if ru else chat_en),'small'))
    h('Evidence and final pre-battle checks' if not ru else 'Источники и проверка перед боем')
    body('Roster: 18 screenshots supplied by the commander; green starters/yellow substitutes confirmed in chat. Mechanics: local Tiles Survive client snapshot 2.6.100.261, AvaPhase, AvaBuildings, AvaMineCollection and English event help, re-read 4 Oct 2026. Map: supplied Discord reference. These are a documented client snapshot, not a live server update check; current in-game countdown and tooltip take precedence.' if not ru else 'Состав: 18 скриншотов командира; зеленые основные/желтые запасные подтверждены в чате. Правила: локальный снимок клиента Tiles Survive 2.6.100.261, AvaPhase, AvaBuildings, AvaMineCollection и справка, повторно прочитаны 04.10.2026. Карта: изображение из Discord. Это снимок клиента, не проверка обновления сервера; текущий таймер и подсказки игры важнее.')
    body('R4 confirms live attendance, main-march readiness, leader rally capacity and spawn-side access. Strategy and assignments are proposed orders based on the supplied power; no enemy roster or attendance forecast was supplied. Scout and adjust before committing across the map.' if not ru else 'R4 проверяет явку, готовность основных маршей, лимит ралли лидеров и доступ со стороны появления. Назначения - предлагаемые команды по указанной силе; состав врага и прогноз явки не предоставлены. До перехода через карту разведать и скорректировать.')

def footer(c,doc):
    c.setStrokeColor(colors.HexColor('#C4D0DA'));c.line(14*mm,13*mm,196*mm,13*mm)
    c.setFont('Body',8);c.setFillColor(INK);c.drawString(14*mm,8*mm,'[VeD] RR | EN / RU | 2026-10-04');c.drawRightString(196*mm,8*mm,str(doc.page))
doc=SimpleDocTemplate(str(args.output),pagesize=A4,leftMargin=14*mm,rightMargin=14*mm,topMargin=13*mm,bottomMargin=18*mm,title='VeD Reservoir Raid Battle Plan - English and Russian',author='Alliance command planning')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
args.output.with_suffix('.txt').write_text('EN ('+str(len(chat_en))+' characters)\n'+chat_en+'\n\nRU ('+str(len(chat_ru))+' characters)\n'+chat_ru+'\n',encoding='utf-8')
print(json.dumps({'pdf':str(args.output),'starters':len(players),'reserves':len(reserves),'starter_power_M':round(sum(v for _,v in players),2),'EN_characters':len(chat_en),'RU_characters':len(chat_ru)},ensure_ascii=False))
