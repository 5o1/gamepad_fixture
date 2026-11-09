"""Produce a printer-facing color order and swatch sheet from config/colors.json."""
import csv,json
from pathlib import Path
from palette import load_palette,part_color,rgb

def make(out,palette_path=None):
    out=Path(out);manifest=json.loads((out/'manifest.json').read_text());palette=load_palette() if palette_path is None else load_palette(palette_path)
    folder=out/'color_reference';folder.mkdir(exist_ok=True)
    rows=[]
    order=list(palette['printed_parts'])
    for row in sorted(manifest['parts'],key=lambda r:order.index(r['name']) if r['is_printed'] else len(order)):
        if not row['is_printed']:continue
        c=part_color(palette,row['name'],True)
        rows.append([row['name'],c['name'],row['name']+'.stl',1,'PETG',c['color_name'],c['hex'],','.join(map(str,rgb(c['hex']))),'Confirm against supplier PETG swatch'])
    head=['part_id','part_name','STL_file','quantity','material','color_name','sRGB_HEX','sRGB_RGB','supplier_color_code']
    with (folder/'print_colors.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(head);w.writerows(rows)
    (folder/'print_colors.md').write_text('# Printing color reference\n\n'+palette['manufacturing_note']+'\n\n| '+' | '.join(head)+' |\n|'+'|'.join('---' for _ in head)+'|\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)+'\n')
    (folder/'colors.json').write_text(json.dumps(palette,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig=plt.figure(figsize=(8.27,11.69));a=fig.add_axes([0,0,1,1]);a.set(xlim=(0,210),ylim=(0,297));a.axis('off')
    a.text(16,280,'Printing color reference',fontsize=20,color='#173b48');a.text(16,270,f'Gamepad fixture | {len(rows)} parts | PETG | 1 of each',fontsize=10)
    for i,r in enumerate(rows):
        y=244-i*32;a.add_patch(Rectangle((16,y-10),23,20,facecolor=r[6],edgecolor='#999',lw=.4))
        a.text(45,y+5,r[1],fontsize=12,fontweight='bold');a.text(45,y-2,r[2],fontsize=8);a.text(45,y-9,f'{r[5]}   {r[6]}   RGB {r[7]}',fontsize=9)
    a.text(16,34,'Match actual PETG to the supplier swatch before production.',fontsize=9)
    a.text(16,27,'HEX/RGB are sRGB display references; they are not filament SKUs.',fontsize=9)
    a.text(16,20,'The URDF and both assembly renders use the same color configuration.',fontsize=8.5)
    fig.savefig(folder/'print_colors.pdf');fig.savefig(folder/'print_colors.png',dpi=180);plt.close(fig)
    print('Printing color reference:',folder,flush=True)
    return rows
