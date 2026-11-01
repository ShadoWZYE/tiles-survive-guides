"""Render the S1 city regions from manifest-verified client tables.

Borders follow MapPieceId.MapAreaId, never nearest-city/Voronoi estimates.
Capture intentions come from the user's screenshots, not current ownership.
"""
from pathlib import Path
from collections import Counter, defaultdict
from xml.sax.saxutils import escape
import csv
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'work/hero-extraction'))
from refresh_hero_data import verified_tables
from decode_cfg import decode_table
from decode_language_pack import decode_language_pack

ASSETS = Path('C:/Program Files (x86)/FunPlus/Tiles Survive/GameData/GameAssets')
PRIVATE = ROOT / 'tmp/state-map-2026-10-26'
OUT = ROOT / 'outputs/state-map'
TARGETS = {(828, 588): 1, (1108, 468): 2, (908, 768): 3,
           (968, 768): 4, (968, 488): 5, (1048, 528): 6}
VAN = {(508,588), (548,408), (648,328), (428,328), (328,188), (468,248)}
ALL = {(848,328), (668,248), (868,248), (908,508), (808,188), (948,188)}
RUS = {(868,988), (648,948), (388,988), (728,1068), (968,1068), (1008,1128)}
ECL = {(668,828), (408,828), (328,748), (248,848), (248,668), (168,628)}
TCE = {(308,468), (408,528), (248,488), (248,348), (168,348), (168,488)}
CLAIMS = {'VeD':set(TARGETS), 'VAN':VAN, 'ALL':ALL, 'rus':RUS, 'ECL':ECL, 'TCE':TCE}
REGION_COLORS = {'VeD':'#1764b5','VAN':'#8c4c86','ALL':'#8a622b','rus':'#347358','ECL':'#236b79','TCE':'#98483b'}
FLAG_COLORS = {'VeD':'#42bcff','VAN':'#ef9ee1','ALL':'#ffce70','rus':'#86e6a9','ECL':'#89ecf7','TCE':'#ffb399'}
NAMES = ['','Village','Factory','Town','Metropolis','Research Center','Military Base']
RU_NAMES = ['', 'Деревня', 'Фабрика', 'Город', 'Метрополис', 'Научный центр', 'Военная база']
BENEFITS = {300300: ('Resource production','Производство ресурсов'),
            300747: ('Gathering speed','Скорость сбора'),
            300314: ('Construction speed','Скорость строительства'),
            300484: ('Research speed','Скорость исследований'),
            300321: ('Training speed','Скорость обучения'),
            301835: ('Troop ATK','Атака войск'),
            301836: ('Troop DEF','Защита войск'),
            301837: ('Troop HP','Здоровье войск')}
COLORS = ['', '#bdd4dd', '#8ddac0', '#e5d684', '#ecaa7c', '#c1a0eb', '#f5cf6c']


def project(x, y):
    # Screenshot-matched orientation: X up/right, Y up/left.
    return (1600 + (x-y)*1.16, 2260 - (x+y)*.77)


def boundary(cells):
    """Cancel shared edges; trace closed rings including any holes."""
    edges = set()
    for x, y in cells:
        corners = [(x,y),(x+1,y),(x+1,y+1),(x,y+1)]
        for a,b in zip(corners, corners[1:]+corners[:1]):
            if (b,a) in edges: edges.remove((b,a))
            else: edges.add((a,b))
    nxt = defaultdict(set)
    for a,b in edges: nxt[a].add(b)
    rings = []
    while nxt:
        start = min(nxt); p = start; ring = [p]
        while True:
            q = min(nxt[p]); nxt[p].remove(q)
            if not nxt[p]: del nxt[p]
            p = q
            if p == start: break
            ring.append(p)
        simple = []
        for i,p in enumerate(ring):
            a,b = ring[i-1],ring[(i+1)%len(ring)]
            if (p[0]-a[0])*(b[1]-p[1]) != (p[1]-a[1])*(b[0]-p[0]): simple.append(p)
        rings.append(simple)
    return rings


def path(cells):
    parts=[]
    rings=boundary(cells)
    area=sum(sum(x*yy-xx*y for (x,y),(xx,yy) in zip(r,r[1:]+r[:1]))/2 for r in rings)
    assert area==len(cells), 'Region border tracing changed the source tile area'
    for ring in rings:
        pts=[project(x*10,y*10) for x,y in ring]
        parts.append('M'+'L'.join(f'{x:.1f},{y:.1f}' for x,y in pts)+'Z')
    return ''.join(parts)


def load():
    PRIVATE.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    pack=(ASSETS/'BinaryConfigPack.ss').read_bytes()
    manifest=ASSETS/'BinaryConfig/BinVersionList_Realtime.json'
    names={'map_area_id','map_piece_id','analysis_center','analysis_center_position'}
    tables={}; hashes={}
    for name,(_,raw) in verified_tables(pack,json.loads(manifest.read_bytes()),names,manifest.parent).items():
        p=PRIVATE/(name+'.cfg');p.write_bytes(raw)
        tables[name]=decode_table(p)['rows']; hashes[name]=hashlib.sha256(raw).hexdigest()
    assert set(tables)==names
    # Verify the actual 10 tiles/piece and 130 pieces/axis constants, statically.
    native=(ROOT/'tmp/native-293/verified/native-rva-image.bin').read_bytes()
    constants=native[0x244b0d0:0x244b15d]
    assert bytes.fromhex('c7010a000000') in constants
    assert bytes.fromhex('c7410882000000') in constants
    lang=decode_language_pack(ASSETS/'Languages/InGameBin/language_en.json.bin.enc')
    cfg={v['InternalId']:v for v in tables['analysis_center']}
    pos={v['InternalId']:v for v in tables['analysis_center_position']
         if v['SeasonType']=='S1' and v['AnalysisCenter']}
    areas={v['InternalId']:v for v in tables['map_area_id'] if v['AreaSeason']=='S1'}
    pieces=tables['map_piece_id']; lookup={(v['PieceX']-1,v['PieceY']-1):v for v in pieces}
    assert len(lookup)==130*130
    cells=defaultdict(list)
    for xy,v in lookup.items():
        if v['MapAreaId']: cells[v['MapAreaId']].append(xy)
    assert set(cells)==set(areas)
    cities=[]
    for aid,a in areas.items():
        p=pos[a['AnalysisCenterPosition']];c=cfg[p['AnalysisCenter']]
        x,y=p['Coordinate']['x'],p['Coordinate']['y']
        assert lookup[(x//10,y//10)]['MapAreaId']==aid
        order=TARGETS.get((x,y))
        claims=[tag for tag,coords in CLAIMS.items() if (x,y) in coords]
        alliance=' / '.join(claims)
        bs=[{'id':v['benefit_id'],'value':v['benefit_value'],
             'en':BENEFITS[v['benefit_id']][0], 'ru':BENEFITS[v['benefit_id']][1]} for v in c['Benefit']]
        cities.append({'position_id':p['InternalId'],'area_id':aid,'area_code':a['Id'],
                       'config_id':c['InternalId'],'config_key':c['Id'],'level':c['Level'],
                       'name':lang[c['Name']],'ru':RU_NAMES[c['Level']], 'x':x,'y':y,
                       'confirmed_owner':'ECL' if (x,y)==(668,828) else 'VAN' if (x,y)==(328,188) else None,'ownership_reported':'2026-10-28' if (x,y)==(668,828) else '2026-10-29' if (x,y)==(328,188) else None,'plan':alliance,'claims':claims,'contested':len(claims)>1,'order':order,'benefits':bs,'pieces':len(cells[aid])})
    cities.sort(key=lambda c:(c['level'],c['y'],c['x']))
    assert Counter(c['level'] for c in cities)=={1:48,2:28,3:16,4:9,5:6,6:3}
    for tag,coords in CLAIMS.items():
        assert sum(tag in c['claims'] for c in cities)==len(coords)
    assert not any(c['contested'] for c in cities)
    evidence={'client_build':'2.6.300.293','layout':'S1/base','state_label':'1005 (screenshots)',
              'table_sha256':hashes,'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
              'geometry':'130 x 130 map pieces; each piece spans 10 x 10 world coordinates. Polygon edges from MapAreaId.',
              'native_scale_proof':{'method':'PieceTintManager..cctor','rva':'0x244b0d0',
                                    'body_sha256':hashlib.sha256(constants).hexdigest(),'tiles_per_piece':10,'cell_width':130},
              'updated':'2026-10-29','contested_regions':[{'x':c['x'],'y':c['y'],'claims':c['claims']} for c in cities if c['contested']],
              'claim_counts':{tag:sum(tag in c['claims'] for c in cities) for tag in CLAIMS},'city_count':len(cities),'region_count':len(areas),'mapped_region_pieces':sum(map(len,cells.values())),
              'target_identification':'Initial plans matched screenshot marker beams and annotated region circles. Current user corrections override the initial screenshot allocation. VeD target number 2 now marks the newly assigned Factory 1108:468, replacing transferred Research Center 908:508; numbers identify current targets, not a capture route.',
              'allocation_changes_2026_10_29':[
                  {'coordinates':[408,528],'from':'VAN','to':None,'reason':'Unclaimed Research Center removed from VAN plan'},
                  {'coordinates':[908,508],'from':'VeD','to':'ALL','reason':'Explicit reassignment'},
                  {'coordinates':[688,188],'from':'ALL','to':None,'reason':'Replaced in ALL plan'},
                  {'coordinates':[1108,468],'from':None,'to':'VeD','reason':'Explicit addition'},
                  {'coordinates':[328,188],'from':None,'to':'VAN','reason':'Ownership confirmed by supplied city tooltip screenshot'}],
              'latest_assignment_update':{'date':'2026-10-29','TCE':[[308,468],[408,528],[248,488],[248,348],[168,348],[168,488]],'ECL':[[248,848]],'note':'Assignments replace previous claims at those coordinates; no competing claims retained for explicit transfers.'},
              'ownership':'Planned claims except Military Base 668:828, reported captured by ECL by the user on 28 October. Factory 328:188 is confirmed owned by VAN in the 29 October screenshot. No live ownership feed.',
              'projection':'Isometric diagram, X up/right, Y up/left; terrain textures and camera perspective are not reconstructed.',
              'stacking':'Per-city configured bonuses are not guaranteed additions. Live 29 October observation: 908:508 and 908:768 together display only +10% training. Static addition depends on live eligibility and active mapping; effective stacking remains unresolved.',
              'cities':cities}
    (OUT/'State-1005-Cities.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    with (OUT/'State-1005-Cities.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['Level','City','X','Y','Alliance claims','Confirmed owner','Ownership reported','Contested','Screenshot marker','Region ID','Buff group','Base-map bonus'])
        for c in cities:w.writerow([c['level'],c['name'],c['x'],c['y'],c['plan'],c['confirmed_owner'],c['ownership_reported'],'Yes' if c['contested'] else 'No',c['order'],c['area_code'],c['config_key'],
                                   '; '.join(f"{v['en']} +{v['value']*100:g}%" for v in c['benefits'])])
    return cities,cells,lookup,evidence


def render(cities,cells,lookup,ru=False):
    text=lambda en,other: other if ru else en
    s=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3200 2560" width="3200" height="2560" role="img" aria-label="State 1005 city capture plan">',
       '<style>text{font-family:Segoe UI,Arial,sans-serif}.city{cursor:pointer}.region{cursor:pointer}.dim{opacity:.12}.label{paint-order:stroke;stroke:#102332;stroke-width:5px;stroke-linejoin:round}</style>',
       '<defs><pattern id="contested" width="26" height="26" patternUnits="userSpaceOnUse" patternTransform="rotate(35)"><rect width="26" height="26" fill="#682c3a"/><rect width="10" height="26" fill="#e66b78"/></pattern></defs>',
       '<rect width="3200" height="2560" fill="#0c1926"/>',
       '<text x="95" y="90" fill="#f2f7fc" font-size="49" font-weight="700">'+text('STATE 1005 · CITY CAPTURE PLAN','ШТАТ 1005 · ПЛАН ЗАХВАТА ГОРОДОВ')+'</text>',
       '<text x="95" y="135" fill="#a5bfce" font-size="24">'+text('110 cities · exact client region boundaries · S1 / base map','110 городов · границы регионов из файлов игры · базовая карта S1')+'</text>']
    noncity=[xy for xy,v in lookup.items() if not v['MapAreaId'] and v['LevelId']!=0]
    s.append(f'<path d="{path(noncity)}" fill="#294c43" stroke="#587567" stroke-width="2"/>')
    for c in cities:
        color='url(#contested)' if c['contested'] else REGION_COLORS.get(c['plan'],['#6b7e82','#728589','#778b8e'][c['area_id']%3])
        stroke='#ff9da8' if c['contested'] else FLAG_COLORS.get(c['plan'],'#e1e9df')
        s.append(f'<path class="region" data-area="{c["area_id"]}" data-level="{c["level"]}" d="{path(cells[c["area_id"]])}" fill="{color}" stroke="{stroke}" stroke-width="{4 if c["plan"] else 2.4}" stroke-linejoin="round"/>')
    # Reference grid at 200-coordinate intervals; region lines remain stronger.
    for i in range(200,1300,200):
        for a,b in [((i,0),(i,1300)),((0,i),(1300,i))]:
            x,y=project(*a);xx,yy=project(*b)
            s.append(f'<path d="M{x},{y}L{xx},{yy}" stroke="#d1e2ed" opacity=".09" stroke-dasharray="6 8" pointer-events="none"/>')
    # Reserve marker/coordinate boxes before placing flags, so flags cannot hide cities.
    occupied=[]; flags=[]
    for c in cities:
        x,y=project(c['x'],c['y']);r=15 if c['level']<4 else 19
        occupied.extend([(x-r-4,y-r-4,x+r+4,y+r+4),(x-57,y+r+6,x+57,y+r+29)])
    # All markers share the exact world coordinate, independent of title length.
    for c in cities:
        x,y=project(c['x'],c['y']); r=15 if c['level']<4 else 19
        title=f"L{c['level']} {c['name']} {c['x']}:{c['y']} | {c['config_key']}"
        s.append(f'<g class="city" tabindex="0" data-area="{c["area_id"]}" data-level="{c["level"]}" transform="translate({x:.1f} {y:.1f})"><title>{escape(title)}</title>')
        s.append(f'<circle r="{r+3}" fill="#102332"/><circle r="{r}" fill="{COLORS[c["level"]]}"/>')
        s.append(f'<text text-anchor="middle" y="6" font-size="20" font-weight="800" fill="#102332">{c["level"]}</text>')
        s.append(f'<text class="label" text-anchor="middle" y="{r+24}" font-size="19" fill="#fff">{c["x"]}:{c["y"]}</text>')
        if c['plan']:
            t=('! ' if c['contested'] else '')+(f'VeD #{c["order"]}' if c['plan']=='VeD' else c['plan'])
            w=max(74,len(t)*13+16)
            candidates=[(0,-70),(-w,-70),(32,-30),(-w-32,-30),(32,42),(-w-32,42),(0,-100),(-w,-100)]
            def score(offset):
                dx,dy=offset;box=(x+dx-3,y+dy-3,x+dx+w+3,y+dy+33)
                return sum(max(0,min(box[2],b[2])-max(box[0],b[0]))*max(0,min(box[3],b[3])-max(box[1],b[1])) for b in occupied)
            dx,dy=min(candidates,key=score)
            occupied.append((x+dx-3,y+dy-3,x+dx+w+3,y+dy+33))
            fill='#ff9da8' if c['contested'] else FLAG_COLORS[c['plan']]
            flags.append(f'<g pointer-events="none" transform="translate({x:.1f} {y:.1f})"><path d="M0,-{r}L{dx},{dy+30}" stroke="#fff" stroke-width="2.5"/><rect x="{dx}" y="{dy}" width="{w}" height="30" rx="5" fill="{fill}"/><text x="{dx+8}" y="{dy+22}" font-size="21" font-weight="800" fill="#102332">{t}</text></g>')
        s.append('</g>')
    s.extend(flags)
    x,y=project(650,650)
    s += [f'<path d="M{x},{y-25}l22,25 -22,25 -22,-25Z" fill="#a1cba4" stroke="#e0efcd" stroke-width="3"/>',
          f'<text class="label" x="{x}" y="{y+52}" text-anchor="middle" fill="#c9e6ce" font-size="22">'+text('Arcadian Domain','Аркадийская область')+'</text>']
    # Information panels occupy the empty corners around the isometric state.
    s.append('<g fill="#d8e5ee"><text x="105" y="226" font-size="29" font-weight="700">'+text('PLANNED ALLOCATION','ПЛАН РАСПРЕДЕЛЕНИЯ')+'</text>')
    legend=[(REGION_COLORS[tag],f'{tag} · {len(coords)} '+text('claims','заявки')) for tag,coords in CLAIMS.items()]
    legend += [('#728589',text('Grey · no claim assigned','Серый · без заявки'))]
    for i,(color,label) in enumerate(legend):
        yy=275+i*45;s.append(f'<rect x="105" y="{yy-23}" width="30" height="28" rx="5" fill="{color}" stroke="#cfe4e8"/><text x="150" y="{yy}" font-size="24">{label}</text>')
    s.append('<text x="105" y="613" font-size="21" fill="#a5bfce">'+text('ECL holds 668:828 · no contested claims.','ECL владеет 668:828 · спорных заявок нет.')+'</text></g>')
    s.append('<g fill="#d8e5ee"><text x="2250" y="215" font-size="29" font-weight="700">'+text('CITY LEVELS','УРОВНИ ГОРОДОВ')+'</text>')
    for level in range(1,7):
        yy=255+level*44
        s.append(f'<circle cx="2270" cy="{yy-8}" r="15" fill="{COLORS[level]}"/><text x="2270" y="{yy-2}" text-anchor="middle" font-size="20" font-weight="700" fill="#102332">{level}</text><text x="2300" y="{yy}" font-size="24">{RU_NAMES[level] if ru else NAMES[level]} · {sum(c["level"]==level for c in cities)}</text>')
    s.append('</g><g fill="#d8e5ee"><text x="105" y="2040" font-size="29" font-weight="700">'+text('VeD · NUMBERED TARGETS','VeD · НОМЕРА ЦЕЛЕЙ')+'</text>')
    for c in sorted([v for v in cities if v['plan']=='VeD'],key=lambda c:c['order']):
        yy=2058+c['order']*45
        label=f"{c['order']}. L{c['level']} {c['ru'] if ru else c['name']} · {c['x']}:{c['y']}"
        s.append(f'<text x="105" y="{yy}" font-size="24">{label}</text>')
    s.append('</g><g fill="#a5bfce"><text x="2250" y="2120" font-size="26">'+text('ISOMETRIC COORDINATES','ИЗОМЕТРИЧЕСКИЕ КООРДИНАТЫ')+'</text>')
    for label,a,b in [('X',(2470,2290),(2610,2197)),('Y',(2470,2290),(2330,2197))]:
        s.append(f'<path d="M{a[0]},{a[1]}L{b[0]},{b[1]}" stroke="#a5bfce" stroke-width="4"/><circle cx="{b[0]}" cy="{b[1]}" r="5" fill="#a5bfce"/><text x="{b[0]}" y="{b[1]-15}" font-size="25">{label} +</text>')
    s.append('</g><text x="105" y="2480" fill="#a5bfce" font-size="23">'+text('Client 2.6.300.293 · 29 Oct 2026 · Borders reconstructed from 14,200 map pieces. No inferred terrain.','Клиент 2.6.300.293 · 29 октября 2026 · Границы по 14 200 фрагментам карты. Рельеф не воспроизводится.')+'</text></svg>')
    return ''.join(s)


def main():
    cities,cells,lookup,evidence=load()
    svgs={}
    for locale in ['EN','RU']:
        svgs[locale]=render(cities,cells,lookup,locale=='RU')
        (OUT/f'State-1005-Capture-Map-{locale}.svg').write_text(svgs[locale],encoding='utf-8')
    template=(ROOT/'scripts/state_map.template.html').read_text(encoding='utf-8')
    payload=json.dumps({'cities':cities,'svgs':svgs},ensure_ascii=False).replace('</','<\\/')
    (OUT/'State-1005-Interactive-Map.html').write_text(template.replace('__MAP_DATA__',payload),encoding='utf-8')
    print(json.dumps({'cities':len(cities),'regions':len(cells),'planned':Counter(c['plan'] or 'Unassigned' for c in cities),'output':str(OUT)}))


if __name__=='__main__':main()
