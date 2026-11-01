from pathlib import Path
import sys,json,hashlib,math
from html import escape
sys.path.insert(0,str(Path('work/hero-extraction').resolve()))
from decode_cfg import decode_table
from refresh_hero_data import verified_tables
from decode_language_pack import decode_language_pack
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,PageBreak,Spacer
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
ROOT=Path(__file__).resolve().parents[2];private=ROOT/'tmp/powerplant-audit';private.mkdir(parents=True,exist_ok=True)
game=Path('C:/Program Files (x86)/FunPlus/Tiles Survive/GameData/GameAssets')
pack=(game/'BinaryConfigPack.ss').read_bytes();manifest=(game/'BinaryConfig/BinVersionList_Realtime.json').read_bytes()
verified=verified_tables(pack,json.loads(manifest),{'buildings','building_type'})
rows={};tables={}
for name,(i,raw) in verified.items():
 p=private/f'{name}.cfg';p.write_bytes(raw);tables[name]=decode_table(p)['rows']
rows={r['InternalId']:r for r in tables['buildings']};types={r['InternalId']:r for r in tables['building_type']}
langs={'EN':decode_language_pack(game/'Languages/InGameBin/language_en.json.bin.enc')}
rup=game/'Languages/InGameBin/language_ru.json.bin.enc'
langs['RU']=decode_language_pack(rup) if rup.exists() else langs['EN']
plant=[r for r in rows.values() if r['Type']==800005 and r['Id']==f"building_stronghold_{r['Level']}" and 1<=r['Level']<=30];plant.sort(key=lambda r:r['Level'])
assert len(plant)==30
# Standard stages only. A level's sequential predecessor is needed even when not repeated in ReqBuildingD.
base={}
for r in rows.values():
 if r['BuildingsRank']==0:
  key=(r['Type'],r['Level'])
  if key in base and base[key]['InternalId']!=r['InternalId']:raise ValueError(f'Ambiguous base stage {key}')
  base[key]=r
print('base nodes',len(base))
def closure(number,found):
 if number in found:return
 r=rows[number];found.add(number)
 prev=base.get((r['Type'],r['Level']-1))
 if r['Level']>1:
  if not prev:raise ValueError('Missing predecessor '+r['Id'])
  closure(prev['InternalId'],found)
 for x in r['ReqBuildingD']:closure(x,found)
from audit_speedup_income import audit
income=audit()
research=decode_table(ROOT/'tmp/speedup-income-audit/research_main.cfg')['rows']
research_by_id={r['InternalId']:r for r in research}

def research_bonuses(existing):
 # Research is assumed completed between PP steps. No future building gate is borrowed.
 cache={}
 def eligible(i,active=None):
  if i in cache:return cache[i]
  active=set() if active is None else active
  if i in active:raise ValueError('Research cycle')
  r=research_by_id[i]
  result=all(x in existing for x in r['BuildingReq']) and all(eligible(x,active|{i}) for x in r['ResearchReq'])
  cache[i]=result;return result
 best={}
 for r in research:
  if r['Id'].startswith(('new_development_building_time_','new_development_help_building_time_')) and eligible(r['InternalId']):
   for b in r['Benefits']:
    key=(r['Group'],b['benefit_id']);best[key]=max(best.get(key,0),b['benefit_value'])
 return sum(v for (g,b),v in best.items() if b==300314),sum(v for (g,b),v in best.items() if b==301893)

def help_budget(existing,extra):
 comms=[rows[n] for n in existing if rows[n]['Type']==800016]
 if not comms:return 0,0
 b=max(comms,key=lambda r:r['Level'])
 benefits={x['benefit_id']:x['benefit_value'] for x in b['BenefitIdD']}
 return int(6+benefits.get(300511,0)),20+extra+benefits.get(300510,0)

records=[];cumulative=0;previous=set();adjusted_total=0
for r in plant:
 cumulative+=r['BuildTimeD'];needed=set();closure(r['InternalId'],needed)
 assert all(rows[n]['Level']<=r['Level'] for n in needed if rows[n]['Type']==800005)
 incremental=needed-previous
 bonus,extra=research_bonuses(previous)
 cap,help_seconds=help_budget(previous,extra)
 adjusted=sum(max(0,math.ceil(rows[n]['BuildTimeD']/(1+bonus))-cap*help_seconds) for n in incremental)
 adjusted_total+=adjusted
 records.append({'step_base_seconds':sum(rows[n]['BuildTimeD'] for n in incremental),'step_adjusted_seconds':adjusted,'adjusted_cumulative_seconds':adjusted_total,'research_speed_bonus':bonus,'help_count':cap,'seconds_per_help':help_seconds,'new_upgrade_count':len(incremental),'level':r['Level'],'powerplant_seconds':r['BuildTimeD'],'powerplant_cumulative_seconds':cumulative,'all_required_work_seconds':sum(rows[n]['BuildTimeD'] for n in needed),'direct_prerequisites':[{'type':rows[n]['Type'],'level':rows[n]['Level'],'last_upgrade_seconds':rows[n]['BuildTimeD']} for n in r['ReqBuildingD']],'required_nodes':len(needed)})
 previous=needed
out=ROOT/'docs/reports/Tiles-Survive-Power-Plant-Upgrade-Times-EN-RU.pdf'
normalized={'date':'2026-10-11','scope':'Levels 1-30; BuildTimeD/ReqBuildingD branch; single queue minimum prerequisite route',
 'pack_sha256':hashlib.sha256(pack).hexdigest(),'tables_sha256':{n:hashlib.sha256(raw).hexdigest() for n,(_,raw) in verified.items()},'rows':records,
 'adjustment_assumptions':'All eligible new-development research completed before each PP step, gated by buildings in previous route closure. Full configured help at previous-route Comms level. No items, VIP, heroes, free finish or resource/research waiting. Fixed help approximation; server traces not observed.',
 'f2p_estimate':income}
(ROOT/'outputs/Power-Plant-Upgrade-Times-2026-10-11.json').write_text(json.dumps(normalized,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
pdfmetrics.registerFont(TTFont('Body','C:/Windows/Fonts/segoeui.ttf'));pdfmetrics.registerFont(TTFont('Bold','C:/Windows/Fonts/segoeuib.ttf'))
navy=colors.HexColor('#12304B');styles={k:ParagraphStyle(k,fontName='Bold' if k in ['title','h','head'] else 'Body',fontSize=size,leading=lead,textColor=colors.white if k=='head' else navy,spaceAfter=6 if k!='cell' else 0) for k,size,lead in [('title',19,23),('h',12,16),('body',9,12),('cell',8,10.5),('head',8,10.5),('small',8,10.5)]}
def p(s,k='body'):return Paragraph(s,styles[k])
def duration(s):
 days,s=divmod(int(s),86400);hours,s=divmod(s,3600);minutes,sec=divmod(s,60)
 return ' '.join(f'{v}{unit}' for v,unit in [(days,'d'),(hours,'h'),(minutes,'m'),(sec,'s')] if v) or '0s'
def name(t,lang):
 row=types[t];return langs[lang].get(row['BuildingName'],langs['EN'].get(row['BuildingName'],row['Id']))
def tbl(headers,data,widths):
 t=Table([[p(x,'head') for x in headers]]+[[p(str(x),'cell') for x in row] for row in data],colWidths=[x*mm for x in widths],repeatRows=1)
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#EEF4F8')]),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#CCD7E1')),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));return t
story=[]
for lang in ['EN','RU']:
 ru=lang=='RU'
 for chunk in [records[:15],records[15:]]:
  if story:story.append(PageBreak())
  story += [p('Power Plant upgrade time' if not ru else 'Время улучшения электростанции','title'),p('11 October 2026 | Standard levels 1-30 | One queue | No speed-up items' if not ru else '11 октября 2026 | Уровни 1-30 | Одна очередь | Без предметов ускорения')]
  story += [p('Each row is the transition from the previous PP level, with that previous level\'s minimum prerequisites already built. Step work includes ALL newly required prerequisite upgrades, counted once. The adjusted column includes research + alliance help, with no speed-up items.' if not ru else 'Строка - переход с предыдущего уровня ЭС, когда его минимальные условия уже выполнены. Работа шага включает ВСЕ новые необходимые улучшения без повторов. Скорректированный срок учитывает исследования и помощь альянса, без предметов ускорения.')]
  data=[]
  for r in chunk:
   deps='<br/>'.join(escape(name(d['type'],lang))+f" L{d['level']}" for d in r['direct_prerequisites']) or ('None' if not ru else 'Нет')
   data.append([f"{r['level']-1}&gt;{r['level']}",deps,duration(r['powerplant_seconds']),duration(r['step_base_seconds']),duration(r['step_adjusted_seconds'])+f"<br/><font size='6.5'>R {r['research_speed_bonus']*100:g}% | H {r['help_count']}</font>",duration(r['adjusted_cumulative_seconds'])])
  story.append(tbl(['Step' if not ru else 'Шаг','Required buildings' if not ru else 'Необходимые здания','PP base' if not ru else 'ЭС база','Step base, all work' if not ru else 'База шага, всё','Step with R + H' if not ru else 'Шаг с R + H','Cumulative R + H' if not ru else 'Сумма R + H'],data,[16,54,27,28,29,28]))
  story += [Spacer(1,8),p('d = days, h = hours, m = minutes, s = seconds. R = construction-speed research assumed already completed; H = full help count assumed received promptly on EACH new upgrade. Bonuses and help use only buildings already present before the step; actual prerequisite upgrades may improve them sooner. See model notes for assumptions.' if not ru else 'd - дни, h - часы, m - минуты, s - секунды. R - уже завершённые исследования скорости; H - полное число своевременных помощей на КАЖДОЕ новое улучшение. Учитываются здания, готовые до шага; новые условия могут повысить бонус раньше. Допущения описаны далее.','small')]
 story.append(PageBreak());story += [p('How to read the construction estimate' if not ru else 'Как читать сроки строительства','title')]
 story += [p('This is a timer-only planning scenario, not a personalised deadline. One continuously busy building queue; resources, unlocks and research are ready at the start of each step. It does not include speed-up items, VIP, hero bonuses, instant finish or extra builders.' if not ru else 'Это сценарий таймеров, а не личный срок. Одна непрерывно занятая очередь; ресурсы, открытия и исследования готовы к началу шага. Предметы ускорения, VIP, герои, мгновенное завершение и дополнительные строители не включены.')]
 story += [p('Research: use the highest eligible level in each new-development construction-speed/help research group, completing its research prerequisites too. Building gates must exist in the PREVIOUS step\'s route. Existing levels replace lower levels in the same group; they are not added together. R can reach 10% construction speed on this branch.' if not ru else 'Исследования: максимальный доступный уровень каждой группы новой ветки скорости/помощи, включая предшествующие исследования. Требуемые здания должны быть готовы по маршруту ПРЕДЫДУЩЕГО шага. Уровни одной группы заменяют друг друга, а не суммируются. Максимум R этой ветки - 10%.')]
 story += [p('Per-upgrade model: ceil(base seconds / (1 + R)) minus H x seconds per help; floored at zero. Example: +10% speed divides the timer by 1.10, rather than subtracting 10%. Research runs on its own queue; the table assumes it has finished beforehand, and does not add research waiting time.' if not ru else 'Для каждого улучшения: округлить вверх базовые секунды / (1 + R), затем вычесть H x секунды помощи; минимум ноль. +10% скорости делит таймер на 1,10. Исследования идут в своей очереди: таблица предполагает, что они завершены заранее; ожидание исследований не добавлено.')]
 story += [p('Help model from configured benefits: cap = 6 + Comms Outpost level benefit; seconds/help = 20 + Comms time benefit + eligible help research (up to 30s). No Comms in the previous minimum route means H = 0. This is a fixed-seconds client approximation: actual server help traces and arrival times are not observed. No unverified 1%-of-remaining-time rule is applied.' if not ru else 'Модель помощи по настройкам: лимит = 6 + бонус уровня Comms Outpost; секунд за помощь = 20 + бонус времени Comms + исследование помощи (до 30с). Если Comms ещё нет в минимальном маршруте, H = 0. Это приближение по фиксированным секундам клиента: серверные значения и время прихода помощи не наблюдались.')]
 story += [p('Totals to PP30: '+duration(records[-1]['powerplant_cumulative_seconds'])+' PP-only base; '+duration(records[-1]['all_required_work_seconds'])+' including all base prerequisites; '+duration(records[-1]['adjusted_cumulative_seconds'])+' in this research/help single-queue scenario.' if not ru else 'Итоги до ЭС30: '+duration(records[-1]['powerplant_cumulative_seconds'])+' база только ЭС; '+duration(records[-1]['all_required_work_seconds'])+' база со всеми условиями; '+duration(records[-1]['adjusted_cumulative_seconds'])+' в данном сценарии исследований/помощи.')]
 story += [p('Sources: manifest-verified buildings, research_main, benefits_base and benefit_calc, audited 11 Oct 2026; native construction getter + BenefitFormulaDouble. BuildTimeD/ReqBuildingD non-legacy branch; account branch and server patches unobserved. PP31+ and level-30 star stages excluded. Existing extra buildings/research can shorten your route; resource or research delays can lengthen it.' if not ru else 'Источники: buildings, research_main, benefits_base, benefit_calc, проверенные по манифесту 11.10.2026; нативные функции строительства и BenefitFormulaDouble. Новая ветка BuildTimeD/ReqBuildingD; ветка аккаунта и серверные патчи не наблюдались. ЭС31+ и звёздные этапы 30 исключены. Дополнительные готовые здания могут сократить путь; ожидание ресурсов/исследований увеличивает его.','small')]
 story.append(PageBreak());story += [p('Daily construction-usable speed-up income' if not ru else 'Ежедневный доход ускорений строительства','title')]
 lo,hi=income['core_hours_per_day']
 story += [p(f'<b>Worked active-F2P scenario: {lo:.1f}-{hi:.1f} hours/day, construction + universal combined.</b> Reward sizes are configuration-backed; daily claim counts below are explicit planning assumptions, not a measured population average. This scenario requires access to the level-10 period fiend reward branch.' if not ru else f'<b>Расчётный сценарий активного F2P: {lo:.1f}-{hi:.1f} часа в день, строительные + универсальные.</b> Размеры наград взяты из настроек; количество получений ниже - явные допущения, а не измеренное среднее. Нужен доступ к указанной ветке наград врага уровня 10.')]
 data=[['Daily activity / Ежедневные задания','15m construction / строительные','One full daily track / Одна полная цепочка','15m'],['Level-10 fiend / Враг ур.10','60m construction per eligible personal claim / за подходящую личную награду','3-5 eligible claims/day / 3-5 наград в день','3-5h'],['Alliance rally chests / Сундуки рейдов альянса','0.525m expected per chest / ожидаемо за сундук','20-60 chests/day / сундуков в день','10.5-31.5m'],['Alliance Duel / Дуэль альянсов','25m construction + 25m universal, full 9-box ladder / полная цепочка 9 сундуков','0-1 full eligible ladder/day / полных цепочек в день','0-50m']]
 story.append(tbl(['Source / Источник','Verified unit / Награда','Assumed daily activity / Допущение','Daily gain / Доход'],data,[37,61,55,29]))
 story += [Spacer(1,8),p(f'At this scenario: {lo*7:.1f}-{hi*7:.1f}h per 7 days; {lo*30:.0f}-{hi*30:.0f}h per 30 days. Universal items are counted only if saved for construction. Ordinary timer progress (24h/day for one busy queue) is separate and is NOT speed-up income.' if not ru else f'В сценарии: {lo*7:.1f}-{hi*7:.1f}ч за 7 дней; {lo*30:.0f}-{hi*30:.0f}ч за 30 дней. Универсальные предметы считаются только при использовании на строительство. Обычный таймер (24ч/день занятой очереди) отдельно и НЕ является доходом предметов.')]
 story += [p('Important reward gates: the selected gve_boss_new_period_10_1/_2 rows each reference a guaranteed 60m construction item; they are alternative claim-count bands, not two rewards to add together. Other fiend levels, seasons and reward paths differ. If your eligible claim count is zero, remove the entire 3-5h line. Daily activity has 12 alternative tracks: choose one, never add all 12.' if not ru else 'Условия наград: выбранные gve_boss_new_period_10_1/_2 дают по 60м строительства; это альтернативные диапазоны числа наград, их нельзя складывать. Другие уровни, сезоны и ветки отличаются. Если подходящих наград нет, убрать всю строку 3-5ч. В ежедневных заданиях 12 альтернативных цепочек: считать только одну.','small')]
 story += [p('Random chest expectation uses chance / 10,000 and the midpoint of the configured item-count range; a particular day can give less or more. Training, research and healing items are excluded, including Reservoir healing rewards. Free VIP packages contain no direct construction/universal item in the audited rows.' if not ru else 'Ожидаемый случайный доход: шанс / 10 000 и середина диапазона количества. За конкретный день может выпасть меньше или больше. Обучение, исследования и лечение исключены, включая лечение за Reservoir. В проверенных бесплатных VIP-пакетах нет прямых строительных/универсальных предметов.','small')]
 story.append(PageBreak());story += [p('Additional events, gifts and intel' if not ru else 'Дополнительные события, подарки и разведка','title')]
 story += [p('These additions are NOT included in the 3.4-6.6h/day core scenario. They prevent a false promise of a daily reward when a source is conditional, random or not yet linked to your active reward path.' if not ru else 'Эти добавки НЕ включены в основной сценарий 3,4-6,6ч/день: источники условны, случайны либо ещё не связаны с активной веткой наград аккаунта.')]
 data=[['Intel dig tables / Таблицы разведки','6.49-14.76m construction per matching dig, depending on table tier / за соответствующую разведку','6-10 matching digs/day adds about 0.65-2.46h/day. Active quest mapping unverified; do not apply to every intel mission. / 6-10 заданий добавляют 0,65-2,46ч; связь с текущими заданиями не подтверждена.'],['Package gifts / Подарки пакетов','Tier 1-5: 1.125, 2.25, 3.75, 6, 9.375m construction expected per chest / ожидаемо за сундук','F2P can receive others\' gifts; count actual tiers and boxes. No assumed paid-member gift volume. / Учитывать реальные уровни и количество полученных подарков.'],['Fiend Aid Crates / Сундуки помощи','Official update: guaranteed 5m universal per crate, possible 15m / гарантировано 5м универсальных, возможны 15м','Add at least 5m x crates actually received; daily cap/path not verified. / Добавить минимум 5м x реально полученные сундуки; лимит не подтверждён.'],['Arcadian / State Clash','Official update adds 20h universal to eligible battle-phase solo progress / 20ч универсальных в подходящих личных наградах','Average as 20h x payouts / cycle days. Example: one earned payout per 28 days = +0.71h/day; cadence is an assumption. / Пример: одна награда за 28 дней = +0,71ч/день, период условный.']]
 story.append(tbl(['Source / Источник','Reward / Награда','How to add / Как добавить'],data,[36,64,82]))
 story += [Spacer(1,8),p('Practical estimate: use the core 3.4-6.6h/day only when the stated fiend claims are available; matching dig rewards would bring the worked range to roughly 4.1-9.1h/day, before other gifts/events. It is an activity-based budget, not a guarantee. No purchases, diamond spending, newcomer rewards or saved stock counted.' if not ru else 'Практический ориентир: 3,4-6,6ч/день только при доступности указанных наград врага; подходящие разведки дают примерно 4,1-9,1ч/день до прочих подарков/событий. Это бюджет по активности, не гарантия. Покупки, алмазы, одноразовые награды новичка и старые запасы не считаются.')]
 story += [p('To calibrate your account: capture one level-10 fiend personal reward mail, your intel reward screen, and seven days of newly earned construction/universal items (including items spent). Record event names and gift tiers. This confirms which reward branch and daily counts apply.' if not ru else 'Для уточнения: одно письмо личной награды врага ур.10, экран награды разведки и семь дней новых строительных/универсальных предметов с учётом потраченных. Записать события и уровни подарков: это подтвердит ветку и число наград.')]
 story += [p('Sources: manifest-verified itemlist, daily_reward, drop_group, drop_main, gve_new_reward and activity_alliance_1v1_duel_box. Official <link href="https://tilesurvivegame.com/en/blog/1047">v2.5.500 patch notes, 26 June 2026</link>: Aid Crates and 20h event rewards. Source tables are local client evidence, not a live server guarantee.' if not ru else 'Источники: проверенные itemlist, daily_reward, drop_group, drop_main, gve_new_reward, activity_alliance_1v1_duel_box. Официальные <link href="https://tilesurvivegame.com/en/blog/1047">изменения v2.5.500 от 26.06.2026</link>: сундуки помощи и 20ч за события. Таблицы клиента не гарантируют текущие серверные награды.','small')]

def footer(c,d):
 c.setFont('Body',8);c.drawString(14*mm,8*mm,'Tiles Survive | EN / RU | 2026-10-11');c.drawRightString(196*mm,8*mm,str(d.page))
SimpleDocTemplate(str(out),pagesize=A4,leftMargin=14*mm,rightMargin=14*mm,topMargin=14*mm,bottomMargin=17*mm).build(story,onFirstPage=footer,onLaterPages=footer)
print('PDF',out,'PP30 hours',records[-1]['powerplant_cumulative_seconds']/3600,'adjusted days',adjusted_total/86400)
