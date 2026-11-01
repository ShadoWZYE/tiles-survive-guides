"""Append an evidence-bounded EN/RU city-buff report to the capture guide.

Retains the existing English/Russian capture pages; repeat runs replace the
supplement instead of accumulating copies. Raw game sources remain private.
"""
from pathlib import Path
import hashlib,json,sys
from io import BytesIO
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work/hero-extraction'))
from refresh_hero_data import verified_tables
from decode_cfg import decode_table
from decode_language_pack import decode_language_pack
from audit_city_stacking import city_stacking_proof,eligibility_boundary_proof
import pymupdf
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,PageBreak

OUT=ROOT/'docs/reports/Tiles-Survive-Metropolis-Alliance-Attack-Guide.pdf'
AUDIT=ROOT/'outputs/City-Buff-Stacking-Audit-2026-10-29.json'
PRIVATE=ROOT/'tmp/city-buffs-2026-10-26'
ASSETS=Path('C:/Program Files (x86)/FunPlus/Tiles Survive/GameData/GameAssets')
NAVY=colors.HexColor('#0B1E36');PANEL=colors.HexColor('#132E50')
CYAN=colors.HexColor('#42D8D0');WHITE=colors.HexColor('#F5F9FF');MUTED=colors.HexColor('#BDD0E8')
PAGE=landscape(A4)


def audit():
    PRIVATE.mkdir(parents=True,exist_ok=True)
    pack=(ASSETS/'BinaryConfigPack.ss').read_bytes();manifest=ASSETS/'BinaryConfig/BinVersionList_Realtime.json'
    tables={};hashes={}
    for name,(_,raw) in verified_tables(pack,json.loads(manifest.read_bytes()),{'analysis_center','analysis_center_position','benefits','buff'},manifest.parent).items():
        p=PRIVATE/(name+'.cfg');p.write_bytes(raw);tables[name]=decode_table(p)['rows'];hashes[name]=hashlib.sha256(raw).hexdigest()
    lang=decode_language_pack(ASSETS/'Languages/InGameBin/language_en.json.bin.enc')
    benefits={r['InternalId']:r for r in tables['benefits']};buffs={r['InternalId']:r for r in tables['buff']}
    selected=[]
    for r in tables['analysis_center']:
        parts=r['Id'].split('_')
        if len(parts)!=4 or parts[:2]!=['analysis','center'] or not parts[2].isdigit():continue
        selected.append({'id':r['Id'],'configuration_id':r['InternalId'],'level':r['Level'],'name':lang.get(r['Name'],r['Name']),
            'benefits':[{'id':v['benefit_id'],'name':benefits[v['benefit_id']]['Id'],'value':v['benefit_value']} for v in r['Benefit']],
            'alternative_post_merge_buff':{k:buffs[r['BenefitCombineserver']][k] for k in ['Id','Benefit','Value']}})
    assert len(selected)==17
    source_methods=[('AllianceBenefit','Parse',0x1EE6B50),('AllianceExtDatabaseCell','get_AllianceBenefitDict',0x1E11720),
                    ('BenefitUtils','UdpateBenefits',0x38F9120),('BenefitItem','Merge',0x38F09C0),
                    ('AnalysisCenterModule','IsBenefitHad',0x38065B0)]
    native=json.loads((ROOT/'tmp/native-293/verified/method-index.json').read_text(encoding='utf-8'))
    for t,n,rva in source_methods:assert any(x['type']==t and x['name']==n and x['rva']==rva for x in native)
    binary=Path('C:/Program Files (x86)/FunPlus/Tiles Survive/ngame/2.6.300.293/GameAssembly.dll')
    digest=hashlib.sha256(binary.read_bytes()).hexdigest()
    from unpack_client_lzma import CURRENT_SHA256
    if digest!=CURRENT_SHA256:raise ValueError('Re-audit methods for the installed binary before publishing')
    result={'date':'2026-10-29','client_build':'2.6.300.293','native_sha256':digest,
        'config_pack_sha256':hashlib.sha256(pack).hexdigest(),'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'table_sha256':hashes,'base_map_cities':selected,
        'alliance_scope_localization':{'key':'alliance_area_desc','value':lang['alliance_area_desc']},
        'stacking_conclusion':{'distinct_stats':'The supplied live UI displays the five different stats separately.',
            'duplicate_same_configuration_id':'Deduplicated by the static local client method.',
            'distinct_configuration_ids_same_stat':'Conditional addition in the local method only; both cities must survive server eligibility and use the expected active configuration. NOT confirmed live.',
            'same_level_and_same_stat':'The supplied live UI shows two different configured Lv.5 groups yielding only +10% training in total.',
            'generic_merge_adds_values':True,'city_specific_rule_verified':False,
            'supersedes':'The 26 October claim that one Lv.5 city from each group guarantees +20% is withdrawn.'},
        'native_base_paths':[{'type':t,'method':n,'rva':hex(r)} for t,n,r in source_methods],
        'evidence_boundary':'Static arithmetic is conditional on server eligibility and active configuration. Live UI contradicts the previous +20% conclusion. Exact server rule and actual training timer effect are not measured.',
        'live_check':{'purpose':'Observe bonus panel before/after a different-bonus city capture or an already-planned transfer, without abandoning a strategic city solely to test.',
                      'controls':'Record city coordinates, city tooltip, alliance bonus panel, time since capture and client version. Training timer measurement would distinguish display-only issues.'}}
    result['city_specific_proof']=city_stacking_proof(selected,tables['analysis_center_position'])
    result['failure_analysis']=eligibility_boundary_proof()
    owned_coordinates=[(968,488),(908,508),(1048,528),(828,588),(908,768),(968,768)]
    config_by_id={c['configuration_id']:c for c in selected}
    position_by_xy={(p['Coordinate']['x'],p['Coordinate']['y']):p for p in tables['analysis_center_position'] if p['SeasonType']=='S1' and p['AnalysisCenter']}
    owned=[]
    for xy in owned_coordinates:
        position=position_by_xy[xy];config=config_by_id[position['AnalysisCenter']]
        owned.append({'coordinates':list(xy),'configuration_id':config['configuration_id'],
                      'configuration_key':config['id'],'configured_benefits':config['benefits']})
    from audit_city_stacking import aggregate_cities
    pairs=[(f'{c["coordinates"][0]}:{c["coordinates"][1]}',c['configuration_id']) for c in owned]
    predicted=aggregate_cities(pairs,config_by_id,{})
    observed={300321:.10,301835:.02,301836:.05,300300:.20,300747:.20}
    assert predicted[300321]==.20 and all(predicted[k]==v for k,v in observed.items() if k!=300321)
    source=Path('C:/Users/Shadow/AppData/Local/Temp/codex-clipboard-4fa3a441-ec52-45ce-aafb-ecdd5c92ab31.png')
    evidence_path=ROOT/'outputs/battle-reports/City-Buffs-Observed-2026-10-29.png'
    source_bytes=source.read_bytes() if source.exists() else evidence_path.read_bytes()
    evidence_path.parent.mkdir(parents=True,exist_ok=True);evidence_path.write_bytes(source_bytes)
    scenarios=[]
    for disabled in ['908:508','908:768']:
        output=aggregate_cities(pairs,config_by_id,{disabled:0})
        assert output==observed
        scenarios.append({'hypothetical_disabled_city':disabled,'totals':output,'matches_displayed_snapshot':True,
                          'interpretation':'Reproduces observation, but no live eligibility payload was captured to establish this as the actual cause.'})
    result['live_observation']={'date_received':'2026-10-29','occupied_count':6,'city_capacity':6,
        'source':str(evidence_path.relative_to(ROOT)),'source_sha256':hashlib.sha256(source_bytes).hexdigest(),
        'owned_cities':owned,'displayed_totals':observed,'all_eligible_static_prediction':predicted,
        'discrepancy':'Training: static prediction +20%, live UI +10%. Other displayed totals agree.',
        'consistent_hypotheses':scenarios,'exact_server_rule_confirmed':False,
        'conclusion':'Use displayed +10% training for current planning. Do not infer a universal highest-only rule, cross-level stacking, or +25% maximum from this single snapshot.'}
    AUDIT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


def styles():
    fonts=Path('C:/Windows/Fonts')
    pdfmetrics.registerFont(TTFont('CitySans',str(fonts/'arial.ttf')))
    pdfmetrics.registerFont(TTFont('CityBold',str(fonts/'arialbd.ttf')))
    pdfmetrics.registerFontFamily('CitySans',normal='CitySans',bold='CityBold',italic='CitySans',boldItalic='CityBold')
    return {name:ParagraphStyle(name,fontName='CityBold' if name in ('title','h') else 'CitySans',fontSize=size,leading=leading,textColor=color,spaceAfter=space)
            for name,size,leading,color,space in [('title',20,23,WHITE,6),('h',11,14,CYAN,5),('body',9,12,WHITE,5),('small',7.6,10,MUTED,4)]}


# Public state-share content. Alliance-specific evidence stays in the separate
# local audit; it is not embedded or linked from the shareable PDF.
TEXT={
'en':{
 'title':'CITY BUFFS: STATE-WIDE STACKING CLARIFICATION',
 'sub':'Public state guide | corrected 29 October 2026 | local client 2.6.300.293',
 'answer':'<b>Correction: two Research Centers configured at +10% each do not guarantee +20% training speed.</b> A live bonus panel shows only +10% combined. The earlier unconditional +20% claim is withdrawn. Different city configuration IDs alone do not establish that both bonuses contribute.',
 'tabletitle':'Configured city bonuses (base-map reference)',
 'headers':['Level / city','Configured bonus of an individual entry'],
 'rows':[['1 - Village','Resource production OR gathering speed +5%'],['2 - Factory','Construction, research OR training speed +5%'],['3 - Town','Troop ATK, DEF OR HP +2%'],['4 - Metropolis','Resource production OR gathering speed +20%'],['5 - Research Center','Training speed +10%'],['6 - Military Base','Troop ATK, DEF OR HP +5%']],
 'tablenote':'OR denotes different city variants, not all bonuses from one city. Values are configuration references, not guaranteed additions or a verified maximum. Follow the active city tooltip and alliance bonus panel for your state/season.',
 'stacktitle':'What is established - and what is not',
 'stackheaders':['Question','Evidence status'],
 'stackrows':[['Two +10% Research Centers','Live observation: +10% combined on the bonus panel, not +20%.'],['Different bonus types','Separate stats can coexist; this does not prove same-stat stacking.'],['Same configuration ID','The inspected local method counts the same configuration once.'],['Different configuration IDs','Addition is conditional on runtime eligibility; extra effective bonus is not guaranteed.'],['Cross-level stacking / maximum','Not verified live. The former +25% training maximum is withdrawn.']],
 'scopehead':'UNAVAILABLE DATA - live eligibility record',
 'scope':'<b>Missing:</b> AllianceExt.stats_info.analysis_center at the time the bonus panel was shown. This runtime record is not available from configuration files or a screenshot. Its values and the server policy producing them are unavailable. <b>No universal cap, server bug or merge-specific stacking rule has been established.</b>',
 'mergehead':'What would establish the live cause?',
 'merge':'A time-matched decoded eligibility record, active per-city configuration IDs and client/patch version. A fresh panel after relogging plus city tooltips can help check stale display or configuration differences. Server merging alone does not prove which bonus mapping applies.',
 'testhead':'Why the earlier guidance was wrong',
 'test':'<b>Verified trace:</b> the Bonuses button calls StrongholdPage.GetCurrentBenefit. The method reads the runtime eligibility record, skips explicit zero entries, then deduplicates configuration IDs and adds surviving bonuses.<br/><b>Confirmed analysis error:</b> the reference examples assumed no city was excluded. The conditional +20% result was incorrectly presented as confirmed without the live input.<br/><b>Live cause: UNRESOLVED - UNAVAILABLE RUNTIME DATA.</b> Filtering either Research Center can reproduce +10%, but neither case is proven. The field is an input filter, not a demonstrated override of the final sum.',
 'planhead':'Guidance for every alliance',
 'plan':'Use the bonus actually displayed for planning. Do not promise extra stats from a second same-stat city without live validation. City bonuses are alliance-wide; assess territory, access and event value separately. Capture starts from a Level 1 city and expands through connected territory. Do not abandon a strategic city solely to test a buff.',
 'evidence':'Basis: manifest-verified local tables, seven hash-gated native methods and a live UI observation. Displayed totals are not independently timed training effects. This public edition omits alliance identities, city coordinates, occupation lists, capacity details and personal battle results.'},
'ru':{
 'title':'БОНУСЫ ГОРОДОВ: ПОЯСНЕНИЕ ДЛЯ ВСЕГО ШТАТА',
 'sub':'Общий гайд штата | исправлено 29 октября 2026 | локальный клиент 2.6.300.293',
 'answer':'<b>Исправление: два исследовательских центра с бонусом +10% каждый не гарантируют +20% обучения.</b> На панели игры наблюдается лишь +10% суммарно. Прежний безусловный вывод о +20% отозван. Разные ID конфигурации сами по себе не доказывают, что оба бонуса учитываются.',
 'tabletitle':'Бонусы в конфигурации базовой карты',
 'headers':['Уровень / город','Бонус одной конфигурационной записи'],
 'rows':[['1 - Деревня','Производство ресурсов ИЛИ скорость сбора +5%'],['2 - Фабрика','Строительство, исследования ИЛИ обучение +5%'],['3 - Городок','Атака, защита ИЛИ здоровье войск +2%'],['4 - Мегаполис','Производство ресурсов ИЛИ скорость сбора +20%'],['5 - Исследовательский центр','Скорость обучения +10%'],['6 - Военная база','Атака, защита ИЛИ здоровье войск +5%']],
 'tablenote':'ИЛИ означает разные варианты городов, а не все бонусы одного города. Это справочные значения, не гарантированные добавки или проверенный максимум. Ориентируйтесь на текущую подсказку города и панель бонусов в своем штате/сезоне.',
 'stacktitle':'Что установлено, а что не доказано',
 'stackheaders':['Вопрос','Статус доказательств'],
 'stackrows':[['Два центра по +10%','Наблюдение в игре: на панели всего +10%, а не +20%.'],['Разные типы бонусов','Разные параметры могут действовать одновременно. Это не доказывает сложение одного параметра.'],['Одинаковый ID конфигурации','Локальный метод учитывает одну конфигурацию один раз.'],['Разные ID конфигурации','Сложение зависит от текущих признаков активности; прибавка не гарантирована.'],['Разные уровни / максимум','В игре не проверено. Прежний максимум +25% обучения отозван.']],
 'scopehead':'ДАННЫЕ НЕДОСТУПНЫ - текущая активность',
 'scope':'<b>Отсутствуют:</b> AllianceExt.stats_info.analysis_center на момент показа панели. Эту текущую запись нельзя получить из таблиц конфигурации или снимка. Ее значения и формирующее их серверное правило недоступны. <b>Общий лимит, ошибка сервера или особое правило после слияния не доказаны.</b>',
 'mergehead':'Что установит причину в игре?',
 'merge':'Декодированная запись активности на момент показа панели, текущие ID конфигураций и версия клиента/патча. Свежая панель после перезахода и подсказки городов помогут проверить отображение и конфигурацию. Само слияние не определяет активную схему бонусов.',
 'testhead':'Почему прежняя рекомендация была неверной',
 'test':'<b>Проверенная цепочка:</b> кнопка бонусов вызывает StrongholdPage.GetCurrentBenefit. Метод читает текущую запись активности, исключает явные нули, убирает повторные ID конфигурации и складывает оставшиеся бонусы.<br/><b>Подтвержденная ошибка анализа:</b> примеры предполагали, что ни один город не исключен. Условный итог +20% ошибочно назвали подтвержденным без реальных данных.<br/><b>Причина в игре НЕ УСТАНОВЛЕНА - ТЕКУЩИЕ ДАННЫЕ НЕДОСТУПНЫ.</b> Исключение любого центра может дать +10%, но ни один вариант не доказан. Поле фильтрует входные данные, а не доказанно меняет готовую сумму.',
 'planhead':'Рекомендации для любого альянса',
 'plan':'Планируйте по бонусу на панели. Не обещайте прибавку от второго города с тем же параметром без проверки в игре. Бонусы действуют на весь альянс; отдельно оценивайте территорию, доступ и события. Начинайте захват с города 1-го уровня и расширяйтесь по смежной территории. Не бросайте важный город только ради проверки бонуса.',
 'evidence':'Основание: локальные таблицы, сверенные с манифестом, семь методов с проверкой хешей и наблюдение панели игры. Показанный итог не равен независимой проверке таймера обучения. В публичной версии нет имен альянсов, координат, списков владения, данных о лимитах и личных результатов боев.'}}


def make_supplement():
    st=styles();p=lambda s,style='body':Paragraph(s,st[style])
    def table(headers,rows):
        t=Table([[p(escape(x),'small') for x in headers]]+[[p(escape(x)) for x in row] for row in rows],colWidths=[100,278],repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#24537F')),('BACKGROUND',(0,1),(-1,-1),PANEL),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.35,colors.HexColor('#315D87')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        return t
    stream=BytesIO();doc=SimpleDocTemplate(stream,pagesize=PAGE,leftMargin=12*mm,rightMargin=12*mm,topMargin=10*mm,bottomMargin=12*mm)
    def background(c,d):
        c.setFillColor(NAVY);c.rect(0,0,*PAGE,fill=1,stroke=0)
        c.setFont('CitySans',7);c.setFillColor(MUTED);c.drawString(12*mm,5.7*mm,'Tiles Survive - City buff report - '+('English' if d.page==1 else 'Русский'))
    story=[]
    for lang in ['en','ru']:
        t=TEXT[lang]
        if story:story.append(PageBreak())
        story += [p(t['title'],'title'),p(t['sub'],'small'),p(t['answer']),Spacer(1,4)]
        left=[p(t['tabletitle'],'h'),table(t['headers'],t['rows']),Spacer(1,6),p(t['tablenote'],'small'),p(t['scopehead'],'h'),p(t['scope']),p(t['mergehead'],'h'),p(t['merge'])]
        right=[p(t['stacktitle'],'h'),table(t['stackheaders'],t['stackrows']),Spacer(1,6),p(t['testhead'],'h'),p(t['test']),p(t['planhead'],'h'),p(t['plan'])]
        columns=Table([[left,right]],colWidths=[390,390]);columns.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
        story += [columns,Spacer(1,7),p(t['evidence'],'small')]
    doc.build(story,onFirstPage=background,onLaterPages=background)
    result=pymupdf.open(stream=stream.getvalue(),filetype='pdf')
    if len(result)!=2:raise ValueError('Supplement overflow: inspect before publication')
    return result


def sanitize_capture_page(page,ru=False):
    navy=(11/255,30/255,54/255)
    blocks=page.get_text('blocks');replacements=[]
    samples=[b for b in blocks if any(x in b[4] for x in ['0.22%','0.07%','0,22%','0,07%']) and b[0]<100]
    if samples:
        y0=min(b[1] for b in samples)-24;y1=max(b[3] for b in samples)+8
        replacements.append((pymupdf.Rect(39,y0,416,y1),
          "Personal cleanup check: use the member's latest tested solo result with the same squad and troop count. Let an officer call one final hitter; do not use another player's damage as your threshold." if not ru else
          'Проверка финального удара: используйте последний проверенный урон конкретного участника тем же отрядом и числом войск. Офицер назначает одного атакующего; чужой урон не является вашим порогом.'))
    for b in blocks:
        if '26K' in b[4]:
            replacements.append((pymupdf.Rect(424,b[1]-7,801,b[3]+7),
              'Lv.4 Mega Summoner has 160 health sections; Subject No.81 has 240. A filled rally survives deeper into the section chain and benefits from rally combat modifiers. The Metropolis configuration recommends 15 participants.' if not ru else
              'У Мега-призывателя ур.4 - 160 секций здоровья, у Субъекта №81 - 240. Полный сбор дольше сохраняет боеспособность и получает боевые бонусы сборов. Конфигурация Мегаполиса рекомендует 15 участников.'))
    for rect,_ in replacements:page.add_redact_annot(rect,fill=navy)
    if replacements:
        page.apply_redactions()
        page.insert_font(fontname='statebody',fontfile='C:/Windows/Fonts/arial.ttf')
        for rect,content in replacements:
            page.draw_rect(rect,color=(49/255,93/255,135/255),fill=(19/255,46/255,80/255),width=.35)
            inset=pymupdf.Rect(rect.x0+5,rect.y0+4,rect.x1-5,rect.y1-3)
            remaining=page.insert_textbox(inset,content,fontname='statebody',fontsize=8.4,lineheight=1.25,color=(.96,.98,1))
            if remaining<0:raise ValueError('Public tactical text overflow')


def main():
    audit();supplement=make_supplement();original=pymupdf.open(OUT)
    backup=PRIVATE/'capture-guide-before-city-buffs.pdf'
    if not backup.exists():backup.write_bytes(OUT.read_bytes())
    else:
        original.close();original=pymupdf.open(backup)
    if len(original)==2:english,russian=0,1
    elif len(original)==4 and 'CITY BUFFS:' in original[1].get_text():english,russian=0,2
    else:raise ValueError('Unexpected guide layout; preserve it and select the base pages explicitly')
    sanitize_capture_page(original[english]);sanitize_capture_page(original[russian],ru=True)
    combined=pymupdf.open()
    for source,index in [(original,english),(supplement,0),(original,russian),(supplement,1)]:combined.insert_pdf(source,from_page=index,to_page=index)
    for i,page in enumerate(combined):
        w,h=page.rect.width,page.rect.height
        page.add_redact_annot(pymupdf.Rect(w-118,h-27,w-25,h-7),fill=(11/255,30/255,54/255));page.apply_redactions()
        page.insert_font(fontname='cityfooter',fontfile='C:/Windows/Fonts/arial.ttf')
        page.insert_textbox(pymupdf.Rect(w-118,h-24,w-34,h-7),f'Page {i+1}/4',fontname='cityfooter',fontsize=7,color=(189/255,208/255,232/255),align=2)
    combined.set_metadata({'title':'Metropolis Capture Guide and City Buff Stacking Report - English and Russian','author':'Tiles Survive state-wide guide','subject':'Captured-city bonuses, stacking evidence and verification limits; 29 October 2026'})
    final=PRIVATE/'updated-capture-guide.pdf';combined.save(final,garbage=4,deflate=True);combined.close();original.close();supplement.close()
    check=pymupdf.open(final)
    assert len(check)==4 and 'CITY BUFFS:' in check[1].get_text() and 'БОНУСЫ ГОРОДОВ' in check[3].get_text()
    check.close();OUT.write_bytes(final.read_bytes());print(OUT)


if __name__=='__main__':main()
