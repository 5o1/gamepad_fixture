"""Independently read the exported STEP, documents and archives for alu10."""
import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
import numpy as np
import ezdxf
from build123d import import_step
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cad'))
from base_review import review, cylinders, solid
from geometry import bounds
from delivery import PACKAGE_NAME, scan_english
from reference_validation import check


def named(shape):
    result={};pending=[shape]
    while pending:
        node=pending.pop();pending.extend(node.children)
        match=re.search(r'\[([A-Za-z0-9_+\-]+)\]',node.label)
        if match and len(node.solids())==1:result[match.group(1)]=node.solids()[0]
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'build/alu10');a=parser.parse_args()
    out=a.out;stage=out/PACKAGE_NAME;m=json.loads((out/'manifest.json').read_text())
    gates=review(out,ROOT/'design/source')
    assembly=import_step(stage/'03_assembly/assembly_with_controller.step');actual=named(assembly)
    assert len(assembly.solids())==m['solid_count']==60
    pose=[]
    for row in m['parts']:
        n=row['name'];s=solid(out/'edit_table_up'/f'{n}.step');t=actual[n]
        error=float(np.max(abs(np.array(bounds(s))-np.array(bounds(t)))));dv=abs(s.volume-t.volume)
        assert error<=1e-6 and dv<=1e-5,(n,error,dv)
        pose.append(dict(part=n,bounds_error_mm=error,volume_error_mm3=dv))
    labels=[];pending=[assembly]
    while pending:
        s=pending.pop();labels.append(s.label);pending.extend(s.children)
    def norm(text):return re.sub(r'[^A-Za-z0-9+\-]','',text)
    assert all(norm(row['display_name']) in {norm(l) for l in labels} for row in m['parts'])
    assert any('[fixture_alu10]' in l for l in labels) and any('[assembly_alu10]' in l for l in labels)
    reference=import_step(ROOT/'design/source/reference/controller_table_up.step')
    controller=next(s for s in assembly.children if 'controller_reference_SURFACE' in s.label)
    assert np.max(abs(np.array(bounds(reference))-np.array(bounds(controller))))<=1e-6
    assert abs(reference.area-controller.area)<=1e-5
    board=solid(stage/'02_purchased/base_plate/CAD/base_aluminum_10.step')
    assert np.max(abs(np.array(bounds(board))-np.array([[0,0,0],[240,130,10]])))<=1e-6
    holes=cylinders(board)
    assert len(holes)==8 and all(abs(r['radius_mm']-3.02)<=1e-6 for r in holes)
    assert all(np.max(abs(np.array(r['bounds_mm'])[:,2]-[0,10]))<=1e-6 for r in holes)
    expected_xy=sorted((x+120,y+130) for x,y in m['board']['holes'])
    assert sorted((round(r['axis_origin_mm'][0],6),round(r['axis_origin_mm'][1],6)) for r in holes)==expected_xy
    d=ezdxf.readfile(stage/'02_purchased/base_plate/CAD/base_aluminum_10.dxf')
    circles=list(d.modelspace().query('CIRCLE'))
    assert d.units==ezdxf.units.MM and len(circles)==8
    assert all(c.dxf.layer=='STI_DRILL_D5_2_THROUGH' and abs(c.dxf.radius-2.6)<=1e-8 for c in circles)
    assert sorted((round(c.dxf.center.x,6),round(c.dxf.center.y,6)) for c in circles)==expected_xy
    for kind,count in [('printed',6),('purchased',54)]:
        sub=import_step(stage/'03_assembly'/f'assembly_{kind}_parts.step')
        assert len(sub.solids())==count
        assert set(named(sub))=={r['name'] for r in m['parts'] if r['is_printed']==(kind=='printed')}
    assert len(list((stage/'01_printed/STL').glob('*.stl')))==6
    for row in m['parts']:
        if row['is_printed']:
            n=row['name']
            assert (stage/'01_printed/STL'/f'{n}.stl').read_bytes()==(out/'print'/f'{n}.stl').read_bytes()
            p=solid(stage/'01_printed/CAD'/f'{n}.step');s=solid(out/'print'/f'{n}.step')
            assert abs(p.volume-s.volume)<=1e-6 and np.max(abs(np.array(bounds(p))-np.array(bounds(s))))<=1e-6
    bom=list(csv.DictReader((stage/'02_purchased/BOM.csv').open(encoding='utf-8-sig')))
    covered=[]
    for r in bom:
        assert all(r.values())
        covered.extend(n for n in r['CAD_part_IDs'].split(';') if n!='not modeled')
    assert len(covered)==len(set(covered))==54
    assert set(covered)=={r['name'] for r in m['parts'] if not r['is_printed']}
    assert not any(n.startswith(('hardware_base_nut_','hardware_base_bottom_washer_')) or n=='base_acrylic' for n in actual)
    files={f.relative_to(stage).as_posix() for f in stage.rglob('*') if f.is_file()}
    index=list(csv.DictReader((stage/'file_index.csv').open(encoding='utf-8-sig')))
    assert {r['file'] for r in index}==files
    hashes={n:h for h,n in (l.split('  ',1) for l in (stage/'SHA256SUMS').read_text().splitlines())}
    assert set(hashes)==files-{'SHA256SUMS'}
    assert all(hashlib.sha256((stage/n).read_bytes()).hexdigest()==h for n,h in hashes.items())
    pdf=stage/'02_purchased/base_plate/drawings/base_and_joint_A3.pdf'
    info=subprocess.check_output(['pdfinfo',str(pdf)],text=True)
    assert re.search(r'Pages:\s+9\b',info) and ('A3' in info or re.search(r'Page size:\s+1190',info))
    for f in out.glob('*v3.4.0.zip'):
        with zipfile.ZipFile(f) as z:
            assert z.testzip() is None
            if f.name.startswith('printing_'):assert sum(n.endswith('.stl') for n in z.namelist())==6
    # Part STEP files are copied directly from the single English source set.
    for row in m['parts']:
        n=row['name']
        if row['is_printed']:
            assert (stage/'01_printed/CAD'/f'{n}.step').read_bytes()==(ROOT/'design/source/print'/f'{n}.step').read_bytes()
        else:
            assert (stage/'02_purchased/CAD'/f'{n}.step').read_bytes()==(ROOT/'design/source/edit_table_up'/f'{n}.step').read_bytes()
    english=scan_english(stage)
    check(out)
    # Verify revision render arrays against actual CAD-derived visual meshes and fixed origins.
    payload=json.loads((out/'render_inputs/payload.json').read_text());arrays=np.load(out/'render_inputs/meshes.npz')
    assert payload['table_from_pad_mm']==m['table_from_pad_mm']
    assert {r['name'] for r in payload['parts']}=={r['name'] for r in m['parts']}
    for row in m['parts']:
        n=row['name'];v=arrays[n+'_v']*1000
        assert np.max(abs(np.array([v.min(0),v.max(0)])-np.array(bounds(actual[n]))))<=.05
    result=dict(pass_=True,critical_gates={f'C{i}':gates[f'C{i}']['pass_'] for i in range(1,7)},
        solid_count=60,printed_count=6,purchased_count=54,bom_rows=len(bom),package_files=len(files),
        all_purchase_bodies_mapped_once=True,all_assembly_labels_English=True,controller_reference_unchanged=True,
        upper_poses_match=True,pose_measurements=pose,machining_bounds_mm=bounds(board),
        paper_sheets=9,english_check=english,render_inputs_checked_without_Blender=True,
        physical_strength_certified=False,physical_test_executed=False)
    (out/'final_review.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('pose_measurements','english_check')},indent=2))


if __name__=='__main__':main()
