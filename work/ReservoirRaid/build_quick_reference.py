"""Create standalone shareable PNG battle charts without changing the PDF."""
from pathlib import Path
import ast
import textwrap
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'outputs' / 'reservoir-raid'
OUT.mkdir(parents=True, exist_ok=True)
tree = ast.parse((HERE / 'build_battle_plan.py').read_text(encoding='utf-8'))
data = {}
for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in ('groups', 'reserves'):
                data[target.id] = ast.literal_eval(node.value)
groups = {g[0]: g for g in data['groups']}
assert sum(len(g[1]) for g in groups.values()) == 30
FONT = Path('C:/Windows/Fonts')
if not FONT.exists(): FONT = Path('/usr/share/fonts/truetype/dejavu')
def font(size, bold=False):
    name = ('segoeuib.ttf' if bold else 'segoeui.ttf') if FONT.name == 'Fonts' else ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')
    return ImageFont.truetype(str(FONT/name), size)
NAVY='#16344C'; INK='#173042'; BLUE='#057893'; PALE='#ECF3F7'; BG='#F8FAFC'
titles={
 'S':('Independent strike team','Самостоятельная ударная группа'),
 'A':('Treatment Center 1','Водоочистительный центр 1'),
 'B':('Treatment Center 2','Водоочистительный центр 2'),
 'C':('Solar > Dev at T+15','Солнечная > комплекс T+15'),
 'D':('Helipad > Munitions at T+15','Площадка > военный T+15'),
 'P1':('Processing Plant 1','Водоперерабатывающий завод 1'),
 'P2':('Processing Plant 2','Водоперерабатывающий завод 2'),
 'P3':('Processing Plant 3','Водоперерабатывающий завод 3'),
 'P4':('Processing Plant 4','Водоперерабатывающий завод 4'),
 'G':('Water collection / support','Сбор воды / поддержка'),
}
jobs={
 'S':('Choose help and attacks. At T+15 take Central. Keep a strong defender there.', 'Сами выбирать помощь и атаки. T+15 - центр. Оставить там сильного защитника.'),
 'A':('Salman holds. Others reinforce, help Plant 1 or collect nearby water when safe.', 'Salman держит. Остальные помогают, идут на завод 1 или безопасный сбор рядом.'),
 'B':('Loki holds. Others reinforce, help Plant 2 or collect nearby water when safe.', 'Loki держит. Остальные помогают, идут на завод 2 или безопасный сбор рядом.'),
 'C':('Wróżka stays at Solar. LadyGroz + Filin move to Dev when Solar is safe.', 'Wróżka держит солнечную. LadyGroz + Filin идут в комплекс при безопасной защите.'),
 'D':('Mortisha stays at Helipad. Martyku + Bruklin88 move to Munitions when safe.', 'Mortisha держит площадку. Martyku + Bruklin88 идут на военный при безопасной защите.'),
 'P1':('Lexxiii holds. CaptMac supports; collects safe water in SW.', 'Lexxiii держит. CaptMac помогает; собирает безопасную воду на ЮЗ.'),
 'P2':('Баламут holds. IBRAHIM Zain supports; collects safe water in NE.', 'Баламут держит. IBRAHIM Zain помогает; собирает безопасную воду на СВ.'),
 'P3':('HoloCrow holds. monika supports; collects safe water in NW.', 'HoloCrow держит. monika помогает; собирает безопасную воду на СЗ.'),
 'P4':('KayKat holds. ryan supports; collects safe water in SE.', 'KayKat держит. ryan помогает; собирает безопасную воду на ЮВ.'),
 'G':('Collect safe splashed water immediately. No water? Reinforce or scout your sector.', 'Разлитую воду собирать сразу, если безопасно. Нет воды - помощь или разведка сектора.'),
}

def build(ru):
    im=Image.new('RGB',(2400,1640),BG);d=ImageDraw.Draw(im)
    def txt(x,y,text,size=24,bold=False,color=INK): d.text((x,y),text,font=font(size,bold),fill=color)
    def wrap(text,width,size):
        result=[];line=''
        for word in text.split():
            test=(line+' '+word).strip()
            if d.textlength(test,font=font(size))>width and line: result.append(line);line=word
            else: line=test
        if line: result.append(line)
        return result
    def block(x,y,text,width,size=24,bold=False,color=INK,gap=5):
        lines=wrap(text,width,size)
        for i,line in enumerate(lines): txt(x,y+i*(size+gap),line,size,bold,color)
        return len(lines)*(size+gap)
    d.rectangle((0,0,2400,140),fill=NAVY)
    txt(40,19,'[VeD] RESERVOIR RAID' if not ru else '[VeD] РЕЙД НА РЕЗЕРВУАР',49,True,'white')
    txt(40,84,'Commander: TheShadowWZYE   |   Second-in-command: Shikiiigami' if not ru else 'Командир: TheShadowWZYE   |   Заместитель: Shikiiigami',29,False,'white')
    txt(2320,40,'EN' if not ru else 'RU',29,True,'white')
    def card(code,x,y):
        d.rounded_rectangle((x,y,x+690,y+174),radius=14,fill='white',outline='#C3D0DA',width=2)
        txt(x+18,y+10,code+' | '+titles[code][int(ru)],28,True,NAVY)
        if code=='G':
            names=('4uzhaya NW / Xaroth NE / Yesimemily SW / Bulik SE' if not ru else '4uzhaya СЗ / Xaroth СВ / Yesimemily ЮЗ / Bulik ЮВ')
        else: names=' / '.join(n for n,_ in groups[code][1])
        height=block(x+18,y+48,names,650,26)
        end=y+48+height+7+block(x+18,y+48+height+7,jobs[code][int(ru)],650,23)
        assert end<=y+168,(code,ru,end,y+174)
    for i,code in enumerate(['A','B','C','D','P1']): card(code,40,160+i*188)
    for i,code in enumerate(['S','P2','P3','P4','G']): card(code,1670,160+i*188)

    # Actual client isometric projection. Compact labels sit beside their icons.
    x0,y0,scale=785,200,4.5
    d.rounded_rectangle((760,160,1640,1090),radius=16,fill='#F2E6D3')
    def pos(x,y): return (x0+(91+.65*(x-y))*scale, y0+(178-(16+.65*(x+y-142)))*scale)
    nodes=[
      ('factory',138,195,'P3 | Plant 3','P3 | Завод 3',34,150,44),
      ('powerstation',100,200,'C | Solar','C | Солнечная',4,91,43),
      ('zombie',119,162,'C | Dev T+15','C | Комплекс T+15',50,85,44),
      ('process_center',56,105,'A | Treatment 1','A | Центр 1',45,1,50),
      ('factory',33,119,'P1 | Plant 1','P1 | Завод 1',4,35,43),
      ('factory',205,119,'P2 | Plant 2','P2 | Завод 2',129,146,50),
      ('process_center',181,132,'B | Treatment 2','B | Центр 2',103,101,47),
      ('tank',119,76,'D | Munitions T+15','D | Военный T+15',102,62,40),
      ('airport',138,37,'D | Helipad','D | Площадка',144,47,35),
      ('factory',100,42,'P4 | Plant 4','P4 | Завод 4',137,6,43),
      ('center',117,117,'S | Central T+15','S | Центр T+15',51,51,48),
    ]
    for x,y,name,off in [(86,150,'4uzhaya',-9),(86,90,'Yesimemily',-9),(154,150,'Xaroth',9),(154,90,'Bulik',9)]:
        px,py=pos(x,y);radius=6*scale
        d.ellipse((px-radius,py-radius,px+radius,py+radius),outline=BLUE,width=3)
        ty=py-off*scale-9
        tw=d.textlength(name,font=font(19,True));txt(px-tw/2,ty,name,19,True,BLUE)
    for kind,x,y,en,rus,bx,by,bw in nodes:
        px,py=pos(x,y);bh=9
        lx=x0+bx*scale;ly=y0+(178-by-bh)*scale;lw=bw*scale;lh=bh*scale
        ax=max(lx,min(px,lx+lw));ay=max(ly,min(py,ly+lh))
        d.line((ax,ay,px,py),fill='#AA9475',width=2)
        icon=Image.open(HERE/'assets'/f'sp_icon_big_ava_building_{kind}.png').convert('RGBA')
        icon.thumbnail((72,72),Image.Resampling.LANCZOS)
        im.paste(icon,(round(px-icon.width/2),round(py-icon.height/2)),icon)
        label=Image.new('RGBA',im.size,(0,0,0,0));ld=ImageDraw.Draw(label)
        ld.rounded_rectangle((lx,ly,lx+lw,ly+lh),radius=7,fill=(255,255,255,210),outline=(170,150,120,100),width=1)
        im.paste(label,(0,0),label)
        caption=rus if ru else en
        label_size=20
        while d.textlength(caption,font=font(label_size,True))>lw-16:
            label_size-=1
        assert label_size>=16,(caption,label_size)
        txt(lx+8,ly+7,caption,label_size,True,NAVY)
    block(783,1010,'Blue circles: possible tank areas. Names: sector collectors. Cards: squad members and jobs.' if not ru else 'Синие круги: районы водосборников. Ники: сборщики сектора. Карточки: состав и задачи групп.',820,22)

    d.rounded_rectangle((40,1110,2360,1250),radius=14,fill=PALE)
    txt(60,1120,'RESERVES | Blockbuster first. Enter from T+5 only if a place is free.' if not ru else 'ЗАПАСНЫЕ | Blockbuster первой. Вход с T+5 только при свободном месте.',27,True,NAVY)
    txt(60,1162,'Blockbuster / Icemind / hellolleh / Purplerockchick',26)
    txt(60,1201,'Peacheybites! / KORAK / Eden Ivy / SWATIRAQ7',26)
    rules=[
      ('FOLLOW THE PLAN','Follow your listed jobs unless HQ changes the plan. S chooses its own fights.', 'СЛЕДОВАТЬ ПЛАНУ','Выполнять свои задачи, пока HQ не изменит план. S сама выбирает атаки.'),
      ('MOVE WHEN SAFE','Next job open + enough defense stays + no incoming attack. Report and move; no approval needed.', 'ИДТИ, ЕСЛИ БЕЗОПАСНО','Следующая цель открыта, защита достаточна, атаки нет. Сообщить и идти без разрешения.'),
      ('KEEP DEFENSE','Never leave as the last defender. S keeps a strong defender at Central.', 'СОХРАНИТЬ ЗАЩИТУ','Последний защитник не уходит. S оставляет сильного защитника в центре.'),
      ('PICK UP WATER','Safe spills: collect now; both sides can take them. No water? Return to your job.', 'СОБИРАТЬ ВОДУ','Безопасные лужи брать сразу: они доступны обеим сторонам. Нет воды - вернуться к задаче.'),
    ]
    for i,r in enumerate(rules):
        x=40+i*590
        d.rounded_rectangle((x,1270,x+560,1430),radius=12,fill='white',outline='#C3D0DA',width=2)
        txt(x+16,1280,r[2] if ru else r[0],24,True,NAVY)
        block(x+16,1318,r[3] if ru else r[1],525,24)
    txt(40,1450,'T+3  Opening buildings    |    T+15  Central / Dev / Munitions    |    T+25 / 35 / 45  Tank waves' if not ru else 'T+3  Стартовые здания    |    T+15  Центр / комплекс / военный    |    T+25 / 35 / 45  Волны сбора',31,True,NAVY)
    txt(40,1504,'T starts with preparation. Use the live game countdown. Splashed water has no fixed wave time.' if not ru else 'T считается от начала подготовки. Таймер игры важнее. Разлитая вода не привязана к волнам.',26)
    txt(40,1560,'30 starters / 8 confirmed reserves | 4 Oct 2026 | Separate quick reference; detailed plan has full instructions.' if not ru else '30 основных / 8 подтвержденных запасных | 04.10.2026 | Отдельная памятка; подробные правила в плане.',22,False,'#536B7B')
    path=OUT/f'VeD-Reservoir-Raid-Quick-Reference-{"RU" if ru else "EN"}.png'
    im.save(path,optimize=True)
    print(path)
for ru in (False,True): build(ru)
