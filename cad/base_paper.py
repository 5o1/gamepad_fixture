"""English A3 machining views and nominal joint sections, without Blender."""
import csv
import json
from pathlib import Path
import ezdxf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, Rectangle


def make(out):
    out = Path(out); folder = out/'machining/paper'; folder.mkdir(parents=True, exist_ok=True)
    m = json.loads((out/'manifest.json').read_text()); insert = m['board']['insert']
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':9})
    holes = [(i+1, x+120, y+130, y) for i, (x, y) in enumerate(m['board']['holes'])]
    pages = []

    def sheet(title, name, scale='1:1', part='Aluminum plate, 240 x 130 x 10', datum='Machining datum: lower-left X0/Y0; underside Z0.'):
        fig = plt.figure(figsize=(420/25.4, 297/25.4)); a = fig.add_axes([0, 0, 1, 1])
        a.set(xlim=(0, 420), ylim=(0, 297), aspect='equal'); a.axis('off')
        a.add_patch(Rectangle((10, 10), 400, 277, fill=False, lw=.8))
        a.text(18, 275, title, fontsize=15)
        a.text(18, 265, 'Units: mm | Third-angle independent views | Dimensions govern | Print at 100%')
        a.add_patch(Rectangle((195, 10), 215, 29, fill=False, lw=.6))
        a.text(199, 30, f'GP-FIX-ALU10-B | v3.4-alu10 | {part}')
        a.text(199, 16, f'Scale {scale} | A3 | Sheet {len(pages)+1}/9 | Nominal geometry; no load certification', fontsize=8)
        a.text(18, 16, datum, fontsize=8)
        pages.append((fig, name))
        return a

    def line(a, x0, y0, x1, y1, hidden=False):
        a.plot([x0, x1], [y0, y1], color='black', lw=.6, ls='--' if hidden else '-')

    def dim(a, x0, y0, x1, y1, text):
        a.annotate('', xy=(x0, y0), xytext=(x1, y1), arrowprops=dict(arrowstyle='<->', lw=.6))
        a.text((x0+x1)/2+2, (y0+y1)/2+2, text, fontsize=9,
               rotation=90 if x0 == x1 else 0, ha='left' if x0 == x1 else 'center')

    def notes(a, lines, y=83):
        for i, text in enumerate(lines):
            a.text(18, y-i*6, text, fontsize=8.2)

    machining_notes = [
        '8 x drill diameter 5.2 THROUGH, then M5 x 0.8 STI (HELICOIL holding-thread tap) THROUGH.',
        'Install 8 tangless wire thread inserts (JP: helisert) M5 x 0.8, 1.5D = 7.5 long, from top; recess 0.4.',
        'Equivalents: Bollhoff HELICOIL Tangfree 5130 005 0075; Advanex TNM-M5-0.8X1.5D. Do NOT substitute 1.0D.',
        'CAD bore diameter 6.04 is the installed outer envelope, NOT the drill diameter. No helical threads modeled.',
        'Flat underside: no counterbores, nuts or bottom washers. Deburr; do not add flat-bottom pockets.',
        'Aluminum alloy, temper and finish are left to the buyer/supplier. All dimensions are finished dimensions.',
        'Targets: outline +/-0.2, thickness +/-0.1, hole positions +/-0.15; supplier to confirm capability.',
    ]
    for bottom in (False, True):
        a = sheet('Base plate - '+('bottom view (-Z toward +Z)' if bottom else 'top view (+Z toward -Z)'),
                  '02_bottom' if bottom else '01_top')
        ox, oy = 35, 110; a.add_patch(Rectangle((ox, oy), 240, 130, fill=False))
        for n, x, y, raw_y in holes:
            xx = 240-x if bottom else x
            a.add_patch(Circle((ox+xx, oy+y), 2.6, fill=False))
            line(a, ox+xx-5, oy+y, ox+xx+5, oy+y, True)
            line(a, ox+xx, oy+y-5, ox+xx, oy+y+5, True)
            a.text(ox+xx+5, oy+y+2, f'H{n:02d}', fontsize=7)
        dim(a, ox, oy+142, ox+240, oy+142, '240 +/-0.2')
        dim(a, ox+253, oy, ox+253, oy+130, '130 +/-0.2')
        a.text(307, 241, 'Hole     X       Y      Use', fontsize=9)
        for i, (n, x, y, raw_y) in enumerate(holes):
            a.text(307, 231-i*8, f'H{n:02d}   {x:3.0f}    {y:3.0f}    '+('active' if raw_y in (-14, -46) else 'spare'), fontsize=8)
        notes(a, machining_notes)
    for i, (title, width, positions) in enumerate([
        ('front (Y130 toward -Y)', 240, [85, 155]), ('rear (Y0 toward +Y)', 240, [85, 155]),
        ('left (X0 toward +X)', 130, [20, 52, 84, 116]), ('right (X240 toward -X)', 130, [20, 52, 84, 116])], 3):
        a = sheet('Base plate - '+title, f'{i:02d}_'+title.split()[0]); ox, oy = 55, 170
        a.add_patch(Rectangle((ox, oy), width, 10, fill=False))
        for x in positions:
            for dx in (-2.6, 2.6): line(a, ox+x+dx, oy, ox+x+dx, oy+10, True)
        dim(a, ox, oy-14, ox+width, oy-14, str(width))
        dim(a, ox+width+14, oy, ox+width+14, oy+10, '10 +/-0.1')
        notes(a, ['All holes are along Z; side views show hidden drill envelopes.',
                  'No side holes. Top face is Z10 in machining coordinates; underside is Z0.']+machining_notes, y=130)
    a = sheet('A-A - plate section at machining X85', '07_plate_section', '2:1'); ox, oy, s = 55, 170, 2
    a.add_patch(Rectangle((ox, oy), 130*s, 10*s, fc='#d3d8dc', ec='black', hatch='///'))
    for y in (20, 52, 84, 116):
        a.add_patch(Rectangle((ox+(y-3.02)*s, oy), 6.04*s, 10*s, fc='white', ec='black'))
        for sign in (-1, 1):
            a.add_patch(Rectangle((ox+(y+sign*2.5-(.52 if sign < 0 else 0))*s, oy+2.1*s), .52*s, 7.5*s, fc='#6b7c89', ec='black', lw=.4))
    dim(a, ox+275, oy, ox+275, oy+20, '10')
    notes(a, ['Section uses simplified diameter 6.04 receiving envelopes and ring inserts ID5 / OD6.04.',
              'Insert top: machining Z9.6; bottom Z2.1; length 7.5. Drill 5.2 then STI tap through.',
              'H01/H02/H05/H06 are active. H03/H04/H07/H08: rear-shift spare, inserts installed.',
              'Inserts: tangless M5 x 0.8 1.5D (7.5), e.g. Bollhoff 5130 005 0075 or Advanex TNM-M5-0.8X1.5D; not 1.0D.'], y=135)
    a = sheet('Nominal M5 joint - table-up assembly Z', '08_joint_section', '4:1', part='M5 base joint (reference)', datum='Assembly frame: Z0 = tabletop.'); ox, oy, s = 95, 95, 4
    for x0, w, z0, h, color in [(-11,22,.75,10,'#c9d0d5'),(-10,20,10.75,14,'#8dc6be')]:
        a.add_patch(Rectangle((ox+x0*s, oy+z0*s), w*s, h*s, fc=color, ec='black'))
    for x0,w,z0,h in [(-3.02,6.04,.75,10),(-2.75,5.5,10.75,8),(-5.2,10.4,18.75,6)]:
        a.add_patch(Rectangle((ox+x0*s,oy+z0*s),w*s,h*s,fc='white',ec='black',lw=.5))
    for x0,w,z0,h in [(-3.02,.52,2.85,7.5),(2.5,.52,2.85,7.5),(-5,10,18.75,1),(-5,10,19.75,1),(-5,10,20.75,1),(-2.5,5,1.75,20),(-4.25,8.5,21.75,5)]:
        a.add_patch(Rectangle((ox+x0*s,oy+z0*s),w*s,h*s,fc='#778a99',ec='black',lw=.5))
    for i, text in enumerate(['Bolt: M5x20 ISO 4762 class 8.8', 'Head Z21.75..26.75; bearing Z21.75',
        '3 x ISO 7089 M5 washers per bolt', 'Washer stack Z18.75..21.75; OD10 / ID5.3 / t1',
        'Flange bottom Z10.75; top Z24.75', 'Counterbore diameter 10.4, depth 6',
        'Insert Z2.85..10.35, tangless, length 7.5', 'Bolt tip Z1.75: 1.0 above underside',
        'Tip passes insert bottom by 1.10', 'Pad: 1 nominal, 0.75 compressed; not a CAD body']):
        a.text(165, 235-i*10, text, fontsize=10)
    notes(a, ['Nominal dimensions only; measure actual plate, flange, washers, bolts and recess before assembly.',
              'No qualified M5 tightening torque. Steel bolt screening does not certify PETG, insert or aluminum thread capacity.'], y=68)
    a = sheet('Column base - option B derived flange revision', '09_column_flange', '1:1', part='Column base [column_lower], printed PETG (reference)', datum='Assembly frame: table-up; print STL governs.')
    ox, oy = 65, 135; a.add_patch(Rectangle((ox, oy), 90, 50, fc='#dcf0eb', ec='black'))
    for x in (-35,35):
        for y in (-14,-46):
            for r in (2.75,5.2): a.add_patch(Circle((ox+x+45,oy+y+55),r,fill=False))
    dim(a,ox,oy-12,ox+90,oy-12,'90');dim(a,ox+104,oy,ox+104,oy+50,'50')
    a.text(205,210,'Table-up bounds: X -45..45, Y -55..-5',fontsize=10)
    for i,text in enumerate(['Flange Z10.75..24.75 (14 thick)', '4 x diameter 5.5 through',
        '4 x diameter 10.4 flat counterbore', 'Depth 6 from top Z24.75 to floor Z18.75',
        'Axes (X,Y): (+/-35,-14), (+/-35,-46)', 'Upper geometry above Z24.75 unchanged',
        'M6 teardrop height-lock holes unchanged']): a.text(205,198-i*11,text,fontsize=10)
    notes(a, ['Print frame: registered source translation (45,55,-16.75), then +6 Z bed re-zero; no rotation.',
              'Revised print bounds: X0..90, Y0..50, Z0..76. Teardrop apex remains +Z.',
              'Counterbores open upward; floor at print Z8. Confirm floor surface and tool clearance in slicing.'], y=100)
    with PdfPages(folder/'base_and_joint_A3.pdf') as pdf:
        for fig, name in pages:
            pdf.savefig(fig); fig.savefig(folder/(name+'.pdf')); fig.savefig(folder/(name+'.png'), dpi=120); plt.close(fig)
    with (folder/'hole_positions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['hole','X_mm','Y_mm','STI_drill_mm','tap','insert_length_mm','top_recess_mm','use'])
        for n,x,y,raw_y in holes: w.writerow([f'H{n:02d}',x,y,5.2,insert['thread'],7.5,.4,'active' if raw_y in (-14,-46) else 'rear-shift spare'])
    d=ezdxf.new('R2010');d.units=ezdxf.units.MM;ms=d.modelspace()
    for name,color in [('OUTLINE',7),('STI_DRILL_D5_2_THROUGH',3),('NOTES',5)]: d.layers.new(name,dxfattribs={'color':color})
    ms.add_lwpolyline([(0,0),(240,0),(240,130),(0,130)],close=True,dxfattribs={'layer':'OUTLINE'})
    for n,x,y,raw_y in holes: ms.add_circle((x,y),2.6,dxfattribs={'layer':'STI_DRILL_D5_2_THROUGH'})
    for i,text in enumerate(['ALUMINUM PLATE 240x130x10; ALLOY/TEMPER/FINISH LEFT TO BUYER/SUPPLIER',
        '8x DRILL 5.2 THROUGH; M5x0.8 STI TAP THROUGH; INSTALL TANGLESS 1.5D INSERT FROM TOP, RECESS 0.4; NOT 1.0D',
        'CAD BORE 6.04 IS INSTALLED ENVELOPE, NOT DRILL SIZE; FLAT UNDERSIDE; NO COUNTERBORES']):
        ms.add_text(text,dxfattribs={'height':2.5,'insert':(0,150-i*6),'layer':'NOTES'})
    d.saveas(out/'machining/base_aluminum_10.dxf')
    print('English A3 drawing ready: 9 sheets',flush=True)
