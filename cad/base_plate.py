"""Build the aluminum base and option B support without modifying source CAD."""
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np
from build123d import Compound, import_step, export_stl
from geometry import box, cyl, bounds
from part_names import label, export_named_step, repair_step_names
from column_lower_b import require

INSERT = dict(manufacturer='Bollhoff', product='HELICOIL Tangfree Free Running',
    part_number='5130 005 0075', thread='M5x0.8 STI (HELICOIL holding thread)',
    length_mm=7.5, recess_mm=.4, installed_envelope_od_mm=6.04, id_mm=5.0,
    sti_drill_mm=5.2, source='https://media.boellhoff.com/files/pdf1/helicoil-tangfree-en-0150.pdf',
    source_pages='16, 18-19', envelope_basis='DHC minimum holding-thread outside diameter, used as nominal installed outer envelope; not free-state diameter 6.25..6.80',
    recess_basis='0.5 pitch selected from manufacturer 0.25..0.5 pitch range')


def make_plate(thickness=10):
    plate = box(-120, 120, -130, 0, .75, .75+thickness)
    for x in (-35., 35.):
        for y in (-14., -46., -78., -110.):
            plate -= cyl(3.02, thickness+.2, (x, y, .75+thickness/2))
    return plate


def make(source, out):
    source, out = Path(source).resolve(), Path(out).resolve()
    for n in ('edit_table_up', 'print', 'machining', 'validation', 'reference'):
        (out/n).mkdir(parents=True, exist_ok=True)
    m=json.loads((source/'manifest.json').read_text())
    revision=json.loads((source/'revision_validation.json').read_text())
    rows,shapes=[],{}
    for r in m['parts']:
        n=r['name'];src=source/'edit_table_up'/f'{n}.step';dst=out/'edit_table_up'/f'{n}.step'
        shutil.copyfile(src,dst)
        s=import_step(dst).solids()[0];s.label=r['display_name'];shapes[n]=s;rows.append(dict(r))
        if r['is_printed']:
            for ext in ('.step','.stl'):shutil.copyfile(source/'print'/(n+ext),out/'print'/(n+ext))
    shutil.copyfile(source/'edit_table_up/base_aluminum.step',out/'machining/base_aluminum_10.step')
    export_stl(shapes['base_aluminum'],out/'machining/base_aluminum_10_preview.stl',tolerance=.04)
    export_named_step(Compound(label='Fixture [fixture_alu10]',children=list(shapes.values())),out/'assembly.step')
    for kind,printed in (('printed',True),('purchased',False)):
        export_named_step(Compound(label=f'{kind.capitalize()} parts [{kind}_parts]',
            children=[shapes[r['name']] for r in rows if r['is_printed']==printed]),out/f'assembly_{kind}_parts.step')
    fixture=import_step(out/'assembly.step');fixture.label='Fixture [fixture_alu10]'
    controller=import_step(source/'reference/controller_table_up.step')
    controller.label=label('controller_reference_SURFACE')
    export_named_step(Compound(label='Fixture and controller [assembly_alu10]',children=[fixture,controller]),out/'assembly_with_controller.step')
    # Reimported children carry OCCT-mangled labels; restore the canonical ones.
    repair_step_names(out/'assembly_with_controller.step',[r['display_name'] for r in rows]+['Fixture [fixture_alu10]',controller.label,'Fixture and controller [assembly_alu10]'])
    for ext in ('.step','.stl'):
        shutil.copyfile(source/'coupons/guide_pin'/('guide_pin_coupon'+ext),out/'reference'/('guide_pin_coupon'+ext))
        shutil.copyfile(source/'reference'/('controller_table_up'+ext),out/'reference'/('controller_table_up'+ext))
    checks=[dict(part=Path(r['file']).stem,**r) for r in revision['final_name_only_geometry_proofs'] if '/edit_table_up/' in r['file']]
    result=dict(design_revision='v3.4-alu10',units='mm',parts=rows,board=m['board'],
        table_from_pad_mm=m['v3_2_table_from_pad'],upper_assembly_translation_mm=[0,0,0],
        pad=dict(nominal_thickness_mm=1,compressed_thickness_mm=.75,modeled_body=False),
        print_count=6,purchased_count=len(rows)-6,solid_count=len(rows),unchanged_sources=checks,
        status='Nominal CAD; no physical strength certification',source_revision_baseline=revision['baseline_git_commit'])
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    shutil.copyfile(source/'revision_validation.json',out/'validation/source_revision.json')
    from base_review import review
    review(out,source)
    print('Geometry copied from authoritative English sources:',len(rows),'solids',flush=True)
    return result
