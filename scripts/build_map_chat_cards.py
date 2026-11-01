"""Low-density map cards for image-compressing game chat uploads.

Render native region polygons, with numbered pins tied to a large-print list.
Coordinates belong in that list, rather than tiny labels across a whole state.
"""
from pathlib import Path
from xml.sax.saxutils import escape
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_state_map as source

OUT=source.OUT/'game-chat'
W,H=960,1200
BG='#0c1926'


def text(s,x,y,size=30,color='#f5f8fc',bold=False,anchor='start'):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}" text-anchor="{anchor}">{escape(s)}</text>'


def header(title,sub,page):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
            '<style>text{font-family:Segoe UI,Arial,sans-serif}</style>',
            '<defs><pattern id="contested" width="18" height="18" patternUnits="userSpaceOnUse" patternTransform="rotate(35)"><rect width="18" height="18" fill="#632231"/><rect width="7" height="18" fill="#ff8494"/></pattern></defs>',
            f'<rect width="{W}" height="{H}" fill="{BG}"/>',text(title,30,57,39,bold=True),
            text(sub,30,101,26,'#c8d8e5'),text(f'{page}/7',930,55,29,'#c8d8e5',anchor='end')]


def geometry(cities,cells,bounds,rect):
    x0,y0,x1,y1=bounds;rx,ry,rw,rh=rect
    scale=min(rw/(x1-x0),rh/(y1-y0));tx=rx+(rw-scale*(x1-x0))/2-scale*x0;ty=ry+(rh-scale*(y1-y0))/2-scale*y0
    result=[f'<svg x="{rx}" y="{ry}" width="{rw}" height="{rh}" viewBox="{rx} {ry} {rw} {rh}">',f'<g transform="translate({tx} {ty}) scale({scale})">']
    for c in cities:
        fill='url(#contested)' if c['contested'] else source.REGION_COLORS.get(c['plan'],'#65777d')
        edge='#ffe5eb' if c['contested'] else '#e8f0ed'
        # vector-effect preserves readable borders at the delivered image size.
        result.append(f'<path d="{source.path(cells[c["area_id"]])}" fill="{fill}" stroke="{edge}" stroke-width="2.6" vector-effect="non-scaling-stroke" stroke-linejoin="round"/>')
    result+=['</g>','</svg>']
    def point(c):
        x,y=source.project(c['x'],c['y']);return tx+scale*x,ty+scale*y
    return result,point


def overview(cities,cells,ru):
    tr=lambda a,b:b if ru else a
    s=header(tr('STATE 1005 · CLAIMS','ШТАТ 1005 · ЗАЯВКИ'),tr('Overview · use cards 2–7 for coordinates','Обзор · координаты на карточках 2–7'),1)
    g,point=geometry(cities,cells,(80,250,3120,2280),(18,135,924,715));s+=g
    anchors={'VeD':(828,588),'VAN':(508,588),'ALL':(848,328),'rus':(868,988),'ECL':(328,748),'TCE':(308,468)}
    for tag,xy in anchors.items():
        c=next(c for c in cities if (c['x'],c['y'])==xy);x,y=point(c)
        width=78 if len(tag)==3 else 65
        s.append(f'<rect x="{x-width/2}" y="{y-20}" width="{width}" height="33" rx="5" fill="{BG}"/>')
        s.append(text(tag,x,y+5,27,source.FLAG_COLORS[tag],True,'middle'))
    for i,(tag,color) in enumerate(source.REGION_COLORS.items()):
        xx=30+(i%3)*310;yy=905+(i//3)*62
        s.append(f'<rect x="{xx}" y="{yy-28}" width="30" height="30" rx="4" fill="{color}" stroke="#fff"/>')
        s.append(text(f'{tag} · {len(source.CLAIMS[tag])}',xx+44,yy,31,bold=True))
    s += [text(tr('ECL CAPTURED 668:828','ECL ЗАХВАТИЛ 668:828'),30,1050,32,'#ffa4b2',True),
          text(tr('No contested regions','Спорных регионов нет'),30,1095,32,bold=True),
          text(tr('Claims, not confirmed ownership · 29 Oct 2026','Заявки, не текущее владение · 29.10.2026'),30,1165,24,'#c8d8e5'),'</svg>']
    return ''.join(s)


def detail(cities,cells,tags,page,ru):
    tr=lambda a,b:b if ru else a
    chosen=[c for c in cities if any(t in c['claims'] for t in tags)]
    chosen.sort(key=lambda c:c['order'] if tags==['VeD'] else (-c['level'],c['y'],c['x']))
    vertices=[source.project(xx*10,yy*10) for c in chosen for ring in source.boundary(cells[c['area_id']]) for xx,yy in ring]
    xs,ys=zip(*vertices);bounds=(min(xs)-55,min(ys)-55,max(xs)+55,max(ys)+55)
    title=' + '.join(tags)
    s=header(f'{title} · '+tr('CITY MAP','КАРТА ГОРОДОВ'),tr('Match map pins to the coordinate list below','Номера на карте соответствуют списку ниже'),page)
    # Only the selected regions are coloured; other claims provide neutral context.
    nearby=[]
    for c in cities:
        v=dict(c)
        if c not in chosen:v.update(plan='',contested=False)
        nearby.append(v)
    g,point=geometry(nearby,cells,bounds,(20,135,920,560));s+=g
    for i,c in enumerate(chosen,1):
        x,y=point(c);fill='#ffdce3' if c['contested'] else '#fff'
        s += [f'<circle cx="{x}" cy="{y}" r="25" fill="{fill}" stroke="#122333" stroke-width="4"/>',text(str(i),x,y+13,37,'#122333',True,'middle')]
    for i,c in enumerate(chosen,1):
        yy=752+(i-1)*60
        fill='#ffdce3' if c['contested'] else '#fff'
        s += [f'<circle cx="47" cy="{yy-11}" r="21" fill="{fill}"/>',text(str(i),47,yy,31,'#122333',True,'middle')]
        suffix=f" · {c['plan']}" if len(tags)>1 else ''
        name=c['ru'] if ru else c['name']
        s.append(text(f"{c['x']}:{c['y']} · L{c['level']} {name}{suffix}",83,yy,29 if len(tags)>1 else 31,bold=True))
    s.append(text(tr('ECL holds 668:828 · no contested regions','ECL владеет 668:828 · спорных регионов нет'),30,1130,27,'#ffa4b2',True))
    s.append(text(tr('Pins identify targets, not capture order.','Номера обозначают цели, не порядок захвата.'),30,1174,25,'#c8d8e5'))
    s.append('</svg>');return ''.join(s)


def main():
    cities,cells,_,_=source.load()
    for lang in ['EN','RU']:
        folder=OUT/lang;folder.mkdir(parents=True,exist_ok=True)
        cards=[('01-Overview',overview(cities,cells,lang=='RU'))]
        for page,tags in enumerate([['VeD'],['VAN'],['ALL'],['rus'],['ECL'],['TCE']],2):
            cards.append((f'{page:02d}-'+ '-'.join(tags),detail(cities,cells,tags,page,lang=='RU')))
        for name,svg in cards:(folder/(name+'.svg')).write_text(svg,encoding='utf-8')
    print(json.dumps({'cards_per_language':7,'dimensions':[W,H],'output':str(OUT)}))

if __name__=='__main__':main()
