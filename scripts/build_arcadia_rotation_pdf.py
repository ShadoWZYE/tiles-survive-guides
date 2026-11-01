"""State-shareable EN/RU rotation proposal with a separately auditable basis.

Governor queue structure, reward thresholds and policy multipliers are checked.
Local-client observations are not represented as live-server confirmation.
"""
from pathlib import Path
from collections import Counter
from decimal import Decimal
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work/hero-extraction'))
from refresh_hero_data import verified_tables
from decode_cfg import decode_table
from decode_language_pack import decode_language_pack
from unpack_client_lzma import CURRENT_SHA256
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,PageBreak,KeepTogether

OUT=ROOT/'docs/reports/Tiles-Survive-Arcadia-State-Rotation-EN-RU.pdf'
AUDIT=ROOT/'outputs/Arcadia-Rotation-Verification-2026-10-30.json'
PRIVATE=ROOT/'tmp/arcadia-chests-2026-10-30'
ASSETS=Path('C:/Program Files (x86)/FunPlus/Tiles Survive/GameData/GameAssets')
NAVY=colors.HexColor('#142B43');TEAL=colors.HexColor('#087F86');INK=colors.HexColor('#21364A')
MUTED=colors.HexColor('#566B7C');PALE=colors.HexColor('#EDF5F7');LINE=colors.HexColor('#CCDCE2')
AMBER=colors.HexColor('#FFF2D6')
WIDTH=A4[0]-80
SOURCE_PATCH='https://tilesurvivegame.com/en/blog/1055'
SOURCE_GUIDE='https://tilesurvivegame.com/en/blog/828'


def verify():
    PRIVATE.mkdir(parents=True,exist_ok=True)
    pack=(ASSETS/'BinaryConfigPack.ss').read_bytes();mp=ASSETS/'BinaryConfig/BinVersionList_Realtime.json'
    tables={};hashes={}
    for name,(_,raw) in verified_tables(pack,json.loads(mp.read_bytes()),{'kingdom_war_pvp_score_step','kingdom_war_pvp_score','buildings','server_event_open_time'},mp.parent).items():
        path=PRIVATE/(name+'.cfg');path.write_bytes(raw);tables[name]=decode_table(path)['rows'];hashes[name]=hashlib.sha256(raw).hexdigest()
    rows=sorted(tables['kingdom_war_pvp_score_step'],key=lambda r:r['Level'])
    assert len(rows)==40 and [r['Level'] for r in rows]==list(range(1,41))
    for r in rows:assert all(r[f'Step_{i}Score']<r[f'Step_{i+1}Score'] for i in range(1,9))
    expected={20:2920000,21:3410000,22:3840000,23:4610000,24:6070000,25:6940000,26:8450000,27:9600000,28:10000000}
    for level,target in expected.items():assert rows[level-1]['Step_9Score']==target
    assert all(r['Step_9Score']==2920000 for r in rows[:20])
    assert all(r['Step_9Score']==10000000 for r in rows[27:])
    assert max(r['Step_9Score'] for r in rows)==10000000
    policy=[]
    for label,level in [('10-20',20)]+[(str(i),i) for i in range(21,28)]+[('28+',28)]:
        t=rows[level-1]['Step_9Score'];cap=int(Decimal(t)*Decimal('1.5'))
        assert cap*2==t*3
        policy.append({'power_plant_level':label,'final_chest_target':t,'proposed_1_5x_ceiling':cap})
    occupations=[r for r in tables['kingdom_war_pvp_score'] if r['Type'] in ['occupy','occupy_t']]
    assert len(occupations)==2 and all(r['Param']==60 and r['Score']==10000 for r in occupations)
    lang=decode_language_pack(ASSETS/'Languages/InGameBin/language_en.json.bin.enc')
    rule=lang['event_throne_shock_help'];assert '1 consecutive hour' in rule and 'lasts 2 hours' in rule
    binary=Path('C:/Program Files (x86)/FunPlus/Tiles Survive/ngame/2.6.300.293/GameAssembly.dll')
    assert hashlib.sha256(binary.read_bytes()).hexdigest()==CURRENT_SHA256
    image=(ROOT/'tmp/native-293/verified/native-rva-image.bin').read_bytes()
    index=json.loads((ROOT/'tmp/native-293/verified/method-index.json').read_text())
    bodies=[('WonderModule.GetPersonalScoreStepStatus',0x112e1d0,0x112e360,'2f1f19f65c780ef940f4bfd507e05fc739eebfd887105a5ef3f5853403f4a4eb'),
            ('KingdomWarPvpScoreStepConfig.GetScoreStepRewardListByLevel',0x1ce67e0,0x1ce6d50,'b59cd9e5de294a0d69e28b56e351963909ec4c5293c547ec2f28dbcc53b37500')]
    for name,a,b,digest in bodies:
        assert any(r['type']+'.'+r['name']==name and r['rva']==a for r in index)
        assert hashlib.sha256(image[a:b]).hexdigest()==digest
    anchors={0x112e281:'e89ac72600',0x112e297:'e84485bb00',0x112e2dc:'4863481033c0483b4e780f9ec0'}
    for a,hexbytes in anchors.items():assert image[a:a+len(bytes.fromhex(hexbytes))]==bytes.fromhex(hexbytes)
    rotations={str(n):list(range(1,n+1))+[1] for n in [3,5,6]}
    for n,queue in rotations.items():
        assert len(queue)==int(n)+1 and queue[0]==queue[-1]==1
        assert len(set(queue[:-1]))==int(n)
    building40=next(r for r in tables['buildings'] if r['Id']=='building_stronghold_40_1')
    gate=next(r for r in tables['server_event_open_time'] if r['InternalId']==building40['ServerEventOpenTime'])
    assert gate['Id']=='city_40'
    result={'date':'2026-10-30','scope':'Shareable proposal; no alliance identities or private roster data.',
            'fact_status':'Verified local client 2.6.300.293 and manifest-verified tables; not a live event read. Live event screen takes priority.',
            'local_native_sha256':CURRENT_SHA256,'manifest_sha256':hashlib.sha256(mp.read_bytes()).hexdigest(),
            'table_sha256':hashes,'native_methods':[{'method':n,'rva':hex(a),'end':hex(b),'sha256':d} for n,a,b,d in bodies],
            'native_instruction_anchors':{hex(a):v for a,v in anchors.items()},
            'reward_selection':'Power Plant level -> reward list; threshold compared directly against WonderModule.PersonScore. Values are cumulative, not additive chest costs.',
            'all_level_thresholds':[{'level':r['Level'],'cumulative_chest_thresholds':[r[f'Step_{i}Score'] for i in range(1,10)]} for r in rows],
            'personal_policy':policy,'maximum_local_final_chest_threshold':10000000,'maximum_proposed_ceiling':15000000,
            'occupation_reference':{'points':10000,'interval_seconds':60,'ten_minutes_points':100000,'not_guaranteed_for_all_members':True},
            'current_local_event_rules':rule,'governor_succession_options':rotations,
            'queue_notation':'Numbers are positions in the agreed ranking snapshot. A always means whichever alliance is next to take control, not a permanently privileged alliance.',
            'rotation_policy':{'A':'Incoming governor alliance and state-chat mediator through R5/R4','starts':'When the protection period ends and battle is available','visitor_main_building_limit_seconds':600,'limit_scope':'Cumulative for each visiting alliance over the entire battle, across all captures and members. Not a ten-minute turn.','A_exempt_from_visitor_limit':True,'participation':'Attacks on Arcadia and towers remain permitted throughout the open battle, within occupation limits. Participation may not be prohibited.','tracking':'Every alliance tracks its own members and cumulative occupation; A mediates in state chat.'},
            'power_plant_40':{'building_configuration_present':True,'building_id':building40['Id'],'gate_id':gate['InternalId'],'gate_name':gate['Id'],'live_availability':'NOT VERIFIED - configuration presence is not proof of a live unlock.'},
            'healing_guidance':{'suggested_starting_batch':[5000,7000],'reported_example_help_cap':44,'guaranteed_batch_size':False,'exact_help_cooldown':'UNVERIFIED - check the live request timer','seconds_removed_per_help':'UNVERIFIED for the player - measure live; do not substitute construction values.','practical_method':'Start a small batch, request help when available, watch actual helps received and remaining time, then adjust. Check request cooldown before expecting a new help round.'},
            'reported_death_rate':{'reported_by_user':.05,'verified':False,'denominator_verified':False,'note':'Do not present as a proven loss of 5% of the entire attacking march on every hit.'},
            'proposals_not_game_mechanics':['Governor succession: top-five default, optional three or six alliances','10-minute cumulative main-building occupation ceiling per visiting alliance','Incoming governor alliance A alone may permanently garrison','1.5x personal scoring ceiling','Each alliance tracks its own members; A mediates in state chat'],
            'runtime_unknowns':['Active event reward overrides and player-specific live tier','Actual handover latency and occupation ledger','Tower-fire behavior in the current live event','Personal occupation point eligibility for a given garrison','Exact permanent-loss rate and denominator','Live Power Plant 40 availability'],
            'sources':[{'url':SOURCE_PATCH,'use':'Official two-hour battle duration update, 9 July 2026.'},{'url':SOURCE_GUIDE,'use':'Official occupation scoring and tower attrition guidance only; its older duration is superseded.'}]}
    # Private reproducibility record only; the public case study contains no exact scores or identities.
    shown=[Decimal(v)*1000000 for v in ['310.54','211.84','206.08','203.75','182.56','153.88']]
    excess=sum(max(0,s-15000000) for s in shown)
    assert sum(shown)==1268650000 and excess==1178650000
    result['anonymous_capture_comparison']={
        'scope':'Only the six visible leading entries; rounded screenshot scores, not the entire event.',
        'screenshot_scores_sum':int(sum(shown)), 'same_entries_at_policy_ceiling':90000000,
        'score_gap':int(excess), 'gap_share':float(excess/sum(shown)),
        'public_presentation':'Qualitative and anonymous. No player names, alliance tags, exact scores, casualty totals or reward quantities.',
        'casualty_conversion':'Not an actual death estimate. Scores also include own casualties, occupation and healing help; enemy defeated is not confirmed permanent death. Do not sum both sides as unique losses.',
        'local_enemy_defeat_points_by_tier':{str(r['Param']):r['Score'] for r in tables['kingdom_war_pvp_score'] if r['Type']=='kill'},
        'conditional_enemy_defeat_only_equivalents':{str(r['Param']):float(excess/Decimal(str(r['Score']))) for r in tables['kingdom_war_pvp_score'] if r['Type']=='kill' and r['Param'] in [7,8,9,10]},
        'conditional_equivalent_warning':'Hypothetical points-to-defeated-troops conversion only; excludes other sources and does not measure unique troops or permanent deaths.',
        'reward_observation':'Screenshot shows rank-dependent tokens, scrolls, speedups, food and wood. Higher rank offers more; incremental rank rewards are distinct from personal chests. No resource-cost break-even is proven.'}
    rates={r['Param']:int(r['Score']) for r in tables['kingdom_war_pvp_score'] if r['Type']=='kill'}
    assert {t:rates[t] for t in [7,8,9,10]}=={7:28,8:38,9:50,10:66}
    result['public_score_scenarios']={
        'assumption':'All scenario points from enemy troop defeats only. Not an estimate of actual unique troops, hospital occupancy, or permanent deaths.',
        'formula':'enemy defeat equivalents = scenario score / points per enemy troop defeated',
        'rows':[{'score':m*1000000,'equivalents':{str(t):m*1000000/rates[t] for t in [7,8,9,10]},'excess_above_15m':max(0,m-15)*1000000} for m in [10,15,100,200,300]],
        'privacy':'Generic score scenarios only; no identities or exact historical individual scores.'}
    AUDIT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return policy


def setup():
    fonts=Path('C:/Windows/Fonts');pdfmetrics.registerFont(TTFont('Arcadia',str(fonts/'arial.ttf')));pdfmetrics.registerFont(TTFont('ArcadiaBold',str(fonts/'arialbd.ttf')))
    pdfmetrics.registerFontFamily('Arcadia',normal='Arcadia',bold='ArcadiaBold',italic='Arcadia',boldItalic='ArcadiaBold')
    return {k:ParagraphStyle(k,fontName='ArcadiaBold' if k in ['title','section'] else 'Arcadia',fontSize=sz,leading=lead,textColor=co,spaceAfter=after)
            for k,sz,lead,co,after in [('title',20,24,NAVY,9),('sub',8.5,11,MUTED,10),('section',11,14,TEAL,6),('body',9.1,12.1,INK,6),('small',7.9,10.3,MUTED,5),('cell',8.7,11.5,INK,0)]}


def build(policy):
    st=setup();story=[]
    def p(text,style='body'):return Paragraph(text,st[style])
    def h(text):return p(text,'section')
    def box(text):
        t=Table([[p(text)]],colWidths=[WIDTH]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('BOX',(0,0),(-1,-1),.5,LINE),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),3)]));return t
    def table(head,rows,widths):
        t=Table([[p('<b>'+v+'</b>','cell') for v in head]]+[[p(v,'cell') for v in row] for row in rows],colWidths=widths,repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F7F9FB')]),('GRID',(0,0),(-1,-1),.35,LINE),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));return t
    for ru in [False,True]:
        tr=lambda en,other:other if ru else en
        if story:story.append(PageBreak())
        story += [p(tr('ARCADIA ROTATION SYSTEM','СИСТЕМА РОТАЦИИ АРКАДИИ'),'title'),
                  p(tr('Shared state agreement | Top-five default | 30 October 2026','Общее соглашение штата | Основной вариант: топ-5 | 30 октября 2026'),'sub'),
                  p(tr('The purpose is a fair governor succession, reward opportunities for everyone and fewer unnecessary troop losses. Apply the same rules to every alliance.','Цель - справедливая передача губернаторства, доступ к наградам для всех и сокращение лишних потерь войск. Правила одинаковы для всех альянсов.')),
                  box(tr('<b>A = the alliance due to take control for the next governor cycle.</b><br/>Only A may permanently garrison Arcadia. Every other alliance has a maximum of <b>10 minutes TOTAL main-building occupation for the whole battle</b>.','<b>A = альянс, который должен принять Аркадию на следующий губернаторский цикл.</b><br/>Только A может держать в Аркадии постоянный гарнизон. Для каждого другого альянса предел - <b>10 минут СУММАРНОГО удержания главного здания за весь бой</b>.')),
                  Spacer(1,9),h(tr('1 | Order and start of transfer','1 | Очередь и начало передачи')),
                  p(tr('At the opening of the rotation, take and publish an alliance-ranking snapshot. Use its order for the agreed cycle; changes require joint agreement. Announce the current governor and the next alliance (A) in state chat; update A at each handover. <b>The transfer starts when the protection period ends</b> and battle becomes available.','При открытии ротации сохраните и опубликуйте снимок рейтинга альянсов. Используйте этот порядок на согласованный цикл; изменения принимаются совместно. В чате штата объявите текущий губернаторский альянс и следующий (A); при каждой передаче обновляйте A. <b>Передача начинается после окончания защиты</b>, когда бой становится доступен.')),
                  table([tr('Format','Формат'),tr('Succession by ranking position - not battle slots','Очередь по месту в рейтинге, не слоты боя')],[
                      [tr('Default: top 5','Основной: топ-5'),'1 -> 2 -> 3 -> 4 -> 5 -> 1'],
                      [tr('OPTION: 3 alliances','ВАРИАНТ: 3 альянса'),'1 -> 2 -> 3 -> 1'],
                      [tr('OPTION: 6 alliances','ВАРИАНТ: 6 альянсов'),'1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 1']],[155,WIDTH-155]),
                  Spacer(1,7),h(tr('2 | Participation stays open','2 | Участие остается открытым')),
                  p(tr('<b>All alliances may attack Arcadia itself or its towers throughout the open battle.</b> Attacks are not restricted to a scheduled window. <b>It is not permitted to prohibit participation in the Arcadia battle.</b> Being outside the governor rotation does not remove the right to participate.','<b>Все альянсы могут атаковать саму Аркадию или ее башни на протяжении открытого боя.</b> Атаки не ограничиваются отдельным временным окном. <b>Запрещено запрещать участие в битве за Аркадию.</b> Отсутствие в губернаторской очереди не лишает права участвовать.')),
                  h(tr('3 | Why the ten-minute timer exists','3 | Зачем нужен таймер десять минут')),
                  p(tr('The timer protects the agreed transfer: a visiting alliance must not take the next governor\'s place by accumulating occupation time. <b>Add all its captures together</b>; changing members, rallies or garrisons does not reset the allowance. Ten minutes is a ceiling, not a guaranteed allocation.','Таймер защищает согласованную передачу: другой альянс не должен занять место следующего губернатора за счет накопленного удержания. <b>Складывайте все его захваты</b>; смена участников, сборов или гарнизона не обнуляет лимит. Десять минут - предел, а не гарантированная квота.')),
                  p(tr('Visiting captains should warn A at eight minutes and arrange the owner change before ten. At the limit, withdraw and do not recapture or hold the main building again. Other permitted participation may continue. Tower holding is coordinated separately by A; it does not add to the main-building timer. <b>Withdrawing troops alone is not proof that ownership time has stopped.</b>','Капитаны других альянсов предупреждают A на восьмой минуте и организуют смену владельца до десятой. При достижении лимита отзовите войска и больше не захватывайте и не удерживайте главное здание. Другие разрешенные способы участия остаются доступны. Удержание башен отдельно координирует A; оно не прибавляется к таймеру главного здания. <b>Один отзыв войск не доказывает остановку времени владения.</b>')),
                  h(tr('4 | Each alliance manages its own members','4 | Каждый альянс отвечает за своих участников')),
                  p(tr('Each alliance\'s R5/R4 tracks its members\' points and its own cumulative Arcadia occupation. Encourage members to participate and claim their chests; once rewards are claimed, recommend withdrawing to reduce state-wide losses. The personal ceiling is <b>1.5 x the player\'s final-chest target</b>; see the reference on the next page.','R5/R4 каждого альянса отслеживают очки своих участников и собственное суммарное удержание Аркадии. Поощряйте участие и получение сундуков; после наград рекомендуйте выйти из боя, чтобы сократить потери штата. Личный предел - <b>1,5 x порог последнего сундука игрока</b>; справочник на следующей странице.')),
                  h(tr('5 | A coordinates and mediates in state chat','5 | A координирует и решает споры в чате штата')),
                  p(tr('A\'s R5/R4 may manage the main-building garrison and tower holding to support the transfer. Each alliance handles its own members; if needed, A mediates using occupation times and battle reports. Resolve errors through recalls, clarification and agreed corrections, not retaliation. <b>Coordination must not become a blanket ban on attacking Arcadia or joining the battle.</b>','R5/R4 альянса A могут управлять гарнизоном главного здания и удержанием башен для передачи контроля. Каждый альянс управляет своими участниками; при необходимости A решает спор по времени удержания и боевым отчетам. Исправляйте ошибки отзывом войск, разъяснением и согласованной корректировкой, а не ответными ударами. <b>Координация не должна превращаться в общий запрет атаковать Аркадию или участвовать в бою.</b>'))]
        story.append(PageBreak())
        story += [p(tr('PERSONAL TARGETS | SIMPLE REFERENCE','ЛИЧНЫЕ ЦЕЛИ | КРАТКИЙ СПРАВОЧНИК'),'title'),
                  p(tr('Rewards first; avoid unnecessary losses | State rules, not game-enforced caps','Сначала награды; избегайте лишних потерь | Правила штата, не лимиты игры'),'sub'),
                  p(tr('<b>T = the cumulative points for your final personal chest shown in the current event.</b> The verified local reward table has nine chests and a highest final threshold of 10,000,000 points. Do not add the chest thresholds together. Check the live reward page; if it differs, use its value.','<b>T = накопленные очки для последнего личного сундука на экране текущего события.</b> В проверенной локальной таблице девять сундуков; наибольший последний порог - 10 000 000 очков. Не складывайте пороги сундуков. Сверьтесь с наградами в игре; при расхождении используйте их значение.'))]
        fmt=lambda x:f'{x:,}'.replace(',',' ' if ru else ',')
        story.append(table([tr('Power Plant','Электростанция'),tr('Final chest: T','Последний сундук: T'),tr('State ceiling: 1.5 x T','Предел штата: 1,5 x T')],[[r['power_plant_level'],fmt(r['final_chest_target']),fmt(r['proposed_1_5x_ceiling'])] for r in policy],[102,(WIDTH-102)/2,(WIDTH-102)/2]))
        story += [Spacer(1,6),p(tr('28+ describes inspected reward rows, not a live building-level limit. Power Plant 40 exists in local data; its availability in this state is unverified.','28+ описывает проверенные строки наград, а не доступный предел здания. Электростанция 40 есть в локальных данных; ее доступность в этом штате не подтверждена.'),'small'),
                  h(tr('Finish rewards; then yield priority','Закройте награды и уступите приоритет')),
                  p(tr('Aim for T, claim the chests, and preferably withdraw. Up to 1.5 x T is a state ceiling, not a second target or an extra reward tier. Stop voluntary score farming at that ceiling. Each alliance tracks and addresses its own overruns; A mediates if needed. Review accidental in-flight points or genuine defence separately - do not punish them automatically or use them to ban normal participation.','Стремитесь к T, заберите сундуки и по возможности выйдите из боя. 1,5 x T - предел штата, а не вторая цель или новый этап наград. На этом пределе прекратите добровольный набор очков. Каждый альянс отслеживает и разбирает свои превышения; A помогает при споре. Очки уже идущих маршей и настоящую оборону рассматривайте отдельно, без автоматического наказания или запрета обычного участия.')),
                  h(tr('Heal in small batches with alliance help','Лечите небольшими партиями с помощью альянса')),
                  p(tr('<b>Start around 5,000-7,000 troops at a time</b>, then adjust to the displayed healing timer. This is a trial batch, not a guaranteed speedup-free amount. Start healing and request Help when available. Ask online members to help; watch <b>helps actually received</b> and time remaining. An example cap of <b>44 helps</b> does not mean all 44 arrive instantly.','<b>Начните примерно с 5 000-7 000 бойцов за раз</b> и подберите размер по таймеру лечения. Это пробная партия, а не гарантия лечения без ускорений. Начните лечение и запросите помощь, когда она доступна. Попросите участников онлайн помочь; смотрите на <b>реально полученную помощь</b> и остаток времени. Пример лимита <b>44 помощи</b> не означает, что все 44 придут мгновенно.')),
                  p(tr('If help finishes the batch, repeat. If time remains, reduce the next batch or wait rather than spend speedups. <b>Check the Help request cooldown before relying on another round.</b> Help strength, troop tier, healing speed and online helpers affect the result. No fixed cooldown or seconds-per-help value is assumed.','Если помощь завершила партию, повторите. Если время осталось, уменьшите следующую партию или дождитесь окончания вместо траты ускорений. <b>Проверьте таймер повторного запроса, прежде чем рассчитывать на новый круг помощи.</b> Результат зависит от силы помощи, тира войск, скорости лечения и участников онлайн. Фиксированная задержка или число секунд за помощь здесь не предполагаются.')),
                  h(tr('Reduce losses without excluding players','Снижайте потери, не исключая игроков')),
                  p(tr('Direct attacks and rallies can cause permanent troop losses. Do not describe them as free points or force anyone to sacrifice troops. Check battle reports, keep hospital space available, and avoid repeating expensive attacks after rewards are complete. No unrelated settlement or resource attacks are needed for this system.','Прямые атаки и сборы могут приводить к безвозвратным потерям войск. Не называйте их бесплатными очками и не заставляйте участников жертвовать войсками. Проверяйте боевые отчеты, оставляйте место в госпитале и не повторяйте дорогие атаки после получения наград. Для этой системы не нужны посторонние атаки на поселения или ресурсы.')),
                  box(tr('<b>Reported ~5% permanent losses: NOT VERIFIED.</b> The exact rate and its denominator were not established from the inspected files. In particular, do not promise that each attack loses exactly 5% of the entire march or rally. Use the actual casualty report.','<b>Сообщаемые ~5% безвозвратных потерь: НЕ ПОДТВЕРЖДЕНО.</b> Точная ставка и база расчета не установлены по проверенным файлам. Не утверждайте, что каждая атака теряет ровно 5% всего марша или сбора. Ориентируйтесь на фактический боевой отчет.')),
                  h(tr('Evidence and limits','Основание и ограничения')),
                  p(tr('Verified locally in client 2.6.300.293: reward values and Power Plant selection. Not live-confirmed: reward overrides, exact healing-help cooldown/effect, and the reported 5% loss rate. The live event screen takes priority. Governor succession, the cumulative ten-minute visitor limit, 1.5x personal ceiling and mediation by A are state rules, not game-enforced limits.','Проверено локально в клиенте 2.6.300.293: награды и выбор по уровню Электростанции. Не подтверждены в текущем событии: изменения наград, точная задержка/эффект помощи лечению и сообщаемые 5% потерь. Приоритет у экрана игры. Очередь, суммарные десять минут для других альянсов, личный предел 1,5x и посредничество A - правила штата, а не ограничения игры.'),'small'),
                  p(tr('Sources: official duration update: ','Источники: официальное обновление длительности: ')+f'<link href="{SOURCE_PATCH}" color="#087F86">tilesurvivegame.com/en/blog/1055</link><br/>'+tr('Official Arcadia guide (occupation/towers; its old duration is superseded): ','Официальный гайд Аркадии (удержание и башни; старая длительность заменена): ')+f'<link href="{SOURCE_GUIDE}" color="#087F86">tilesurvivegame.com/en/blog/828</link>','small')]
        story.append(PageBreak())
        story += [p(tr('WHY STOP AFTER REWARDS?','ЗАЧЕМ ОСТАНАВЛИВАТЬСЯ ПОСЛЕ НАГРАД?'),'title'),
                  p(tr('Anonymous review | Generic score scenarios, not named player results','Анонимный разбор | Условные очки, а не результаты конкретных игроков'),'sub'),
                  box(tr('<b>Hospitalised troops still cost the state.</b> Even when troops survive, unnecessary fighting ties up armies, consumes healing resources and players\' time, and can create pressure to use speedups. <b>Mass hospitalisation purely for personal ranking should be strongly discouraged.</b> Permanent deaths are not the only harm.','<b>Раненые в госпитале тоже обходятся штату дорого.</b> Даже выжившие войска выбывают из строя; лишние бои расходуют ресурсы на лечение и время игроков, подталкивают к трате ускорений. <b>Массовое заполнение госпиталей только ради личного рейтинга следует решительно пресекать.</b> Вред не ограничивается безвозвратными потерями.')),
                  Spacer(1,9),h(tr('How much fighting do these scores represent?','Какому объему боев соответствуют такие очки?')),
                  p(tr('The inspected client awards <b>28 / 38 / 50 / 66 points</b> per defeated enemy troop of tier <b>T7 / T8 / T9 / T10</b>. The table divides each score by that rate. <b>Assumption: all points come from defeating enemy troops.</b> Values are approximate millions of troop defeats, not permanent deaths.','Проверенный клиент начисляет <b>28 / 38 / 50 / 66 очков</b> за пораженного бойца противника тира <b>T7 / T8 / T9 / T10</b>. В таблице очки разделены на эту ставку. <b>Условие: все очки получены только за поражение войск противника.</b> Значения - приблизительные миллионы поражений бойцов, не безвозвратные потери.'))]
        scenario_rates=[28,38,50,66]
        dec=lambda v:f'{v:.2f}'.replace('.',',' if ru else '.')
        story.append(table([tr('Score','Очки')]+[f'T{t}' for t in [7,8,9,10]],
                           [[f'{m} M']+[dec(m/rate) for rate in scenario_rates] for m in [10,15,100,200,300]],
                           [95]+[(WIDTH-95)/4]*4))
        story += [Spacer(1,5),p(tr('All troop columns are in MILLIONS. Rounded to two decimal places. These are enemy-defeat equivalents, not a casualty forecast or a measured hospital count.','Все столбцы войск - в МИЛЛИОНАХ. Округление до сотых. Это эквивалент поражений противника, не прогноз потерь и не фактическая загрузка госпиталей.'),'small'),
                  h(tr('The gap above the recommended ceiling','Разница с рекомендуемым пределом')),
                  p(tr('Compared with <b>15M</b>, scores of <b>100M / 200M / 300M</b> mean about <b>6.7 / 13.3 / 20 times</b> the score. The excess alone is <b>85M / 185M / 285M</b>. In the T8-only scenario, that excess corresponds to about <b>2.24M / 4.87M / 7.50M additional troop defeats</b>. That scale of extra fighting deserves scrutiny even if many troops can later be healed.','Относительно <b>15M</b> результаты <b>100M / 200M / 300M</b> означают примерно <b>6,7 / 13,3 / 20 раз</b> больше очков. Само превышение - <b>85M / 185M / 285M</b>. При условии только T8 это эквивалентно примерно <b>2,24M / 4,87M / 7,50M дополнительных поражений бойцов</b>. Такой масштаб лишних боев требует внимания, даже если многих бойцов затем можно вылечить.')),
                  h(tr('What the numbers do - and do not - establish','Что эти числа показывают, а что нет')),
                  p(tr('Actual event scores also include own wounded or defeated troops, occupation and healing help; troop tiers may be mixed. Subtract those other points before converting a real score. The same troops can be healed and defeated again. Therefore these figures are <b>not unique soldiers, simultaneous hospital occupancy, permanent deaths, or proof that half the state was hospitalised</b>. Battle reports and score breakdowns are needed for those claims.','Фактические очки включают также собственных раненых или потерянных бойцов, удержание и помощь в лечении; тиры могут различаться. При переводе реального результата сначала вычтите прочие очки. Те же бойцы могут быть вылечены и снова поражены. Поэтому это <b>не уникальные бойцы, не одновременное заполнение госпиталей, не погибшие и не доказательство, что половина войск штата попала в госпиталь</b>. Для таких выводов нужны боевые отчеты и разбивка очков.')),
                  h(tr('Rewards do not remove the recovery burden','Награды не отменяют нагрузку на восстановление')),
                  p(tr('<b>After the final personal chest, extra points unlock no additional personal chests in the inspected table.</b> Ranking rewards are separate: better places can award more tokens, scrolls, speedups, food and wood. Compare only the extra prize for improving a place with the extra recovery burden imposed on the state. A rank prize goes to its recipient; other players may bear much of the healing cost. An exact resource break-even is not established by the screenshots.','<b>После последнего личного сундука дополнительные очки не открывают новых личных сундуков в проверенной таблице.</b> Рейтинг - отдельная награда: более высокие места могут дать больше жетонов, свитков, ускорений, еды и древесины. Сравнивайте только прибавку за улучшение места с дополнительной нагрузкой на восстановление штата. Рейтинговый приз получает его обладатель, а значительную часть лечения могут оплачивать другие игроки. Точная окупаемость по скриншотам не установлена.')),
                  box(tr('<b>Shared-state rule:</b> complete the chests, claim rewards, then stop voluntary score farming at the agreed ceiling. Do not keep hospitalising other members\' armies solely to improve personal rank. Genuine transfer or defence needs are reviewed separately. Each alliance manages its members; A mediates disputes.','<b>Общее правило штата:</b> закройте сундуки, заберите награды и прекратите добровольный набор очков на согласованном пределе. Не продолжайте отправлять армии других участников в госпиталь только ради личного места. Реальную необходимость передачи или обороны рассматривайте отдельно. Каждый альянс отвечает за своих участников; A помогает решать споры.')),
                  Spacer(1,6),p(tr('Basis: anonymous supplied leaderboard/reward observations and manifest-verified local scoring tables. Scenario amounts are generic; no player or alliance is identified. Live event scoring takes priority if different.','Основание: анонимные наблюдения по скриншотам рейтинга и наград, локальные таблицы очков с проверкой по манифесту. Значения условные; игроки и альянсы не названы. При расхождении приоритет у текущих правил игры.'),'small')]
    def footer(c,d):
        c.setStrokeColor(LINE);c.line(40,35,A4[0]-40,35);c.setFont('Arcadia',7.5);c.setFillColor(MUTED)
        c.drawString(40,23,'Arcadia | '+('English' if d.page<=3 else 'Русский')+' | 30.10.2026')
        c.drawRightString(A4[0]-40,23,f'{d.page}/6')
    doc=SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=40,rightMargin=40,topMargin=30,bottomMargin=47,
                          title='Arcadia Governor Rotation - State Agreement - English and Russian',author='State coordination proposal',subject='Governor succession; cumulative ten-minute visiting occupation; open participation and personal targets')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    import pymupdf
    check=pymupdf.open(OUT)
    if len(check)!=6:raise ValueError(f'Expected six pages; got {len(check)}. Adjust layout before sharing.')
    for page in check:
        for block in page.get_text('blocks'):assert block[0]>=0 and block[1]>=0 and block[2]<=page.rect.width and block[3]<=page.rect.height
    check.close();print(OUT)


if __name__=='__main__':build(verify())
