"""Apply reviewer Ruling 1; reproducibly update English source CAD from Git v3.2."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import numpy as np
from build123d import import_step
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'cad'))
from base_plate import INSERT, make_plate
from column_lower_b import derive, require
from geometry import bounds, cyl
from part_names import label, export_named_step
from source_identity import git_bytes, english_labels, read_bytes, prove_name_only, prove_geometry, geometry, registration


def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline-ref',default='HEAD');a=p.parse_args()
    ref=subprocess.check_output(['git','rev-parse',a.baseline_ref],cwd=ROOT,text=True).strip()
    source=ROOT/'design/source'
    previous=json.loads(git_bytes(ROOT,ref,'design/PROVENANCE.json'))
    old=json.loads(git_bytes(ROOT,ref,'design/source/manifest.json'))
    baseline_steps=subprocess.check_output(['git','ls-tree','-r','--name-only',ref,'design/source'],cwd=ROOT,text=True).splitlines()
    baseline_steps=[n for n in baseline_steps if n.endswith('.step')]
    proofs=[]
    for rel in baseline_steps:
        before=git_bytes(ROOT,ref,rel);after=english_labels(before)
        changes=prove_name_only(before,after)
        g=prove_geometry(read_bytes(before),read_bytes(after),rel)
        (ROOT/rel).write_bytes(after)
        proofs.append(dict(file=rel,baseline_sha256=hashlib.sha256(before).hexdigest(),
            labeled_sha256=hashlib.sha256(after).hexdigest(),name_tokens_changed=len(changes),changed_name_entities=sorted({r['entity'] for r in changes}),
            all_non_name_bytes_identical=True,**g))
    # Derive once into the authoritative source. The regular build only copies it.
    with tempfile.TemporaryDirectory() as folder:
        baseline=Path(folder)
        for n in ('edit_table_up','print'):
            (baseline/n).mkdir();(baseline/n/'column_lower.step').write_bytes(git_bytes(ROOT,ref,f'design/source/{n}/column_lower.step'))
        _,derivation=derive(baseline,source)
    rows=[]
    original={r['name']:r for r in old['parts']}
    for row in old['parts']:
        n=row['name']
        if n=='base_printed' or n.startswith('hardware_base_M5_'):continue
        r=dict(row);s=import_step(source/'edit_table_up'/f'{n}.step').solids()[0]
        r.update(display_name=label(n),solid_volume_mm3=s.volume,bounds_mm=bounds(s),valid_solid=s.is_valid,solid_count=1)
        if n=='column_lower':r['derived']=derivation;r['note']='Option B: flange extended downward 6 mm, four top counterbores; source updated by explicit owner authorization'
        rows.append(r)
    def add(n,s,material):
        s.label=label(n);export_named_step(s,source/'edit_table_up'/f'{n}.step')
        rows.append(dict(name=n,display_name=label(n),is_printed=False,material=material,solid_volume_mm3=s.volume,
                         bounds_mm=bounds(s),valid_solid=s.is_valid,solid_count=1))
    add('base_aluminum',make_plate(),'aluminum plate; alloy, temper and finish left to buyer/supplier')
    positions=[(x,y) for x in (-35.,35.) for y in (-14.,-46.,-78.,-110.)]
    for i,(x,y) in enumerate(positions):
        ring=cyl(3.02,7.5,(x,y,6.6))-cyl(2.5,7.7,(x,y,6.6))
        add(f'hardware_base_insert_{i}',ring,'stainless steel wire thread insert')
    for i in range(4):
        before=read_bytes(git_bytes(ROOT,ref,f'design/source/edit_table_up/hardware_base_M5_{i}.step')).solids()[0]
        x,y=np.array(bounds(before))[:,:2].mean(0)
        add(f'hardware_base_M5_{i}',cyl(2.5,20,(x,y,11.75))+cyl(4.25,5,(x,y,24.25)),'steel class 8.8')
        for j in range(3):add(f'hardware_base_top_washer_{i}_{j}',cyl(5,1,(x,y,19.25+j))-cyl(2.65,1.2,(x,y,19.25+j)),'steel')
    registrations={}
    for row in rows:
        if not row['is_printed']:continue
        n=row['name'];table=import_step(source/'edit_table_up'/f'{n}.step').solids()[0]
        printing=import_step(source/'print'/f'{n}.step').solids()[0]
        old_matrix=original[n]['print_transform']
        record=registration(table,printing,[np.eye(3)],n)
        record.update(previous_manifest_transform=old_matrix,manifest_was_stale=not np.allclose(old_matrix,record['matrix'],atol=1e-8,rtol=0))
        registrations[n]=record
        row['print_transform']=record['matrix']
        row['print_rotation_deg']=list(printing.location.orientation) if n=='column_lower' else list(__import__('source_identity').location(record['matrix']).orientation)
        # Store the complete transform as authority; Euler angles are descriptive only.
        row['print_bounds_mm']=(np.array(bounds(printing))[1]-np.array(bounds(printing))[0]).tolist()
        row['print_aabb_mm']=bounds(printing)
    parameters=json.loads(json.dumps(old['parameters']))
    historical={}
    def retire(section,keys):
        for key in keys:historical[section+'.'+key]=parameters[section].pop(key)
    retire('installation',['printed_base_thickness','aluminum_base','aluminum_thickness','flange_thickness'])
    retire('hardware',['base_insert_pilot','base_insert_od','base_insert_length','base_insert_pilot_depth','aluminum_tap_drill_d','aluminum_tap_depth','aluminum_base_bolt_length'])
    # Preserve old parameter-key spellings as history while active terminology is English.
    for old_key,new_key in [('ear_inner_x','clevis_lug_inner_x'),('ear_outer_x','clevis_lug_outer_x'),('ear_radius','clevis_lug_radius')]:
        historical['installation.'+old_key]=parameters['installation'].pop(old_key)
        parameters['installation'][new_key]=historical['installation.'+old_key]
    parameters['installation'].update(layout_revision='v3.4-alu10',base_thickness_mm=10,base_material='aluminum plate',
        flange_thickness=14,flange_bottom_z_mm=10.75,flange_top_z_mm=24.75,
        aluminum_alloy_temper_finish='left to buyer/supplier')
    parameters['hardware'].update(base_bolt_length=20,base_bolt_standard='ISO 4762 class 8.8',base_top_washers_per_bolt=3,base_wire_insert=INSERT)
    parameters['historical_v3_2']=dict(status='Historical source assumptions; not active manufacturing instructions',values=historical,
        retired_base_part=original['base_printed'],retired_base_id='base_acrylic')
    parameters['historical_v3_2']['retired_base_part']['display_name']=label('base_printed')
    manifest=dict(design_revision='v3.4-alu10',parts=sorted(rows,key=lambda r:r['name']),parameters=parameters,
        v3_2_table_from_pad=old['v3_2_table_from_pad'],board=dict(width=240,depth=130,thickness=10,bottom_z=.75,top_z=10.75,
            hole_d=6.04,holes=positions,bottom_counterbores=0,insert=INSERT),
        revision_note='Reviewer Ruling 1: owner authorizes STEP changes; English source is authoritative; column option B is derived once by script, not in the build')
    (source/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    modified_geometry={'design/source/edit_table_up/column_lower.step','design/source/print/column_lower.step',
        *[f'design/source/edit_table_up/hardware_base_M5_{i}.step' for i in range(4)]}
    final_proofs=[]
    for proof in proofs:
        rel=proof['file']
        if rel in modified_geometry:continue
        before=git_bytes(ROOT,ref,rel);after=(ROOT/rel).read_bytes()
        prove_name_only(before,after)
        final_proofs.append(dict(proof,current_sha256=hashlib.sha256(after).hexdigest()))
    stls=[]
    for rel in subprocess.check_output(['git','ls-tree','-r','--name-only',ref,'design/source'],cwd=ROOT,text=True).splitlines():
        if not rel.endswith('.stl'):continue
        before=git_bytes(ROOT,ref,rel);after=(ROOT/rel).read_bytes()
        if rel.endswith('/column_lower.stl'):
            stls.append(dict(file=rel,byte_identical=before==after,reason='Authorized option B geometry revision'));continue
        require(before==after,'C2: unexpected STL edit: '+rel)
        has_cjk=bool(re.search(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]',before[:80].decode('utf-8',errors='ignore')))
        stls.append(dict(file=rel,byte_identical=True,baseline_header_contains_CJK=has_cjk,header_changed_for_CJK=False,sha256=hashlib.sha256(after).hexdigest()))
    record=dict(baseline_git_commit=ref,ruling_1='Owner explicitly permits modifying accepted STEP assets; source relabeled in place; no dual active copy design',
        initial_all_47_name_only_proofs=proofs,final_name_only_geometry_proofs=final_proofs,
        authorized_geometry_changes=sorted(modified_geometry),STL_checks=stls,all_six_print_registrations=registrations,
        historical_parameter_keys=historical,derivation=derivation,
        implementation_fix_log=[
            'Registration probe fix 1: Matrix.transform_shape rejected gp_GTrsf as non-orthogonal. Switched to a rigid Location.',
            'Registration probe fix 2: default Location Euler ordering differs from SciPy xyz. Used gp_Trsf.SetValues directly to preserve the tested matrix.',
            'Registration probe fix 3: displaying an empty Boolean common raised AttributeError on None.volume. Used the existing empty-shape volume helper.',
        ],
        slider_boolean_diagnostic='Coincident registered slider solids have identical 41 face metrics and 560 edge samples, but OCCT common can return zero. C3 uses independent feature registration, bounds and volume; no slider geometry was changed.')
    (source/'revision_validation.json').write_text(json.dumps(record,indent=2)+'\n')
    provenance=dict(project='gamepad_fixture',version='v3.4-alu10',owner='5o1',controller_license=previous['controller_license'],
        revision_note=manifest['revision_note'],baseline_git_commit=ref,previous=previous,
        sha256={f.relative_to(source).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(source.rglob('*')) if f.is_file()})
    (ROOT/'design/PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print('Source revision ready:',len(rows),'bodies;',len(final_proofs),'final name-only geometry proofs; six prints registered',flush=True)


if __name__=='__main__':main()
