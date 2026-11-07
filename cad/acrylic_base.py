#!/usr/bin/env python3
"""Prepare an isolated 16mm PMMA machining review using the accepted upper assembly.
No physical-strength certification and no changes to the source delivery.
"""
import argparse,csv,hashlib,json,shutil
from pathlib import Path
import numpy as np
from build123d import Compound,import_step,export_stl
from geometry import box,cyl,hex_prism,bounds
from part_names import export_named_step,repair_step_names


def make(source,out):
    source=Path(source).resolve();out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    for n in ('edit_table_up','print','machining','validation','reference'): (out/n).mkdir(exist_ok=True)
    m=json.loads((source/'manifest.json').read_text());original={r['name']:r for r in m['parts']}
    z0=.75;t=16.;top=z0+t;flange=8.;hole=6.5;pocket=18.;depth=9.5
    top_wash_h=1.;bottom_wash_h=2.;nut_h=4.7;bolt_l=25.
    positions=[(x,y) for x in (-35.,35.) for y in (-14.,-46.,-78.,-110.)]
    base=box(-120,120,-130,0,z0,top)
    for x,y in positions:
        base-=cyl(hole/2,t+.2,(x,y,z0+t/2))
        base-=cyl(pocket/2,depth+.1,(x,y,z0+(depth-.1)/2))
    assert base.is_valid and len(base.solids())==1
    rows=[];shapes={};checks=[]
    for r in m['parts']:
        n=r['name']
        if n=='base_printed' or n.startswith('hardware_base_M5_'):continue
        p=source/'edit_table_up'/f'{n}.step';dst=out/'edit_table_up'/p.name
        shutil.copyfile(p,dst);s=import_step(p).solids()[0];s.label=r['display_name'];shapes[n]=s;rows.append(dict(r))
        a=hashlib.sha256(p.read_bytes()).hexdigest();b=hashlib.sha256(dst.read_bytes()).hexdigest();assert a==b
        checks.append(dict(part=n,sha256=a,step_byte_identical=True))
        if r['is_printed']:
            for ext in ('.step','.stl'):shutil.copyfile(source/'print'/(n+ext),out/'print'/(n+ext))
    def add(n,title,s,material):
        s.label=title+' ['+n+']';shapes[n]=s
        rows.append(dict(name=n,display_name=s.label,is_printed=False,material=material,solid_volume_mm3=s.volume))
        export_named_step(s,out/'edit_table_up'/f'{n}.step')
    add('base_acrylic','底板（16mm浇铸亚克力）',base,'PMMA_cast')
    export_named_step(base,out/'machining/base_acrylic_16.step')
    export_stl(base,out/'machining/base_acrylic_16_preview.stl',tolerance=.04)
    # Position index matches the previous four M5 bolts, preserving stable IDs.
    bolt_rows=[];intersections=[]
    old_positions=[]
    for i in range(4):
        old=import_step(source/'edit_table_up'/f'hardware_base_M5_{i}.step').solids()[0]
        b=np.asarray(bounds(old));x,y=b[:,:2].mean(0);old_positions.append([float(x),float(y)])
        head_z=top+flange+2*top_wash_h;tip=head_z-bolt_l
        bolt=cyl(2.5,bolt_l,(x,y,(head_z+tip)/2))+cyl(4.25,5,(x,y,head_z+2.5))
        add(f'hardware_base_M5_{i}',f'立柱底座固定螺丝 M5×25 8.8级 {i+1}',bolt,'Steel_8_8')
        for j in range(2):
            z=top+flange+(j+.5)*top_wash_h
            w=cyl(5,top_wash_h,(x,y,z))-cyl(2.65,top_wash_h+.2,(x,y,z))
            add(f'hardware_base_top_washer_{i}_{j}',f'底座螺丝上平垫 M5 {i+1}-{j+1}',w,'Steel')
        wtop=z0+depth;wbottom=wtop-bottom_wash_h;nbottom=wbottom-nut_h
        w=cyl(7.5,bottom_wash_h,(x,y,(wtop+wbottom)/2))-cyl(2.65,bottom_wash_h+.2,(x,y,(wtop+wbottom)/2))
        add(f'hardware_base_bottom_washer_{i}',f'底座螺母厚平垫 M5 {i+1}',w,'Steel')
        nut=hex_prism(8.,nut_h,(x,y,(wbottom+nbottom)/2))-cyl(2.5,nut_h+.2,(x,y,(wbottom+nbottom)/2))
        add(f'hardware_base_nut_{i}',f'底座螺母 M5 8级 {i+1}',nut,'Steel_class8')
        bolt_rows.append(dict(index=i+1,xy_mm=[float(x),float(y)],bolt_tip_above_board_bottom_mm=tip-z0,
          nut_bottom_above_board_bottom_mm=nbottom-z0,bolt_projection_beyond_nut_mm=nbottom-tip,
          nominal_nut_thread_height_mm=nut_h,nut_full_height_traversed=tip<nbottom,
          all_hardware_above_board_bottom=tip>z0 and nbottom>z0))
        for name in (f'hardware_base_M5_{i}',f'hardware_base_bottom_washer_{i}',f'hardware_base_nut_{i}',f'hardware_base_top_washer_{i}_0',f'hardware_base_top_washer_{i}_1'):
            q=shapes[name]&base;v=q.volume if q else 0
            if v>1e-5:intersections.append(dict(parts=[name,'base_acrylic'],volume_mm3=v))
        for j in range(2):
            name=f'hardware_base_top_washer_{i}_{j}';q=shapes[name]&shapes['column_lower'];v=q.volume if q else 0
            if v>1e-5:intersections.append(dict(parts=[name,'column_lower'],volume_mm3=v))
    assert not intersections,intersections
    assert all(r['all_hardware_above_board_bottom'] and r['nut_full_height_traversed'] and r['bolt_projection_beyond_nut_mm']>=.8 for r in bolt_rows)
    # Bottom pocket section, hole centres and material removal read back from STEP.
    reloaded=import_step(out/'machining/base_acrylic_16.step').solids()[0]
    assert abs(reloaded.volume-base.volume)<1e-5
    expected=240*130*16-8*(np.pi*(hole/2)**2*t+np.pi*((pocket/2)**2-(hole/2)**2)*depth)
    assert abs(base.volume-expected)<1e-5
    all_checks=dict(executed=True,geometry_pass=True,physical_strength_pass=None,physical_test_executed=False,
      nonbase_unchanged=checks,unchanged_count=len(checks),expected_unchanged_count=35,
      overall_bounds_mm=bounds(base),volume_mm3=base.volume,independent_volume_mm3=expected,
      through_holes=8,through_hole_diameter_mm=hole,bottom_counterbores=8,counterbore_diameter_mm=pocket,
      counterbore_depth_mm=depth,remaining_acrylic_above_counterbore_mm=t-depth,
      minimum_counterbore_to_board_edge_mm=14-pocket/2,nominal_socket_OD_limit_mm=pocket,
      washer_radial_clearance_mm=(pocket-15)/2,bolt_stacks=bolt_rows,unexpected_intersections=intersections,
      upper_assembly_translation_mm=[0,0,0],original_16mm_base_top_preserved=True,
      limits=['Nominal CAD only; printed flange height, stock thickness, bolt lengths and washer/nut tolerances require dimensional confirmation.',
      'No female thread in acrylic. Steel external/internal thread teeth omitted from hardware representation.',
      'Pockets leave6.5mm acrylic above and5mm side ligament at nearest edge: no brittle fracture, torque, creep or clamp-load certification.',
      'Do not use unconstrained standard metal-bolt torque tables to tighten against acrylic or printed flange.'])
    (out/'validation/acrylic_geometry.json').write_text(json.dumps(all_checks,indent=2,ensure_ascii=False)+'\n')
    rows.sort(key=lambda r:r['name']);compound=Compound(label='夹具v3.2_16mm亚克力底板方案 [fixture_acrylic16]',children=list(shapes.values()))
    export_named_step(compound,out/'assembly.step')
    printed=[shapes[r['name']] for r in rows if r['is_printed']];purchased=[shapes[r['name']] for r in rows if not r['is_printed']]
    export_named_step(Compound(label='需要打印的部件（保留装配位置） [printed_parts]',children=printed),out/'assembly_printed_parts.step')
    export_named_step(Compound(label='需要购买加工的部件（保留装配位置） [purchased_parts]',children=purchased),out/'assembly_purchased_parts.step')
    controller=import_step(source/'reference/controller_table_up.step');controller.label='手柄参考面壳（勿打印） [controller_reference_SURFACE]'
    # Creating subsets reparents the original children. Reload the saved
    # complete assembly so the presentation STEP retains all named parts.
    fixture=import_step(out/'assembly.step');fixture.label='夹具（16mm亚克力底板） [fixture_acrylic16]'
    export_named_step(Compound(label='夹具及手柄参考 [assembly_acrylic16]',children=[fixture,controller]),out/'assembly_with_controller.step')
    bom=[['4','M5×25，ISO4762，8.8级','替代原M5×16'],['8','M5普通平垫，ISO7089，OD10 / ID5.3 / 厚1','每颗螺丝头下2片，已计入长度'],['4','M5厚平垫，DIN7349，OD15 / ID5.3 / 厚2','底面沉孔内，分散螺母压力'],['4','M5螺母，ISO4032:2023，8级，AF8 / 最大高4.7','底面沉孔内'],['1','浇铸PMMA底板240×130×16，8×Ø6.5通孔、底面8×Ø18平底沉孔深9.5','按加工图；取消原8个M5热熔螺母']]
    with (out/'底座五金变更.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['数量','规格','说明']);w.writerows(bom)
    for ext in ('.step','.stl'):shutil.copyfile(source/'coupons/guide_pin'/('guide_pin_coupon'+ext),out/'reference'/('guide_pin_coupon'+ext))
    result=dict(design_revision='v3.2-acrylic16-review',source_output=source.name,units='mm',parts=rows,
      board=dict(width=240,depth=130,thickness=16,bottom_z=z0,top_z=top,hole_d=hole,counterbore_d=pocket,counterbore_depth=depth,holes=positions),
      print_count=len(printed),purchased_count=len(purchased),solid_count=len(shapes),
      status='Nominal assembly and machining review; not physical strength certification',source_preserved=True)
    # Use manifest labels as the authority after nested STEP reimports. Some
    # imported OCCT names otherwise retain a second UTF8/Latin1 conversion.
    canonical=[r['display_name'] for r in rows]+[
        '夹具（16mm亚克力底板） [fixture_acrylic16]',
        '夹具及手柄参考 [assembly_acrylic16]',
        '需要打印的部件（保留装配位置） [printed_parts]',
        '需要购买加工的部件（保留装配位置） [purchased_parts]',
        '手柄参考面壳（勿打印） [controller_reference_SURFACE]']
    for name in ('assembly.step','assembly_printed_parts.step','assembly_purchased_parts.step','assembly_with_controller.step'):
        repair_step_names(out/name,canonical)
    (out/'manifest.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('parts',)},indent=2),flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();make(a.source,a.out)
