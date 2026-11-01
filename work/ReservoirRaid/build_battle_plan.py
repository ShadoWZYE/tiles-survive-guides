"""Build the combined EN/RU VeD Reservoir Raid command plan.
Run with Python and reportlab. Output path is configurable; assets are optional.
"""
from pathlib import Path
import argparse
import json
from html import escape
import arabic_reshaper
from bidi.algorithm import get_display

def display(text):
    return text.replace("الفدرالي", get_display(arabic_reshaper.reshape("الفدرالي")))
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
def p(text,style='body'): return Paragraph(display(text),ST[style])
ST['roster']=ParagraphStyle('roster',parent=ST['cell'],fontSize=8,leading=10)
def table(headers,rows,widths,compact=False):
    data=[[p(x,'head') for x in headers]]+[[p(str(x),'roster' if compact else 'cell') for x in r] for r in rows]
    t=Table(data,colWidths=[v*mm for v in widths],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#C4D0DA')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    if compact: t.setStyle(TableStyle([('TOPPADDING',(0,1),(-1,-1),4),('BOTTOMPADDING',(0,1),(-1,-1),4)]))
    return t

# Green participant and yellow reserve selections read from the 1 November screenshots.
groups=[
 ('S',[('Addalicious',56.40),('ChaosGoblin',24.43),('Paradise flower',27.98),('подвальная мышь',24.00)],
  'Strike / central','Ударная / центр',
  'Addalicious + Paradise flower help Solar; ChaosGoblin + подвальная мышь help Helipad. After capture, respond to contested treatment centers.',
  'Addalicious + Paradise flower помогают на солнечной; ChaosGoblin + подвальная мышь - на площадке. После захвата помогают центрам под атакой.',
  'T+15: Central unless HQ changes the plan. Addalicious holds it; ChaosGoblin leads attacks. Others choose help, escort or attacks themselves. Keep Central covered.',
  'T+15: центр, если HQ не меняет план. Addalicious держит; ChaosGoblin ведет атаки. Остальные сами выбирают помощь, прикрытие или атаки. Сохранить защиту центра.'),
 ('A',[('Yildiz',21.02),('LadyGroz',19.31),('Lamga',21.40),('Shikiiigami',16.65)],'Treatment 1 / SW','Центр 1 / ЮЗ',
  'Yildiz anchors Treatment 1; LadyGroz reports; Lamga and Shikiiigami reinforce. Shikiiigami may help Plant 1 when Treatment 1 is safe.',
  'Yildiz держит центр 1; LadyGroz докладывает; Lamga и Shikiiigami усиливают. Shikiiigami помогает заводу 1, если центр 1 в безопасности.',
  'Keep a strong Treatment 1 anchor. Supports may cover Plant 1 or collect nearby water when safe; report the move.', 'Сохранить сильный гарнизон центра 1. Помощники идут на завод 1 или сбор рядом, если безопасно; сообщить переход.'),
 ('B',[('Sattow',29.72),('ryan',16.37),('Azrael',15.20)],'Treatment 2 / NE','Центр 2 / СВ',
  'Sattow anchors Treatment 2; ryan reinforces and reports; Azrael reinforces / scouts Plant 2.',
  'Sattow держит центр 2; ryan усиливает и докладывает; Azrael усиливает / следит за заводом 2.',
  'Keep a strong Treatment 2 anchor. Supports may cover Plant 2 or collect nearby water when safe; report the move.', 'Сохранить сильный гарнизон центра 2. Помощники идут на завод 2 или сбор рядом, если безопасно; сообщить переход.'),
 ('C',[('Martyku',20.55),('creative',20.64),('Баламут',15.68)],'Solar / NW','Солнечная / СЗ',
  'Martyku captures/anchors Solar; creative supports; Баламут scouts and prepares to hold.',
  'Martyku захватывает солнечную; creative помогает; Баламут разведывает и готовится держать.',
  'T+15: Martyku + creative move to Dev once Баламут is holding Solar safely. No HQ approval needed. If unsafe, keep cover and report.',
  'T+15: Martyku + creative идут в комплекс, когда Баламут безопасно держит солнечную. Разрешение HQ не нужно. При угрозе сохранить защиту и доложить.'),
 ('D',[('MenInPantyhose',16.55),('Bruklin88',15.33),('Пятница',16.77)],'Helipad / SE','Площадка / ЮВ',
  'MenInPantyhose captures/anchors Helipad; Bruklin88 supports; Пятница scouts and prepares to hold.',
  'MenInPantyhose захватывает площадку; Bruklin88 помогает; Пятница разведывает и готовится держать.',
  'T+15: MenInPantyhose + Bruklin88 move to Munitions once Пятница holds Helipad safely. No HQ approval needed. Report strong opposition.',
  'T+15: MenInPantyhose + Bruklin88 идут на военный, когда Пятница безопасно держит площадку. Разрешение HQ не нужно. Доложить сильное сопротивление.'),
 ('P1',[('Peacheybites!',15.81),('Filin',12.85)],'Plant 1 / SW','Завод 1 / ЮЗ',
  'Peacheybites! anchors Plant 1; Filin reinforces and watches the SW approach.',
  'Peacheybites! держит завод 1; Filin усиливает и следит за подходом с ЮЗ.',
  'Peacheybites! holds; Filin may collect SW tanks/spills when the anchor is safe. Report and go; return if threatened.',
  'Peacheybites! держит; Filin собирает точки/разлитую воду на ЮЗ при безопасном гарнизоне. Сообщить и идти; вернуться при угрозе.'),
 ('P2',[('HoloCrow',15.81),('Sukuna',14.41)],'Plant 2 / NE','Завод 2 / СВ',
  'HoloCrow anchors Plant 2; Sukuna reinforces and watches the NE approach.',
  'HoloCrow держит завод 2; Sukuna усиливает и следит за подходом с СВ.',
  'HoloCrow holds; Sukuna may collect NE tanks/spills when safe. Report and go; return if threatened.',
  'HoloCrow держит; Sukuna собирает точки/разлитую воду на СВ, если безопасно. Сообщить и идти; вернуться при угрозе.'),
 ('P3',[('Александр',13.99),('M1K3.Marius',12.40)],'Plant 3 / NW','Завод 3 / СЗ',
  'Александр anchors Plant 3; M1K3.Marius reinforces and watches the NW approach.',
  'Александр держит завод 3; M1K3.Marius усиливает и следит за подходом с СЗ.',
  'Александр holds; M1K3.Marius may collect NW tanks/spills when safe. Report and go; return if threatened.',
  'Александр держит; M1K3.Marius собирает точки/разлитую воду на СЗ, если безопасно. Сообщить и идти; вернуться при угрозе.'),
 ('P4',[('Wild berry777',13.44),('الفدرالي',10.88)],'Plant 4 / SE','Завод 4 / ЮВ',
  'Wild berry777 anchors Plant 4; الفدرالي reinforces and watches the SE approach.',
  'Wild berry777 держит завод 4; الفدرالي усиливает и следит за подходом с ЮВ.',
  'Wild berry777 holds; الفدرالي may collect SE tanks/spills when safe. Report and go; return if threatened.',
  'Wild berry777 держит; الفدرالي собирает точки/разлитую воду на ЮВ, если безопасно. Сообщить и идти; вернуться при угрозе.'),
 ('G',[('Lunar',10.31),('nikkita',9.35),('Золото Мира',9.69),('black beard',10.49)],'Collection / support','Сбор / поддержка',
  'Lunar: NW/Solar; nikkita: NE/Treatment 2; Золото Мира: SW/Treatment 1; black beard: SE/Helipad. Reinforce and scout before tanks.',
  'Lunar: СЗ/солнечная; nikkita: СВ/центр 2; Золото Мира: ЮЗ/центр 1; black beard: ЮВ/площадка. До волн - помощь и разведка.',
  'Collect nearby spills immediately when safe, at any time. T+25/35/45: gather tank waves. No water: reinforce/scout. Report moves and enemy collectors.',
  'Безопасную разлитую воду собирать сразу в любое время. T+25/35/45: волны сбора. Нет воды - помощь/разведка. Докладывать переходы и сборщиков врага.'),
 ('HQ',[('TheShadoWZYE',12.00)],'Commander','Командир',
  'Lead calls, count attendance, track score and incoming rallies. Support the nearest safe objective with main march.',
  'Команды, явка, счет и ралли врага. Основной марш - помощь ближайшему безопасному объекту.',
  'Keep command visibility. Coordinate S and substitutes. Confirmed second-in-command: Shikiiigami. They take command if HQ is unavailable.',
  'Контролировать карту, S и запасных. Согласованный заместитель: Shikiiigami. При отсутствии HQ принимает командование.'),
]

reserves=[('Artur', 22.92, '1', 'Cover the missing role on HQ call; readiness and role fit take priority.', 'Заменить отсутствующего по вызову HQ; готовность и роль важнее силы.'), ('IBRAHIM Zain', 11.93, '2', 'Cover the missing role on HQ call; readiness and role fit take priority.', 'Заменить отсутствующего по вызову HQ; готовность и роль важнее силы.'), ('Bulik', 10, '3', 'Cover the missing role on HQ call; readiness and role fit take priority.', 'Заменить отсутствующего по вызову HQ; готовность и роль важнее силы.'), ('Cass', 7.54, '4', 'Cover the missing role on HQ call; readiness and role fit take priority.', 'Заменить отсутствующего по вызову HQ; готовность и роль важнее силы.'), ('GRANDAL', 5.41, '5', 'Cover the missing role on HQ call; readiness and role fit take priority.', 'Заменить отсутствующего по вызову HQ; готовность и роль важнее силы.')]

chat_en='[VeD] RR 1 Nov\nHQ TheShadoWZYE; 2IC Shikiiigami\n\nS Addalicious/ChaosGoblin/Paradise flower/подвальная мышь: help, Central T+15\nA Yildiz/LadyGroz/Lamga/Shikiiigami: Treatment 1\nB Sattow/ryan/Azrael: Treatment 2\nC Martyku/creative/Баламут: Solar; first two to Dev T+15, Баламут stays\nD MenInPantyhose/Bruklin88/Пятница: Helipad; first two to Munitions T+15, Пятница stays\nP1 Peacheybites!/Filin\nP2 HoloCrow/Sukuna\nP3 Александр/M1K3.Marius\nP4 Wild berry777/الفدرالي\nG Lunar NW, nikkita NE, Золото Мира SW, black beard SE: safe spills now; tanks T+25/35/45\n\nFirst named holds. Move with safe cover; report. Heal.\n\nReserves: Artur/IBRAHIM Zain/Bulik/Cass/GRANDAL\nEnter on HQ call when entry opens and a seat is free.\nT from preparation; live countdown wins.'
chat_ru='[VeD] RR 01.11\nHQ TheShadoWZYE; зам Shikiiigami\n\nS Addalicious/ChaosGoblin/Paradise flower/подвальная мышь: помощь, центр T+15\nA Yildiz/LadyGroz/Lamga/Shikiiigami: центр 1\nB Sattow/ryan/Azrael: центр 2\nC Martyku/creative/Баламут: солнечная; первые двое в комплекс T+15, Баламут остается\nD MenInPantyhose/Bruklin88/Пятница: площадка; первые двое на военный T+15, Пятница остается\nP1 Peacheybites!/Filin\nP2 HoloCrow/Sukuna\nP3 Александр/M1K3.Marius\nP4 Wild berry777/الفدرالي\nG Lunar СЗ, nikkita СВ, Золото Мира ЮЗ, black beard ЮВ: лужи сразу; волны T+25/35/45\n\nПервый держит. Переходить при прикрытии; сообщать. Лечить.\n\nЗапас: Artur/IBRAHIM Zain/Bulik/Cass/GRANDAL\nВход по HQ, когда открыт и есть место.\nT от подготовки; таймер игры важнее.'
assert len(chat_en)<=1000 and len(chat_ru)<=1000
players=[x for g in groups for x in g[1]]
assert len(players)==30 and len(set(n for n,_ in players))==30
assert round(sum(v for _,v in players),2)==539.43
assert len(reserves)==5 and not set(n for n,_ in players)&set(r[0] for r in reserves)

class Map(Flowable):
    def __init__(self,ru): Flowable.__init__(self); self.width=W; self.height=178*mm; self.ru=ru
    def draw(self):
        c=self.canv
        c.setFillColor(colors.HexColor('#F2E6D3'));c.roundRect(0,0,W,self.height,8,fill=1,stroke=0)
        def project(x,y): return (91+.65*(x-y))*mm,(16+.65*(x+y-142))*mm
        # Same client coordinates and isometric x-y / x+y projection as the earlier map.
        nodes=[
          ('factory',138,195,'P3: Завод 3' if self.ru else 'P3: Plant 3',['Александр / M1K3.Marius'],34,150,44),
          ('powerstation',100,200,'C: Солнечная' if self.ru else 'C: Solar',['Martyku / creative','Баламут'],4,91,43),
          ('zombie',119,162,'C: Комплекс T+15' if self.ru else 'C: Dev T+15',['Martyku / creative'],50,85,44),
          ('process_center',56,105,'A: Центр 1' if self.ru else 'A: Treatment 1',['Yildiz / LadyGroz','Lamga / Shikiiigami'],45,1,50),
          ('factory',33,119,'P1: Завод 1' if self.ru else 'P1: Plant 1',['Peacheybites! / Filin'],4,35,43),
          ('factory',205,119,'P2: Завод 2' if self.ru else 'P2: Plant 2',['HoloCrow / Sukuna'],129,146,50),
          ('process_center',181,132,'B: Центр 2' if self.ru else 'B: Treatment 2',['Sattow / ryan / Azrael'],103,101,47),
          ('tank',119,76,'D: Военный T+15' if self.ru else 'D: Munitions T+15',['MenInPantyhose / Bruklin88'],102,62,40),
          ('airport',138,37,'D: Площадка' if self.ru else 'D: Helipad',['MenInPantyhose / Bruklin88','Пятница'],144,47,35),
          ('factory',100,42,'P4: Завод 4' if self.ru else 'P4: Plant 4',['Wild berry777 / الفدرالي'],137,6,43),
          ('center',117,117,'S: Центр T+15' if self.ru else 'S: Central T+15',['Addalicious / ChaosGoblin','Paradise flower / подвальная мышь'],51,51,48),
        ]
        c.setStrokeColor(colors.HexColor('#007C9D'));c.setLineWidth(1);c.setDash(3,2)
        for x,y in [(86,150),(86,90),(154,150),(154,90)]:
            px,py=project(x,y);c.circle(px,py,6*mm,fill=0,stroke=1)
        c.setDash()
        c.setFillColor(colors.HexColor('#006B85'));c.setFont('Bold',7.2)
        for x,y,name,offset in [(86,150,'Lunar',-9),(86,90,'Золото Мира',-9),(154,150,'nikkita',9),(154,90,'black beard',9)]:
            px,py=project(x,y);c.drawCentredString(px,py+offset*mm,name)
        for kind,x,y,label,names,bx,by,bw in nodes:
            px,py=project(x,y)
            bh=8+4*len(names)
            # Short connectors terminate at the nearest label edge.
            ax=max(bx*mm,min(px,(bx+bw)*mm))
            ay=max(by*mm,min(py,(by+bh)*mm))
            c.setStrokeColor(colors.HexColor('#AA9475'));c.setLineWidth(.45);c.line(ax,ay,px,py)
        for kind,x,y,label,names,bx,by,bw in nodes:
            px,py=project(x,y)
            asset=Path(__file__).parent/'assets'/f'sp_icon_big_ava_building_{kind}.png'
            c.drawImage(ImageReader(str(asset)),px-8*mm,py-8*mm,16*mm,16*mm,mask='auto',preserveAspectRatio=True)
            bh=8+4*len(names)
            c.saveState();c.setFillAlpha(.80);c.setStrokeAlpha(.30)
            c.setFillColor(colors.white);c.setStrokeColor(colors.HexColor('#AE9F89'));c.setLineWidth(.4)
            c.roundRect(bx*mm,by*mm,bw*mm,bh*mm,3,fill=1,stroke=1);c.restoreState()
            c.setFillColor(NAVY);c.setFont('Bold',7.6);c.drawString((bx+2)*mm,(by+bh-4.5)*mm,label)
            c.setFont('Body',7.1)
            for i,name in enumerate(names):
                name=display(name)
                size=7.1
                while pdfmetrics.stringWidth(name,'Body',size)>(bw-4)*mm: size-=.1
                c.setFont('Body',size)
                c.drawString((bx+2)*mm,(by+bh-8.5-i*4)*mm,name)

story=[]
def title(x): story.append(p(x,'title'))
def h(x): story.append(p(x,'h'))
def body(x):
    x=x.replace('the agreed backup ChaosGoblin takes calls', 'the confirmed second-in-command Shikiiigami takes command')
    x=x.replace('согласованный заместитель ChaosGoblin', 'согласованный заместитель Shikiiigami')
    story.append(p(x))
def page(): story.append(PageBreak())
for ru in (False,True):
    if ru: page()
    title('[VeD] Reservoir Raid' if not ru else '[VeD] Рейд на резервуар')
    body('R4 command plan | 1 November 2026 | English version' if not ru else 'План командования R4 | 1 ноября 2026 | Русская версия')
    body('<b>Commander: TheShadoWZYE. 30 starters + 5 registered substitutes.</b> Allocate the strongest available march by the roster below. Group labels remain the same in both languages.' if not ru else '<b>Командир: TheShadoWZYE. 30 основных + 5 зарегистрированных запасных.</b> Использовать сильнейший доступный марш по распределению ниже. Обозначения групп одинаковы в обоих языках.')
    body('<b>Second-in-command (2IC): Shikiiigami - confirmed.</b> Takes command if TheShadoWZYE is unavailable. Otherwise keeps the assigned Treatment 1 support role.' if not ru else '<b>Заместитель командира (2IC): Shikiiigami - согласовано.</b> Принимает командование, если TheShadoWZYE недоступен. В остальное время помогает центру 1 по плану.')
    h('Battle objective and opening' if not ru else 'Цель боя и старт')
    body('Win by Alliance Water. A/B hold both Treatment Centers; P1-P4 capture or probe their Plants; C/D take Solar/Helipad with S support. Empty objectives: capture immediately. A defended objective stronger than your pair: report, preserve troops and request a coordinated attack. R4 may concede a remote Plant to protect the major income buildings.' if not ru else 'Победа определяется союзной водой. A/B держат оба центра; P1-P4 берут или проверяют заводы; C/D берут солнечную/площадку с помощью S. Пустую точку брать сразу. Если защита сильнее вашей пары - доклад, сохранение войск и запрос общей атаки. R4 может отдать дальний завод ради основных доходных зданий.')
    h('When to move without asking' if not ru else 'Когда можно идти без разрешения')
    body('<b>Default rule: follow this plan unless HQ gives a different order.</b> You do not need a new command for each listed job. A/B protect their Treatment Centers; P1-P4 protect their Plants; C/D make their listed T+15 move when covered; G collects water and supports its sector. Other groups do not pick unrelated targets.' if not ru else '<b>Основное правило: выполнять этот план, пока HQ не даст другую команду.</b> Новая команда для каждой указанной задачи не нужна. A/B защищают центры; P1-P4 - заводы; C/D переходят по плану на T+15 при прикрытии; G собирает и помогает своему сектору. Другие группы не выбирают посторонние цели.')
    body('<b>Go to your next assigned job when all three checks pass:</b> the next objective is open; a teammate remains in the current garrison and can defend it; no enemy attack or rally is coming to that point. Check the actual garrison, not just a teammate standing nearby. Tell the squad who stays, then move and post your destination. You do not need a reply from HQ.' if not ru else '<b>Идите на следующую назначенную задачу, если выполнены три условия:</b> новая цель открыта; в текущем гарнизоне остается союзник, способный его защитить; на точку не идет атака или ралли врага. Проверяйте гарнизон, а не союзника рядом на карте. Скажите группе, кто остается; затем идите и напишите цель. Ответ HQ не нужен.')
    body('<b>Stay if any check fails.</b> Do not leave as the last defender. Do not count a weak spare march as enough cover against a stronger nearby enemy. If two players want to leave, agree who stays before either recalls. A direct HOLD order overrides the normal move rules until lifted.' if not ru else '<b>Если хоть одно условие не выполнено - остаться.</b> Последний защитник не уходит. Слабый запасной марш не заменяет защиту против сильного врага рядом. Если уходят двое, заранее договориться, кто остается. Прямая команда ДЕРЖАТЬ действует до отмены.')
    story.append(table(['Ситуация' if ru else 'Situation','Что делать' if ru else 'Action'],[
      ['C / D, T+15','Martyku + creative: Dev; MenInPantyhose + Bruklin88: Munitions. Move as soon as the three checks pass.' if not ru else 'Martyku + creative: комплекс; MenInPantyhose + Bruklin88: военный. Идти сразу после трех проверок.'],
      ['P1-P4','Support player collects nearby water while the named main defender stays. Return when the building is threatened.' if not ru else 'Помощник собирает воду рядом, основной защитник остается. Вернуться при угрозе зданию.'],
      ['G','Collect safe water immediately. If there is none, help or scout your sector. Report enemy activity.' if not ru else 'Собирать безопасную воду сразу. Нет воды - помощь или разведка своего сектора. Докладывать врага.'],
      ['S','Help the nearby threatened assigned objective. At T+15, move to Central unless a direct order changes the target. Keep capture attacks together.' if not ru else 'Помогать ближайшей назначенной точке под угрозой. T+15 - центр, если нет другой прямой команды. Атаковать для захвата вместе.'],
    ],[31,151]))
    h('S acts independently' if not ru else 'S действует самостоятельно')
    body('Addalicious leads S; ChaosGoblin leads its attacks. S chooses where to reinforce, escort collectors or attack a weak enemy point without waiting for HQ. Before T+15, help Solar/Helipad and threatened Treatment Centers. At T+15, take Central together unless HQ changes that target. Once held, keep Addalicious or an agreed strong replacement inside; the other S marches respond where needed. S sets its own rally/arrival time and tells the team. Do not scatter into separate attacks against strong defense.' if not ru else 'Addalicious ведет S; ChaosGoblin ведет атаки. S сама выбирает подкрепление, прикрытие сбора или атаку слабой точки без ожидания HQ. До T+15 помогать солнечной/площадке и центрам под угрозой. T+15 - совместно взять центр, если HQ не меняет цель. После захвата внутри остается Addalicious или согласованная сильная замена; остальные S помогают там, где нужно. S сама задает время ралли/прибытия и сообщает команде. Не разделяться на одиночные атаки сильной защиты.')
    h('Power-based allocation' if not ru else 'Распределение по силе')
    body('S concentrates four high-power marches (24.00-56.40M). Yildiz/Sattow anchor Treatment 1/2. Martyku/MenInPantyhose lead the later utility captures. Lower-power players have active collection, reinforcement and scouting duties. Power is an allocation proxy: hero skills, formation, march capacity and rally bonuses must be checked by the squad leads.' if not ru else 'S объединяет четыре сильных марша (24.00-56.40M). Yildiz/Sattow держат центры 1/2. Martyku/MenInPantyhose ведут захват объектов второго этапа. Игроки меньшей силы собирают, усиливают и разведывают. Сила - ориентир: лидеры проверяют навыки героев, формацию, вместимость и бонусы ралли.')
    body('T+0 is the start of preparation: battle opens T+3. If your screen counts from combat start, use 12 minutes to Central and 22/32/42 minutes to tank waves. Follow the live countdown if it differs.' if not ru else 'T+0 - начало подготовки: бой открывается T+3. Если экран считает от начала боя, до центра 12 минут, до волн сбора 22/32/42. При расхождении следовать таймеру игры.')
    page()
    title('Isometric map and player names' if not ru else 'Изометрическая карта и игроки')
    body('Building icons use the same client coordinates and isometric projection as the earlier map. Lines connect each name card to its building. C/D names appear twice because those players have two successive jobs.' if not ru else 'Иконки стоят по координатам клиента и изометрии прежней карты. Линия связывает список игроков со зданием. Имена C/D указаны дважды: у этих игроков две последовательные задачи.')
    story.append(Map(ru))
    story.append(Spacer(1,7))
    body('Blue dashed circles: possible tank-wave areas. They do not mark splashed water. Splashed water appears around a building that changes hands. S starts by helping Solar/Helipad, then goes to Central at T+15.' if not ru else 'Синие пунктирные круги: возможные районы волн сбора. Разлитая вода появляется у захваченного здания. S сначала помогает солнечной/площадке, затем идет в центр T+15.')
    body('<b>G:</b> Lunar - NW; nikkita - NE; Золото Мира - SW; black beard - SE. <b>HQ:</b> TheShadoWZYE commands and helps the nearest safe point. Use live map pins to identify the exact water pool.' if not ru else '<b>G:</b> Lunar - СЗ; nikkita - СВ; Золото Мира - ЮЗ; black beard - ЮВ. <b>HQ:</b> TheShadoWZYE командует и помогает ближайшей безопасной точке. Конкретную лужу указывать меткой игры.')
    page()
    title('Complete starter allocation' if not ru else 'Все основные участники')
    body('Names identify the selected screenshot rows; power is Highest Team Power in millions. First listed member leads each group, except G (Lunar coordinates collection) and HQ. Each starter appears exactly once. Roles below refer to the main march.' if not ru else 'Ники переписаны со скриншотов; сила - Highest Team Power в миллионах. Первый в списке ведет группу; в G сбор координирует Lunar. Каждый основной участник указан один раз. Ниже задачи основного марша.')
    rows=[]
    for g in groups:
        code,members,en,rus,open_en,open_ru,next_en,next_ru=g
        names='<br/>'.join(f'{escape(n)} <b>{v:.2f}M</b>' for n,v in members)
        rows.append([f'<b>{code}</b><br/>{rus if ru else en}',names,(open_ru if ru else open_en)+'<br/><b>'+('Далее:' if ru else 'Next:')+'</b> '+(next_ru if ru else next_en)])
    story.append(table(['Группа' if ru else 'Group','Игрок / сила' if ru else 'Player / power','Старт и последующие действия' if ru else 'Opening and later orders'],rows,[27,55,100],compact=True))
    page()
    title('Substitutes and battle clock' if not ru else 'Запасные и тайминг')
    body('30 starters and 5 registered reserves are assigned. Maximum 30 inside. HQ names the absent/departed starter and their replacement. Enter only when the live reserve-entry button is enabled and a seat is free; confirm in chat.' if not ru else 'Назначены 30 основных и 5 зарегистрированных запасных. Внутри максимум 30. HQ называет отсутствующего/вышедшего и его замену. Входить, когда кнопка входа запасного доступна и есть место; подтвердить в чате.')
    story.append(table(['Порядок' if ru else 'Priority','Запасной / сила' if ru else 'Substitute / power','Назначение при входе' if ru else 'Assignment on entry'],[[r[2],f'{escape(r[0])} <b>{r[1]:.2f}M</b>',r[4] if ru else r[3]] for r in reserves],[18,58,106]))
    body('The list is a default call order by displayed power, not a guaranteed entry queue. Choose a present reserve whose march fits the missing role. Keep major buildings covered.' if not ru else 'Список - предварительный порядок по указанной силе, а не обязательная очередь входа. Выбирать готового запасного под нужную роль. Сохранить защиту важных зданий.')

    body('If a high-power anchor is missing, move a suitable present support or S member to that anchor; the reserve covers the released support/collection role. Do not ask a 5-12M reserve to replace a 20-56M anchor solely because a seat opened.' if not ru else 'Если нет сильного защитника, перевести подходящего игрока поддержки или S на его место; запасной закрывает освободившуюся роль поддержки/сбора. Не ставить запасного 5-12M вместо защитника 20-56M только из-за свободного места.')
    h('Clock and exact command sequence' if not ru else 'Часы и порядок команд')
    timeline=[
      ('T+0-3','Count starters; assign live pins; confirm squad leads and backup commander.','Проверить явку, поставить метки, подтвердить лидеров и заместителя.'),
      ('T+3','Opening objectives unlock. S assists C/D then the contested Treatment Center.','Стартовые объекты открыты. S помогает C/D, затем центру под атакой.'),
      ('Live entry / Вход','Call a reserve when their entry unlocks and a seat is free.','Вызвать запасного, когда вход открыт и есть свободное место.'),
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
    body('Report: TARGET - STATUS - ENEMIES - ARRIVAL TIME - HELP. Example: Treatment 2 - held - 4 enemy marches - rally in 00:40 - need 2 S players. Move report: Martyku + creative to Dev; Баламут stays at Solar. Follow the plan without asking when safe. S chooses and times its own fights. HQ changes the overall plan and coordinates attacks involving several groups. If HQ disconnects, the agreed backup ChaosGoblin takes calls.' if not ru else 'Доклад: ЦЕЛЬ - СТАТУС - ВРАГИ - ПРИБЫТИЕ - ПОМОЩЬ. Пример: центр 2 - держим - 4 марша врага - ралли через 00:40 - нужны двое S. Переход: Martyku + creative в комплекс; Баламут остается на солнечной. Безопасный переход по плану - без разрешения. S сама выбирает атаки и время. HQ меняет общий план и согласует атаки нескольких групп. При отключении HQ команды принимает согласованный заместитель ChaosGoblin.')
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
    body('<b>Example:</b> Treatment 1 changes hands. Золото Мира goes to any safe pools there. Filin or Shikiiigami may help collect if their building is safely covered. The fighting marches keep the new garrison and protect collectors. If we lost Treatment 1, the same safe-pickup rule applies while the combat team prepares its next attack.' if not ru else '<b>Пример:</b> центр 1 сменил владельца. Золото Мира идет к безопасным лужам рядом. Filin или Shikiiigami помогают собирать, если их здание прикрыто. Боевые марши держат новый гарнизон и защищают сборщиков. Если центр 1 потеряли мы, безопасную воду тоже подбирать, пока бойцы готовят следующую атаку.')
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
    story.append(p(escape(chat_ru if ru else chat_en).replace('\n','<br/>'),'small'))
    h('Evidence and final pre-battle checks' if not ru else 'Источники и проверка перед боем')
    body('Roster updated 1 November 2026 from 19 supplied screenshots: 30 green starters and 5 yellow reserves. Starter row total: 539.43M; displayed header: 499.76M (difference 39.67M; cause unverified). The Arabic-named starter was confirmed in the additional screenshot. Mechanics and coordinates are retained from the earlier client-backed plan; live countdown and tooltips take precedence.' if not ru else 'Состав обновлен 01.11.2026 по 19 скриншотам: 30 зеленых основных и 5 желтых запасных. Сумма силы основных: 539.43M; заголовок: 499.76M (разница 39.67M, причина неизвестна). Участник с арабским ником подтвержден дополнительным скриншотом. Правила и координаты сохранены из прежнего плана по клиенту; таймер и подсказки игры важнее.')
    body('R4 confirms live attendance, main-march readiness, leader rally capacity and spawn-side access. Strategy and assignments are proposed orders based on the supplied power; no enemy roster or attendance forecast was supplied. Scout and adjust before committing across the map.' if not ru else 'R4 проверяет явку, готовность основных маршей, лимит ралли лидеров и доступ со стороны появления. Назначения - предлагаемые команды по указанной силе; состав врага и прогноз явки не предоставлены. До перехода через карту разведать и скорректировать.')

def footer(c,doc):
    c.setStrokeColor(colors.HexColor('#C4D0DA'));c.line(14*mm,13*mm,196*mm,13*mm)
    c.setFont('Body',8);c.setFillColor(INK);c.drawString(14*mm,8*mm,'[VeD] RR | EN / RU | 2026-11-01');c.drawRightString(196*mm,8*mm,str(doc.page))
doc=SimpleDocTemplate(str(args.output),pagesize=A4,leftMargin=14*mm,rightMargin=14*mm,topMargin=13*mm,bottomMargin=18*mm,title='VeD Reservoir Raid Battle Plan - English and Russian',author='Alliance command planning')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
args.output.with_suffix('.txt').write_text('EN ('+str(len(chat_en))+' characters)\n'+chat_en+'\n\nRU ('+str(len(chat_ru))+' characters)\n'+chat_ru+'\n',encoding='utf-8')
print(json.dumps({'pdf':str(args.output),'starters':len(players),'reserves':len(reserves),'starter_power_M':round(sum(v for _,v in players),2),'EN_characters':len(chat_en),'RU_characters':len(chat_ru)},ensure_ascii=False))
