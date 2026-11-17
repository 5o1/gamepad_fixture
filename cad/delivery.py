"""English manufacturing, purchasing and rendering delivery for v3.4-alu10."""
import csv
import fnmatch
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path
from build123d import Location, import_step
from part_names import export_named_step, label

RELEASE = 'v3.4.0'
PACKAGE_NAME = 'gamepad_fixture_'+RELEASE
TEXT_SUFFIXES = {'.md','.txt','.csv','.json','.step','.stp','.dxf','.svg','.xml','.urdf','.py','.cmake'}
CJK = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]')


def decoded_step(text):
    for marker, encoding in (('2','utf-16-be'),('4','utf-32-be')):
        text = re.sub(r'\\X'+marker+r'\\([0-9A-Fa-f]+)\\X0\\',
                      lambda m:bytes.fromhex(m.group(1)).decode(encoding), text)
    return text


def scan_english(folder):
    checked=[];problems=[]
    for f in sorted(Path(folder).rglob('*')):
        rel=f.relative_to(folder).as_posix()
        if CJK.search(rel):problems.append(rel+': filename')
        if not f.is_file():continue
        if f.suffix.lower() in TEXT_SUFFIXES or f.name in ('LICENSE','SHA256SUMS','CMakeLists.txt'):
            text=f.read_text(encoding='utf-8-sig')
            if f.suffix.lower() in ('.step','.stp'):text=decoded_step(text)
            if CJK.search(text):problems.append(rel+': text')
            checked.append(rel)
        if f.suffix == '.pdf':
            import subprocess
            text=subprocess.check_output(['pdftotext',str(f),'-'],text=True)
            if CJK.search(text):problems.append(rel+': PDF text')
            checked.append(rel)
    if problems:raise RuntimeError('CJK remains in delivery: '+repr(problems))
    return dict(pass_=True,checked_files=len(checked),files=checked,problems=problems,
                STEP_unicode_escapes_decoded=True,PDF_text_extracted=True)


def archive(folder, destination, exclude_cad=False):
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(folder.rglob('*')):
            if f.is_file() and not (exclude_cad and f.relative_to(folder).parts[0]=='CAD'):
                z.write(f,f.relative_to(folder).as_posix())


def package(out):
    out=Path(out);m=json.loads((out/'manifest.json').read_text());repo=Path(__file__).resolve().parents[1]
    stage=out/PACKAGE_NAME
    if stage.exists():shutil.rmtree(stage)
    stage.mkdir()
    def cp(src,rel):
        dst=stage/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    def write(rel,text):
        dst=stage/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(text,encoding='utf-8')
    def table(rel,head,rows):
        dst=stage/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        with dst.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(head);w.writerows(rows)
    definitions=[
        ('B01','Aluminum base plate',1,'Custom GP-FIX-ALU10-B; 240x130x10; 8 M5x0.8 STI through; alloy, temper and finish left to buyer/supplier','Base; flat underside','base_aluminum'),
        ('B02','Column mounting bolts',4,'ISO 4762 M5x20 class 8.8, socket head, fully threaded','Front two mounting rows; no bottom nuts','hardware_base_M5_*'),
        ('B03','Column mounting washers',12,'ISO 7089 M5, steel, ID5.3 / OD10 / thickness1','Three per bolt inside flange counterbores','hardware_base_top_washer_*'),
        ('B04','Wire thread inserts',8,'Bollhoff HELICOIL Tangfree Free Running 5130 005 0075; M5x0.8; 1.5D=7.5; stainless steel; tangless','All eight holes; install from top, recess0.4; no tang removal required','hardware_base_insert_*'),
        ('B06','Steel guide rods',2,'ISO 2338 diameter6 h8 x100, unhardened; source example KILLICH 23381006100','Guide rods through cap, springs and slider','guide_rod_*'),
        ('B07','Compression springs',2,'OD11 / wire1.1 / free length40; target k=2 N/mm; solid length<=13; supplier SKU unselected','Installed length30; target20 N each; supplier to confirm force/displacement','hardware_compression_spring_*'),
        ('B08','Pivot bolt',1,'ISO 4017 M8x100 class8.8 fully threaded steel; AF13; head5.3','Through clevis lugs, Hirth discs and cradle','hardware_M8_axis_bolt'),
        ('B09','Large pivot washers',3,'ISO 7093 type M8; steel; ID8.4 / OD24 / thickness2','Bolt side, cradle hub and sleeve side','hardware_M8_washer_*;hardware_M8_hub_washer'),
        ('B10','Sliding steel sleeve',1,'Machined steel OD12 / ID8.4 / length22; flat deburred ends','Pivot right side; assembly X11..33; projects4','hardware_M8_sliding_sleeve'),
        ('B11','Through-thread star knob',1,'Ganter DIN 6336-KT-40-M8-D; PA body, steel insert; M8 THROUGH; OD40; height25','Pivot lock; do not substitute blind-thread knob','hardware_M8_star_knob_envelope'),
        ('B12','Height-lock bolt',1,'ISO 4017 M6x70 class8.8 fully threaded steel; AF10','Through gusset plates, sleeve and inner column; three height settings','hardware_M6_height_bolt'),
        ('B13','Height-lock nut',1,'DIN 985 M6x1 steel nylon locknut; AF10; nominal envelope height6','Height-lock bolt end; confirm purchased dimensions','hardware_M6_locknut'),
        ('B14','Height-lock washers',2,'ISO 7093 type M6; steel; ID6.4 / OD18 / thickness1.6','One per height-lock side','hardware_M6_washer_*'),
        ('B15','Fixed Hirth mounting bolts',3,'ISO 4762 M3x12 class8.8 steel socket head','Fixed disc to left clevis lug; 0/120/240 degrees','hardware_fixed_ring_M3_*'),
        ('B16','Moving Hirth mounting bolts',3,'ISO 4762 M3x20 class8.8 steel socket head','Moving disc to cradle; 60/180/300 degrees','hardware_moving_ring_M3_*'),
        ('B17','Hirth mounting nuts',6,'DIN 934 M3 historical ISO 4032 dimensions; AF5.5 / height2.4; steel','Three fixed and three moving disc hex pockets','hardware_fixed_ring_nut_*;hardware_moving_ring_nut_*'),
        ('B18','Controller pad stock',1,'Self-adhesive silicone sheet thickness2; suggested minimum100x100; cut three pads','Back support and jaws; use full-size A4 template','pad_*'),
        ('B19','Table clamps',2,'C clamps; opening>=50; suggested foot diameter>=20; supplier SKU unselected','Clamp plate to nominal25 thick tabletop, 10..20 from edge; not modeled',''),
        ('B20','Anti-slip base pad',1,'Compatible silicone/non-slip sheet 240x130x1 nominal; cut as needed','Compressed thickness0.75 nominal; not modeled; verify actual compression',''),
        ('O01','Optional guide-cap heat-set inserts',2,'M3; OD4.6 / length4; existing pilot4.1','Optional guide rod retention; not installed by default',''),
        ('O02','Optional flat-point set screws',2,'DIN 913 M3x6, flat-point socket','Use with O01 only; not installed by default',''),
    ]
    bom=[];covered=[]
    for ident,title,qty,spec,use,patterns in definitions:
        ids=[r['name'] for r in m['parts'] if not r['is_printed'] and any(fnmatch.fnmatchcase(r['name'],p) for p in patterns.split(';') if p)]
        covered.extend(ids);bom.append([ident,title,qty,'each' if ident!='B18' else 'sheet',spec,use,
                                       'optional; not installed' if ident.startswith('O') else 'required',';'.join(ids) or 'not modeled'])
    assert len(covered)==len(set(covered)) and set(covered)=={r['name'] for r in m['parts'] if not r['is_printed']}
    head=['item','name','quantity','unit','specification','use_and_position','status','CAD_part_IDs']
    table('02_purchased/BOM.csv',head,bom)
    write('02_purchased/BOM.md','# Purchasing list\n\nDimensions in mm. '+str(m['purchased_count'])+' modeled purchased bodies; sheet stock, clamps and optional items are separate.\n\n| '+' | '.join(head)+' |\n|'+'|'.join('---' for _ in head)+'|\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in bom)+'\n')
    prints=[]
    for r in m['parts']:
        n=r['name']
        if r['is_printed']:
            cp(out/'print'/(n+'.stl'),'01_printed/STL/'+n+'.stl')
            cp(out/'print'/(n+'.step'),'01_printed/CAD/'+n+'.step')
            prints.append([n,r['display_name'],1,'PETG',n+'.stl','Registered option B orientation; bed Z0' if n=='column_lower' else 'Accepted source orientation, unchanged'])
        else:
            cp(out/'edit_table_up'/(n+'.step'),'02_purchased/CAD/'+n+'.step')
    table('01_printed/print_list.csv',['part_ID','name','quantity','material','STL_file','orientation'],prints)
    board=import_step(out/'edit_table_up/base_aluminum.step').moved(Location((120,130,-.75)))
    board.label=label('base_aluminum')
    machining=stage/'02_purchased/base_plate/CAD/base_aluminum_10.step';machining.parent.mkdir(parents=True,exist_ok=True)
    export_named_step(board,machining)
    cp(out/'machining/base_aluminum_10.dxf','02_purchased/base_plate/CAD/base_aluminum_10.dxf')
    for f in (out/'machining/paper').iterdir():cp(f,'02_purchased/base_plate/drawings/'+f.name)
    cp(repo/'design/source/pad_templates_A4.svg','02_purchased/pads/pad_templates_A4.svg')
    for n in ('assembly.step','assembly_with_controller.step','assembly_printed_parts.step','assembly_purchased_parts.step'):cp(out/n,'03_assembly/'+n)
    cp(out/'reference/controller_table_up.step','03_assembly/controller_reference.step')
    cp(out/'reference/guide_pin_coupon.step','04_validation/guide_pin_coupon.step')
    cp(out/'reference/guide_pin_coupon.stl','04_validation/guide_pin_coupon.stl')
    for f in (out/'validation').glob('*.json'):cp(f,'04_validation/'+f.name)
    cp(out/'bolt_strength/results.json','04_validation/steel_bolt_screening.json')
    cp(out/'manifest.json','manifest.json')
    for source,target in [('color_reference','01_printed'),('simulation_reference','05_simulation_and_rendering/URDF'),('render_inputs','05_simulation_and_rendering/render_inputs')]:
        for f in (out/source).rglob('*'):
            if f.is_file():cp(f,target+'/'+f.relative_to(out/source).as_posix())
    for n in ('LICENSE','THIRD_PARTY_NOTICES.md'):
        for directory in ('','01_printed/','02_purchased/base_plate/'):
            cp(repo/n,directory+n)
    write('README.md','''# Gamepad fixture v3.4-alu10

1. Send `printing_STL_v3.4.0.zip` to the printing center: six PETG parts, one each. STL units are mm. See print colors and instructions.
2. Send `aluminum_manufacturing_v3.4.0.zip` to the plate supplier: 10 mm aluminum plate, eight M5 wire thread insert positions, STEP/DXF, nine A3 drawings and machining instructions. Alloy, temper and finish are left to the buyer/supplier.
3. Purchase items in `02_purchased/BOM.csv`. There are four M5x20 bolts, twelve top washers and eight tangless inserts. There are no base nuts or bottom washers.
4. `03_assembly` contains the English-labeled assembly and grouped STEP files in the table-up frame. The controller is a CC BY 4.0 surface reference, not a printable solid.
5. `05_simulation_and_rendering` contains the revised visual URDF and rendering inputs. The approved packed Blender scene must be supplied separately from the existing Release. No rendering was run for this revision.

Tabletop Z0; base underside Z0.75 and top Z10.75. A nominal 1 mm anti-slip pad is represented by a 0.75 mm compressed offset, without a CAD body. Option B extends the column flange downward by 6 mm; the accepted upper geometry and controller frame are unchanged. The owner-edited upper jaw slider geometry is retained. English source STEP files are copied directly into this package; there is one active set of part geometry.

All six critical geometry gates passed, including a failing 9 mm plate negative control. This is nominal CAD and steel bolt static screening, not physical strength, thread capacity, printability or machining certification. No approved M5 tightening torque is supplied. Historical records are not new validation.
''')
    write('01_printed/instructions.md','''# Printing instructions

Print six PETG parts, one each, at the provided STL scale (mm). Keep the five unchanged orientations. The revised column base has the geometrically registered source axes and a new bed origin: X0..90, Y0..50, Z0..76. Its M6 teardrop apex remains +Z. Counterbores open upward; floors are at print Z8. Confirm floor finish and tool access in the slicer. This is a geometric printability note, not a tested process.

Keep the cradle in its accepted side orientation. Keep Hirth teeth upward; the existing tooth-layer plan is 0.08-0.12 mm. The printing center selects actual slicing and removable supports for the sleeve closed top and clevis-lug holes, cradle cross holes/windows and overhangs, and below the slider R3 region. Remove supports without damaging guide holes, tooth faces or pad seats. Guide-pin coupon is separate from the six production parts.

Use print_colors.csv and print_colors.pdf; confirm actual PETG supplier swatches. Colors and per-part assignments are unchanged. Geometry files do not encode printing settings.
''')
    write('02_purchased/base_plate/machining_instructions.md','''# Aluminum plate machining and insert installation

Make one 240 x 130 x 10 mm aluminum plate. Alloy, temper and finish are left to the buyer/supplier. The machining STEP has bounds X0..240, Y0..130, Z0..10; the assembly STEP is translated by (-120,-130,+0.75). Use the hole table and drawings. DXF circles are the 5.2 mm STI drill size; CAD cylinders are simplified 6.04 mm installed envelopes and are NOT the drilling instruction.

At all eight positions, drill diameter5.2 through and cut an M5x0.8 STI HELICOIL holding thread through using the system-specific tap. An ordinary M5 tap is not suitable. Install eight Bollhoff HELICOIL Tangfree Free Running 5130 005 0075 inserts, nominal 7.5 mm (1.5D), from the top with 0.4 mm recess. This is 0.5 pitch within the catalog range 0.25-0.5 pitch. Tangless inserts need no tang removal. Gauge the STI and installed M5 threads with the supplier's appropriate tooling.

The 6.04 mm nominal envelope follows the catalog DHC minimum holding-thread outside diameter; free-state insert OD6.25..6.80 is not used. A ring envelope ID5.0 / OD6.04 represents each insert without threads. Confirm actual STI tolerances and installation process with the supplier. The underside is flat, without counterbores; no bottom washers or nuts. Deburr without adding flat-bottom pockets. Drawing tolerance targets require supplier confirmation.

H01/H02/H05/H06 (assembly Y-14/-46) are active. H03/H04/H07/H08 are rear-shift spare, with inserts installed; shifting the column would change the controller Y frame.

Manufacturer source: [Bollhoff HELICOIL Tangfree, catalog 0150/19-V1-GB, pages 16 and 18-19](https://media.boellhoff.com/files/pdf1/helicoil-tangfree-en-0150.pdf). The catalog is cited, not redistributed.
''')
    write('02_purchased/assembly_instructions.md','''# Base joint assembly and inspection

Use the revised column base only: flange bottom Z10.75, top Z24.75, four diameter10.4 counterbores depth6 ending at Z18.75. Place three ISO 7089 M5 washers (OD10, ID5.3, thickness1 each) in each counterbore. Fit four M5x20 ISO 4762 class8.8 bolts at the accepted front two rows, keeping the CAD index mapping.

Nominal washer stack is Z18.75..21.75; head bearing Z21.75 and head top Z26.75; tip Z1.75. Inserts span Z2.85..10.35, so each bolt passes the full insert length by 1.10 mm and remains 1.0 mm above the plate underside. Heads project 2 mm above the flange and remain clear of the gusset plates by nominal geometry. No bottom hardware is installed.

Measure stock thickness, printed flange, counterbore floors, washer stack, bolt length and insert recess; verify full engagement and no underside protrusion. Inspect flange seating before tightening. There is no experimentally qualified M5 torque or preload; do not transfer all-metal torque tables to the PETG flange. Steel bolt screening does not certify insert pullout, aluminum threads, PETG preload/creep, table clamps or overall joint capacity.

Fit the nominal 1 mm anti-slip pad and verify its actual compression; the CAD offset is 0.75 mm. Use two table clamps as specified in the BOM. Upper parts, M6 teardrop height holes, controller pose and table-from-pad transform retain the accepted arrangement. Do not substitute new hole shapes.

Tools: 4 mm hex key (M5), 2.5 mm hex key (M3), two 10 mm wrenches (M6), 13 mm wrench/torque adapter (M8), calipers, STI tap and gauges, and the Tangfree installation tool. The prior 1.2 N m M8 target is not an M5 base torque instruction.
''')
    for archive_name,folder,exclude in [('printing_STL_'+RELEASE+'.zip','01_printed',True),('aluminum_manufacturing_'+RELEASE+'.zip','02_purchased/base_plate',False),('simulation_URDF_'+RELEASE+'.zip','05_simulation_and_rendering/URDF',False),('render_inputs_'+RELEASE+'.zip','05_simulation_and_rendering/render_inputs',False)]:
        archive(stage/folder,out/archive_name,exclude)
        cp(out/archive_name,archive_name)
    english=scan_english(stage)
    (out/'validation/english_package.json').write_text(json.dumps(english,indent=2)+'\n')
    cp(out/'validation/english_package.json','04_validation/english_package.json')
    files=[f.relative_to(stage).as_posix() for f in sorted(stage.rglob('*')) if f.is_file()]
    table('file_index.csv',['file','purpose'],[[n,'Manufacturing, assembly or reference; see directory instructions'] for n in files+['file_index.csv','SHA256SUMS']])
    hashes=[hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.relative_to(stage).as_posix() for f in sorted(stage.rglob('*')) if f.is_file()]
    write('SHA256SUMS','\n'.join(hashes)+'\n')
    archive(stage,out/(PACKAGE_NAME+'.zip'))
    print('Package ready:',stage,flush=True)
    return stage
