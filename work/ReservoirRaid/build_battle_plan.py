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
from reportlab.lib.utils import ImageReader
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
  'T+15: Central unless HQ changes the plan. ChaosGoblin holds it; Artur leads attacks. Others choose help, escort or attacks themselves. Keep Central covered.',
  'T+15: центр, если HQ не меняет план. ChaosGoblin держит; Artur ведет атаки. Остальные сами выбирают помощь, прикрытие или атаки. Сохранить защиту центра.'),
 ('A',[('Salman',12.87),('Luke',10.53),('Avalon',8.98),('Shikiiigami',8.72)],'Treatment 1 / SW','Центр 1 / ЮЗ',
  'Salman anchors Treatment 1; Luke reports; Avalon and Shikiiigami reinforce. Shikiiigami may help Plant 1 when Treatment 1 is safe.',
  'Salman держит центр 1; Luke докладывает; Avalon и Shikiiigami усиливают. Shikiiigami помогает заводу 1, если центр 1 в безопасности.',
  'Keep a strong Treatment 1 anchor. Supports may cover Plant 1 or collect nearby water when safe; report the move.', 'Сохранить сильный гарнизон центра 1. Помощники идут на завод 1 или сбор рядом, если безопасно; сообщить переход.'),
 ('B',[('Loki',12.13),('Sattow',11.43),('Hammy',9.08)],'Treatment 2 / NE','Центр 2 / СВ',
  'Loki anchors Treatment 2; Sattow reinforces and reports; Hammy reinforces / scouts Plant 2.',
  'Loki держит центр 2; Sattow усиливает и докладывает; Hammy усиливает / следит за заводом 2.',
  'Keep a strong Treatment 2 anchor. Supports may cover Plant 2 or collect nearby water when safe; report the move.', 'Сохранить сильный гарнизон центра 2. Помощники идут на завод 2 или сбор рядом, если безопасно; сообщить переход.'),
 ('C',[('LadyGroz',11.26),('Filin',7.52),('Wróżka Nerwuska1',6.43)],'Solar / NW','Солнечная / СЗ',
  'LadyGroz captures/anchors Solar; Filin supports; Wróżka Nerwuska1 scouts and prepares to hold.',
  'LadyGroz захватывает солнечную; Filin помогает; Wróżka Nerwuska1 разведывает и готовится держать.',
  'T+15: LadyGroz + Filin move to Dev once Wróżka is holding Solar safely. No HQ approval needed. If unsafe, keep cover and report.',
  'T+15: LadyGroz + Filin идут в комплекс, когда Wróżka безопасно держит солнечную. Разрешение HQ не нужно. При угрозе сохранить защиту и доложить.'),
 ('D',[('Martyku',10.22),('Bruklin88',7.72),('Mortisha',6.81)],'Helipad / SE','Площадка / ЮВ',
  'Martyku captures/anchors Helipad; Bruklin88 supports; Mortisha scouts and prepares to hold.',
  'Martyku захватывает площадку; Bruklin88 помогает; Mortisha разведывает и готовится держать.',
  'T+15: Martyku + Bruklin88 move to Munitions once Mortisha holds Helipad safely. No HQ approval needed. Report strong opposition.',
  'T+15: Martyku + Bruklin88 идут на военный, когда Mortisha безопасно держит площадку. Разрешение HQ не нужно. Доложить сильное сопротивление.'),
 ('P1',[('Lexxiii',9.46),('CaptMac',7.14)],'Plant 1 / SW','Завод 1 / ЮЗ',
  'Lexxiii anchors Plant 1; CaptMac reinforces and watches the SW approach.',
  'Lexxiii держит завод 1; CaptMac усиливает и следит за подходом с ЮЗ.',
  'Lexxiii holds; CaptMac may collect SW tanks/spills when the anchor is safe. Report and go; return if threatened.',
  'Lexxiii держит; CaptMac собирает точки/разлитую воду на ЮЗ при безопасном гарнизоне. Сообщить и идти; вернуться при угрозе.'),
 ('P2',[('Баламут',9.02),('IBRAHIM Zain',6.62)],'Plant 2 / NE','Завод 2 / СВ',
  'Баламут anchors Plant 2; IBRAHIM Zain reinforces and watches the NE approach.',
  'Баламут держит завод 2; IBRAHIM Zain усиливает и следит за подходом с СВ.',
  'Баламут holds; IBRAHIM Zain may collect NE tanks/spills when safe. Report and go; return if threatened.',
  'Баламут держит; IBRAHIM Zain собирает точки/разлитую воду на СВ, если безопасно. Сообщить и идти; вернуться при угрозе.'),
 ('P3',[('HoloCrow',8.59),('monika',5.86)],'Plant 3 / NW','Завод 3 / СЗ',
  'HoloCrow anchors Plant 3; monika reinforces and watches the NW approach.',
  'HoloCrow держит завод 3; monika усиливает и следит за подходом с СЗ.',
  'HoloCrow holds; monika may collect NW tanks/spills when safe. Report and go; return if threatened.',
  'HoloCrow держит; monika собирает точки/разлитую воду на СЗ, если безопасно. Сообщить и идти; вернуться при угрозе.'),
 ('P4',[('KayKat',8.53),('ryan',8.42)],'Plant 4 / SE','Завод 4 / ЮВ',
  'KayKat anchors Plant 4; ryan reinforces and watches the SE approach.',
  'KayKat держит завод 4; ryan усиливает и следит за подходом с ЮВ.',
  'KayKat holds; ryan may collect SE tanks/spills when safe. Report and go; return if threatened.',
  'KayKat держит; ryan собирает точки/разлитую воду на ЮВ, если безопасно. Сообщить и идти; вернуться при угрозе.'),
 ('G',[('4uzhaya',6.00),('Xaroth',5.79),('Yesimemily',5.66),('Bulik',5.54)],'Collection / support','Сбор / поддержка',
  '4uzhaya: NW/Solar; Xaroth: NE/Treatment 2; Yesimemily: SW/Treatment 1; Bulik: SE/Helipad. Reinforce and scout before tanks.',
  '4uzhaya: СЗ/солнечная; Xaroth: СВ/центр 2; Yesimemily: ЮЗ/центр 1; Bulik: ЮВ/площадка. До волн - помощь и разведка.',
  'Collect nearby spills immediately when safe, at any time. T+25/35/45: gather tank waves. No water: reinforce/scout. Report moves and enemy collectors.',
  'Безопасную разлитую воду собирать сразу в любое время. T+25/35/45: волны сбора. Нет воды - помощь/разведка. Докладывать переходы и сборщиков врага.'),
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
chat_en = chat_en.replace('follow TheShadowWZYE.', 'follow this plan unless HQ changes it.').replace('mobile help, then Central T+15.', 'choose help/fights; Central T+15.').replace('Anchors stay until relieved.', 'Move to your next job when safely covered; report, no approval needed.').replace('; extra marches only if useful.', '.').replace('No solo feeding or kill chasing.', 'Collect safe spills immediately; both sides can recover them.').replace('Reserves: enter only', 'Reserves: Blockbuster first; enter only')
chat_ru = chat_ru.replace('командует TheShadowWZYE.', 'следовать плану, пока HQ не изменит.').replace('помощь, затем центр T+15.', 'сами выбирают помощь/атаки; центр T+15.').replace('Гарнизоны стоят до замены.', 'Если прикрыто и безопасно, идти на следующую роль без разрешения; сообщить.').replace('; дополнительные только с пользой.', '.').replace('Не атаковать сильных в одиночку, не гоняться за убийствами.', 'Безопасную разлитую воду собирать сразу; доступна обеим сторонам.').replace('Запасные входят', 'Blockbuster - первая замена. Запасные входят')
chat_en = chat_en.replace('[VeD] RR:', '[VeD] RR: HQ=TheShadowWZYE.')
chat_ru = chat_ru.replace('[VeD] RR:', '[VeD] RR: HQ=TheShadowWZYE.')
assert len(chat_en)<=1000 and len(chat_ru)<=1000
players=[x for g in groups for x in g[1]]
assert len(players)==30 and len(set(n for n,_ in players))==30
assert len(reserves)==8 and not set(n for n,_ in players)&set(r[0] for r in reserves)

class Map(Flowable):
    def __init__(self,ru): Flowable.__init__(self); self.width=W; self.height=178*mm; self.ru=ru
    def draw(self):
        c=self.canv
        c.setFillColor(colors.HexColor('#F2E6D3'));c.roundRect(0,0,W,self.height,8,fill=1,stroke=0)
        def project(x,y): return (91+.38*(x-y))*mm,(25+.5*(x+y-125))*mm
        # Same client coordinates and isometric x-y / x+y projection as the earlier map.
        nodes=[
          ('factory',138,195,'P3: Завод 3' if self.ru else 'P3: Plant 3',['HoloCrow / monika'],2,148,48),
          ('powerstation',100,200,'C: Солнечная' if self.ru else 'C: Solar',['LadyGroz / Filin','Wróżka Nerwuska1'],2,119,48),
          ('zombie',119,162,'C: Комплекс T+15' if self.ru else 'C: Dev T+15',['LadyGroz / Filin'],2,90,48),
          ('process_center',56,105,'A: Центр 1' if self.ru else 'A: Treatment 1',['Salman / Luke','Avalon / Shikiiigami'],2,38,48),
          ('factory',33,119,'P1: Завод 1' if self.ru else 'P1: Plant 1',['Lexxiii / CaptMac'],2,10,48),
          ('factory',205,119,'P2: Завод 2' if self.ru else 'P2: Plant 2',['Баламут / IBRAHIM Zain'],132,148,48),
          ('process_center',181,132,'B: Центр 2' if self.ru else 'B: Treatment 2',['Loki / Sattow / Hammy'],132,119,48),
          ('tank',119,76,'D: Военный T+15' if self.ru else 'D: Munitions T+15',['Martyku / Bruklin88'],132,90,48),
          ('airport',138,37,'D: Площадка' if self.ru else 'D: Helipad',['Martyku / Bruklin88','Mortisha'],132,38,48),
          ('factory',100,42,'P4: Завод 4' if self.ru else 'P4: Plant 4',['KayKat / ryan'],132,10,48),
          ('center',117,117,'S: Центр T+15' if self.ru else 'S: Central T+15',['ChaosGoblin / Artur','Wanderlust / Yildiz'],62,148,58),
        ]
        c.setStrokeColor(colors.HexColor('#007C9D'));c.setLineWidth(1);c.setDash(3,2)
        for x,y in [(86,150),(86,90),(154,150),(154,90)]:
            px,py=project(x,y);c.circle(px,py,6*mm,fill=0,stroke=1)
        c.setDash()
        c.setFillColor(colors.HexColor('#006B85'));c.setFont('Bold',7.5)
        for x,y,name in [(86,150,'4uzhaya'),(86,90,'Yesimemily'),(154,150,'Xaroth'),(154,90,'Bulik')]:
            px,py=project(x,y);c.drawCentredString(px,py-9*mm,name)
        for kind,x,y,label,names,bx,by,bw in nodes:
            px,py=project(x,y)
            ax=(bx+bw if bx<20 else bx if bx>120 else bx+bw/2)*mm
            ay=(by+12 if bx<20 or bx>120 else by)*mm
            c.setStrokeColor(colors.HexColor('#8B765A'));c.setLineWidth(.6);c.line(ax,ay,px,py)
        for kind,x,y,label,names,bx,by,bw in nodes:
            px,py=project(x,y)
            asset=Path(__file__).parent/'assets'/f'sp_icon_big_ava_building_{kind}.png'
            c.drawImage(ImageReader(str(asset)),px-7*mm,py-7*mm,14*mm,14*mm,mask='auto',preserveAspectRatio=True)
            c.setFillColor(colors.white);c.setStrokeColor(colors.HexColor('#AE9F89'));c.roundRect(bx*mm,by*mm,bw*mm,24*mm,4,fill=1,stroke=1)
            c.setFillColor(NAVY);c.setFont('Bold',8);c.drawString((bx+2)*mm,(by+18)*mm,label)
            c.setFont('Body',7.4)
            for i,name in enumerate(names): c.drawString((bx+2)*mm,(by+12-i*4.5)*mm,name)

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
    h('When to move without asking' if not ru else 'Когда можно идти без разрешения')
    body('<b>Default rule: follow this plan unless HQ gives a different order.</b> You do not need a new command for each listed job. A/B protect their Treatment Centers; P1-P4 protect their Plants; C/D make their listed T+15 move when covered; G collects water and supports its sector. Other groups do not pick unrelated targets.' if not ru else '<b>Основное правило: выполнять этот план, пока HQ не даст другую команду.</b> Новая команда для каждой указанной задачи не нужна. A/B защищают центры; P1-P4 - заводы; C/D переходят по плану на T+15 при прикрытии; G собирает и помогает своему сектору. Другие группы не выбирают посторонние цели.')
    body('<b>Go to your next assigned job when all three checks pass:</b> the next objective is open; a teammate remains in the current garrison and can defend it; no enemy attack or rally is coming to that point. Check the actual garrison, not just a teammate standing nearby. Tell the squad who stays, then move and post your destination. You do not need a reply from HQ.' if not ru else '<b>Идите на следующую назначенную задачу, если выполнены три условия:</b> новая цель открыта; в текущем гарнизоне остается союзник, способный его защитить; на точку не идет атака или ралли врага. Проверяйте гарнизон, а не союзника рядом на карте. Скажите группе, кто остается; затем идите и напишите цель. Ответ HQ не нужен.')
    body('<b>Stay if any check fails.</b> Do not leave as the last defender. Do not count a weak spare march as enough cover against a stronger nearby enemy. If two players want to leave, agree who stays before either recalls. A direct HOLD order overrides the normal move rules until lifted.' if not ru else '<b>Если хоть одно условие не выполнено - остаться.</b> Последний защитник не уходит. Слабый запасной марш не заменяет защиту против сильного врага рядом. Если уходят двое, заранее договориться, кто остается. Прямая команда ДЕРЖАТЬ действует до отмены.')
    story.append(table(['Ситуация' if ru else 'Situation','Что делать' if ru else 'Action'],[
      ['C / D, T+15','LadyGroz + Filin: Dev; Martyku + Bruklin88: Munitions. Move as soon as the three checks pass.' if not ru else 'LadyGroz + Filin: комплекс; Martyku + Bruklin88: военный. Идти сразу после трех проверок.'],
      ['P1-P4','Support player collects nearby water while the named main defender stays. Return when the building is threatened.' if not ru else 'Помощник собирает воду рядом, основной защитник остается. Вернуться при угрозе зданию.'],
      ['G','Collect safe water immediately. If there is none, help or scout your sector. Report enemy activity.' if not ru else 'Собирать безопасную воду сразу. Нет воды - помощь или разведка своего сектора. Докладывать врага.'],
      ['S','Help the nearby threatened assigned objective. At T+15, move to Central unless a direct order changes the target. Keep capture attacks together.' if not ru else 'Помогать ближайшей назначенной точке под угрозой. T+15 - центр, если нет другой прямой команды. Атаковать для захвата вместе.'],
    ],[31,151]))
    h('S acts independently' if not ru else 'S действует самостоятельно')
    body('ChaosGoblin leads S; Artur leads its attacks. S chooses where to reinforce, escort collectors or attack a weak enemy point without waiting for HQ. Before T+15, help Solar/Helipad and threatened Treatment Centers. At T+15, take Central together unless HQ changes that target. Once held, keep ChaosGoblin or an agreed strong replacement inside; the other S marches respond where needed. S sets its own rally/arrival time and tells the team. Do not scatter into separate attacks against strong defense.' if not ru else 'ChaosGoblin ведет S; Artur ведет атаки. S сама выбирает подкрепление, прикрытие сбора или атаку слабой точки без ожидания HQ. До T+15 помогать солнечной/площадке и центрам под угрозой. T+15 - совместно взять центр, если HQ не меняет цель. После захвата внутри остается ChaosGoblin или согласованная сильная замена; остальные S помогают там, где нужно. S сама задает время ралли/прибытия и сообщает команде. Не разделяться на одиночные атаки сильной защиты.')
    h('Power-based allocation' if not ru else 'Распределение по силе')
    body('S concentrates four high-power marches (12.80-14.93M). Salman/Loki anchor Treatment 1/2. LadyGroz/Martyku lead the later utility captures. Lower-power players have active collection, reinforcement and scouting duties. Power is an allocation proxy: hero skills, formation, march capacity and rally bonuses must be checked by the squad leads.' if not ru else 'S объединяет четыре сильных марша (12.80-14.93M). Salman/Loki держат центры 1/2. LadyGroz/Martyku ведут захват объектов второго этапа. Игроки меньшей силы собирают, усиливают и разведывают. Сила - ориентир: лидеры проверяют навыки героев, формацию, вместимость и бонусы ралли.')
    body('T+0 is the start of preparation: battle opens T+3. If your screen counts from combat start, use 12 minutes to Central and 22/32/42 minutes to tank waves. Follow the live countdown if it differs.' if not ru else 'T+0 - начало подготовки: бой открывается T+3. Если экран считает от начала боя, до центра 12 минут, до волн сбора 22/32/42. При расхождении следовать таймеру игры.')
    page()
    title('Isometric map and player names' if not ru else 'Изометрическая карта и игроки')
    body('Building icons use the same client coordinates and isometric projection as the earlier map. Lines connect each name card to its building. C/D names appear twice because those players have two successive jobs.' if not ru else 'Иконки стоят по координатам клиента и изометрии прежней карты. Линия связывает список игроков со зданием. Имена C/D указаны дважды: у этих игроков две последовательные задачи.')
    story.append(Map(ru))
    story.append(Spacer(1,7))
    body('Blue dashed circles: possible tank-wave areas. They do not mark splashed water. Splashed water appears around a building that changes hands. S starts by helping Solar/Helipad, then goes to Central at T+15. Blockbuster joins S when she enters, unless she must replace a missing main defender.' if not ru else 'Синие пунктирные круги: возможные районы волн сбора. Они не обозначают разлитую воду. Разлитая вода появляется у захваченного здания. S сначала помогает солнечной/площадке, затем идет в центр T+15. Blockbuster после входа идет в S, если не нужна замена основного защитника.')
    body('<b>G:</b> 4uzhaya - NW; Xaroth - NE; Yesimemily - SW; Bulik - SE. <b>HQ:</b> TheShadowWZYE commands and helps the nearest safe point. Use live map pins to identify the exact water pool.' if not ru else '<b>G:</b> 4uzhaya - СЗ; Xaroth - СВ; Yesimemily - ЮЗ; Bulik - ЮВ. <b>HQ:</b> TheShadowWZYE командует и помогает ближайшей безопасной точке. Конкретную лужу указывать меткой игры.')
    page()
    title('Complete starter allocation' if not ru else 'Все основные участники')
    body('Names are copied from the screenshots; power is Highest Team Power in millions. First listed member leads each group, except G (4uzhaya coordinates collection) and HQ. Each starter appears exactly once. Roles below refer to the main march.' if not ru else 'Ники переписаны со скриншотов; сила - Highest Team Power в миллионах. Первый в списке ведет группу; в G сбор координирует 4uzhaya. Каждый основной участник указан один раз. Ниже задачи основного марша.')
    rows=[]
    for g in groups:
        code,members,en,rus,open_en,open_ru,next_en,next_ru=g
        names='<br/>'.join(f'{escape(n)} <b>{v:.2f}M</b>' for n,v in members)
        rows.append([f'<b>{code}</b><br/>{rus if ru else en}',names,(open_ru if ru else open_en)+'<br/><b>'+('Далее:' if ru else 'Next:')+'</b> '+(next_ru if ru else next_en)])
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
      ('T+12-14','C/D check who stays and whether cover is safe. S scouts Central and regroups. Main Treatment defenders stay.','C/D проверяют, кто остается и хватает ли защиты. S разведывает центр и собирается. Основные защитники водоочистки остаются.'),
      ('T+15','S: Central; C: Dev; D: Munitions. Move when safe and covered; post the move without waiting for HQ.','S: центр; C: комплекс; D: военный. Идти при безопасном прикрытии; сообщить, не ждать HQ.'),
      ('T+23/33/43','G scouts its sectors. P supports may join collection when their main defender is safe.','G проверяет сектора. Помощники P идут на сбор, если основной защитник в безопасности.'),
      ('T+25/35/45','Tank waves: 3 / 3 / 4 spawns. G calls actual locations and gathers.','Волны: 3 / 3 / 4 точки. G сообщает реальные места и собирает.'),
      ('Any / Всегда','Collect safe splashed water around a captured building. Do not wait for a tank wave or HQ call.','Собирать безопасную разлитую воду у захваченного здания. Не ждать волны или команды HQ.'),
      ('T+50-60','Protect income; timed flips only if score recovery requires them. Scoring ends T+60.','Защищать доход; захваты по времени при отставании. Подсчет заканчивается T+60.'),
    ]
    story.append(table(['Время' if ru else 'Time','Действия R4' if ru else 'R4 action'],[[a,c if ru else b] for a,b,c in timeline],[29,153]))
    page()
    title('R4 orders during the fight' if not ru else 'Команды R4 в бою')
    commands=[
      ('HOLD / ДЕРЖАТЬ','Hold the named main-march garrison. Reinforce; no rotation until a replacement confirms arrival.','Держать названный гарнизон основным маршем. Усиливать; не уходить до прибытия замены.'),
      ('RELIEF / СМЕНА','Agree who stays. Check that their march is actually inside and strong enough. Then move to the next assigned job and report. HQ approval is not needed.','Договориться, кто остается. Проверить, что его марш внутри и достаточно силен. Затем идти на следующую задачу и сообщить. Разрешение HQ не нужно.'),
      ('RALLY / РАЛЛИ','Name leader, target, joiners and launch time. Joiners confirm march availability. Check rally capacity/bonuses; highest power alone is not proof of best rally lead.','Назвать лидера, цель, участников и время запуска. Участники подтверждают марш. Проверить лимит/бонусы; сила сама по себе не доказывает лучший выбор лидера.'),
      ('HIT / УДАР','For a planned attack wave, specify arrival time, not merely launch time. Hit a defended point only with adequate support.','Для общей атаки задавать время прибытия, а не только отправки. Защищенную точку атаковать с достаточной поддержкой.'),
      ('REINFORCE / УСИЛИТЬ','Name target and players. Send best available useful march; check capacity. After taking a point, establish the anchor and fill defense.','Назвать цель и игроков. Отправить лучший полезный доступный марш, проверить лимит. После захвата поставить якорь и заполнить защиту.'),
      ('TANK / СБОР','Give the water pin. Nearby G or safe support goes immediately. If enemies are stronger, request cover. No water nearby: reinforce or scout.','Дать метку воды. Ближайший G или свободный помощник идет сразу. Враг сильнее - запросить прикрытие. Нет воды рядом - помощь или разведка.'),
      ('RESET / ПЕРЕСБОР','Recall, heal and regroup at the named location. Stop isolated repeat attacks.','Вернуть войска, вылечить и собраться у названной метки. Прекратить одиночные повторные атаки.'),
    ]
    story.append(table(['Команда' if ru else 'Call','Действие' if ru else 'Action'],[[a,c if ru else b] for a,b,c in commands],[36,146]))
    h('Decision rules for the commander' if not ru else 'Решения командира')
    body('<b>Central heavily defended:</b> scout first. Keep A/B income; establish Munitions/Dev if feasible, then rally with S and released supports. Do not empty both Treatment Centers. If capture remains unrealistic, defend the two Treatments, utility buffs and viable Plants, and contest tanks.' if not ru else '<b>Центр сильно защищен:</b> сначала разведка. Сохранить доход A/B; по возможности взять военный/комплекс, затем ралли S с освобожденной поддержкой. Не опустошать оба центра. Если захват нереален, держать два центра, полезные объекты и доступные заводы, бороться за сбор.')
    body('<b>Utility relief too weak:</b> keep the original anchor until support arrives; postpone Dev/Munitions rotation. <b>Two rallies incoming:</b> prioritize the higher-value vulnerable objective and call reinforcements before impact. <b>Behind:</b> arrange two concurrent pressure targets; strike where reports show weaker defense. <b>Ahead:</b> keep major income stable and intercept tank collectors.' if not ru else '<b>Смена на полезном объекте слаба:</b> оставить якорь до помощи; отложить переход к комплексу/военному. <b>Два ралли врага:</b> сначала усилить более доходную уязвимую цель до удара. <b>Отстаем:</b> давить две цели одновременно; бить туда, где разведка показывает слабую защиту. <b>Ведем:</b> держать основной доход и перехватывать сборщиков.')
    body('Report: TARGET - STATUS - ENEMIES - ARRIVAL TIME - HELP. Example: Treatment 2 - held - 4 enemy marches - rally in 00:40 - need 2 S players. Move report: LadyGroz + Filin to Dev; Wróżka stays at Solar. Follow the plan without asking when safe. S chooses and times its own fights. HQ changes the overall plan and coordinates attacks involving several groups. If HQ disconnects, the agreed backup Artur takes calls.' if not ru else 'Доклад: ЦЕЛЬ - СТАТУС - ВРАГИ - ПРИБЫТИЕ - ПОМОЩЬ. Пример: центр 2 - держим - 4 марша врага - ралли через 00:40 - нужны двое S. Переход: LadyGroz + Filin в комплекс; Wróżka остается на солнечной. Безопасный переход по плану - без разрешения. S сама выбирает атаки и время. HQ меняет общий план и согласует атаки нескольких групп. При отключении HQ команды принимает согласованный заместитель Artur.')
    page()
    title('Splashed water: what to do' if not ru else 'Разлитая вода: что делать')
    body('<b>Splashed water is water on the ground around a building that has been taken from its defenders.</b> The game calls it a Pool of Water. Both alliances can recover it. Capturing the building does not automatically give you all the water on the ground.' if not ru else '<b>Разлитая вода лежит вокруг здания, отбитого у защитников.</b> В игре это лужа воды (Pool of Water). Ее могут подобрать оба альянса. Захват здания не дает вам автоматически всю воду на земле.')
    h('Why it appears' if not ru else 'Почему она появляется')
    body('While a building is held, it keeps producing water. Some accumulated water can exceed its storage capacity. The game help says this excess counts for the defender at the end if they keep the building. If the enemy takes the building, the excess scatters nearby and either side can send troops to recover it for points. A recently held building may have little or no excess to drop.' if not ru else 'Удерживаемое здание производит воду. Накопленная вода может превысить вместимость. По справке игры этот избыток засчитывается защитнику в конце, если здание удержано. Если здание берет враг, избыток разливается рядом: войска обеих сторон могут подобрать его ради очков. Недавно занятое здание может почти ничего не сбросить.')
    h('After any building changes hands' if not ru else 'После любого перехода здания')
    spillsteps=[
      ('1','Look around the building immediately. Check the capture/loss notice and the live map for pools. Post a pin if you see water.','Сразу осмотреть здание. Проверить сообщение о захвате/потере и лужи на карте. Если есть вода - дать метку.'),
      ('2','The nearest G player collects first. A nearby support can also collect if their main defender is safely covered. No HQ approval is needed.','Ближайший игрок G идет на сбор. Помощник рядом тоже может собирать, если основной защитник в безопасности. Разрешение HQ не нужно.'),
      ('3','Select the actual pool and use its pickup/collection action. Send an available march as the game requires. Send different players to different pools.','Выбрать саму лужу и действие подбора/сбора. Отправить свободный марш по требованию игры. Разным игрокам брать разные лужи.'),
      ('4','Combat players keep the building and protect collectors. Do not pull the last defender out to collect. If the enemy is stronger, ask for cover or collect a safer pool.','Бойцы держат здание и прикрывают сборщиков. Последний защитник ради сбора не уходит. Враг сильнее - запросить прикрытие или взять безопасную лужу.'),
      ('5','If our building was lost, recover safe pools too: the water is available to both sides. Do not send repeated solo attacks to reach an unsafe pool.','Если потеряли наше здание, тоже собирать безопасные лужи: вода доступна обеим сторонам. Не повторять одиночные атаки ради опасной лужи.'),
      ('6','Once the nearby pools are gone, return to your next assigned job. Report that the area is clear. Do not wait there for the next tank wave.','Лужи рядом закончились - вернуться к следующей назначенной задаче. Сообщить, что вода собрана. Не ждать там следующую волну.'),
    ]
    story.append(table(['Шаг' if ru else 'Step','Действие' if ru else 'Action'],[[a,c if ru else b] for a,b,c in spillsteps],[18,164]))
    h('Do not confuse the two types of water' if not ru else 'Не путать два вида воды')
    story.append(table(['Вид' if ru else 'Type','Где и когда' if ru else 'Where and when'],[
      ['Splashed water / Разлитая вода','Around a building after it is taken from its defenders. Collect whenever it appears. No fixed wave time.' if not ru else 'У здания после захвата у защитников. Собирать при появлении. Фиксированного времени волны нет.'],
      ['Water Tanks / Водосборники','Scheduled waves T+25/35/45 in the blue dashed areas. Actual positions vary; check live pins.' if not ru else 'Волны T+25/35/45 в синих пунктирных районах. Точное место меняется; проверять метки.'],
    ],[53,129]))
    body('<b>Example:</b> Treatment 1 changes hands. Yesimemily goes to any safe pools there. CaptMac or Shikiiigami may help collect if their building is safely covered. The fighting marches keep the new garrison and protect collectors. If we lost Treatment 1, the same safe-pickup rule applies while the combat team prepares its next attack.' if not ru else '<b>Пример:</b> центр 1 сменил владельца. Yesimemily идет к безопасным лужам рядом. CaptMac или Shikiiigami помогают собирать, если их здание прикрыто. Боевые марши держат новый гарнизон и защищают сборщиков. Если центр 1 потеряли мы, безопасную воду тоже подбирать, пока бойцы готовят следующую атаку.')
    body('No fixed spill percentage, expiry timer or pickup formula is assumed here. The client help confirms the trigger and that both sides can recover water; it does not fully explain the overflow calculation. Use the amount and pickup action shown in the live game.' if not ru else 'Здесь не задаются фиксированный процент разлива, время исчезновения или формула подбора. Справка подтверждает причину и доступ обеим сторонам, но не объясняет полный расчет избытка. Использовать количество и действие, показанные в игре.')
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
    body('Roster: 18 supplied screenshots; green starters/yellow substitutes confirmed in chat. Mechanics: local Tiles Survive client snapshot 2.6.100.261, AvaPhase, AvaBuildings, AvaMineCollection and English help. Spill rules: ava_guide_rob_rules_1/2 and ava_scatter_water_name, re-read 4 Oct 2026. Isometric map: AvaBuildings coordinates, original extracted artwork, checked against the supplied Discord map. Current in-game countdown and tooltips take precedence over this client snapshot.' if not ru else 'Состав: 18 скриншотов; зеленые основные/желтые запасные подтверждены в чате. Правила: снимок клиента Tiles Survive 2.6.100.261, AvaPhase, AvaBuildings, AvaMineCollection и справка. Разлив: ava_guide_rob_rules_1/2 и ava_scatter_water_name, перечитаны 04.10.2026. Изометрия: координаты AvaBuildings и извлеченные иконки, проверка по карте Discord. Текущий таймер и подсказки игры важнее этого снимка клиента.')
    body('R4 confirms live attendance, main-march readiness, leader rally capacity and spawn-side access. Strategy and assignments are proposed orders based on the supplied power; no enemy roster or attendance forecast was supplied. Scout and adjust before committing across the map.' if not ru else 'R4 проверяет явку, готовность основных маршей, лимит ралли лидеров и доступ со стороны появления. Назначения - предлагаемые команды по указанной силе; состав врага и прогноз явки не предоставлены. До перехода через карту разведать и скорректировать.')

def footer(c,doc):
    c.setStrokeColor(colors.HexColor('#C4D0DA'));c.line(14*mm,13*mm,196*mm,13*mm)
    c.setFont('Body',8);c.setFillColor(INK);c.drawString(14*mm,8*mm,'[VeD] RR | EN / RU | 2026-10-04');c.drawRightString(196*mm,8*mm,str(doc.page))
doc=SimpleDocTemplate(str(args.output),pagesize=A4,leftMargin=14*mm,rightMargin=14*mm,topMargin=13*mm,bottomMargin=18*mm,title='VeD Reservoir Raid Battle Plan - English and Russian',author='Alliance command planning')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
args.output.with_suffix('.txt').write_text('EN ('+str(len(chat_en))+' characters)\n'+chat_en+'\n\nRU ('+str(len(chat_ru))+' characters)\n'+chat_ru+'\n',encoding='utf-8')
print(json.dumps({'pdf':str(args.output),'starters':len(players),'reserves':len(reserves),'starter_power_M':round(sum(v for _,v in players),2),'EN_characters':len(chat_en),'RU_characters':len(chat_ru)},ensure_ascii=False))
