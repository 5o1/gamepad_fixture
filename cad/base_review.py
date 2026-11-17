"""Critical gates measured from exported STEP and recorded source history."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import numpy as np
from build123d import Edge, GeomType, import_step
from geometry import bounds, box
from column_lower_b import GateFailure, require, section_area, volume


def solid(path):
    s = import_step(path)
    require(len(s.solids()) == 1 and s.is_valid, f'C1: expected one valid solid: {path.name}')
    return s.solids()[0]


def cylinders(shape):
    rows = []
    for face in shape.faces():
        if face.geom_type != GeomType.CYLINDER:
            continue
        c = face.geom_adaptor().Cylinder(); o = c.Location(); d = c.Axis().Direction()
        rows.append(dict(radius_mm=c.Radius(), axis_origin_mm=[o.X(), o.Y(), o.Z()],
                         axis_direction=[d.X(), d.Y(), d.Z()], bounds_mm=bounds(face)))
    return rows


def seat_check(plate, column):
    top, bottom = bounds(plate)[1][2], bounds(column)[0][2]
    require(abs(top-bottom) <= 1e-6,
            f'C5 seat/contact failed: plate top Z={top:.6f}, flange bottom Z={bottom:.6f}, gap={bottom-top:.6f} mm')
    # Measure the actual common face, so a matching bounding box alone cannot pass.
    pa, ca = section_area(plate, top), section_area(column, bottom)
    from build123d import Compound, Plane
    a = Compound(children=list(plate.intersect(Plane(origin=(0, 0, top)))))
    b = Compound(children=list(column.intersect(Plane(origin=(0, 0, bottom)))))
    contact = (a & b).area
    expected = 90*50 - 4*math.pi*3.02**2
    require(abs(contact-expected) <= 1e-3, f'C5 seat/contact area failed: {contact} != {expected}')
    return dict(plate_top_z_mm=top, flange_bottom_z_mm=bottom, contact_area_mm2=contact,
                expected_contact_area_mm2=expected, plate_section_area_mm2=pa, flange_section_area_mm2=ca)


def review(out, source):
    out, source = Path(out), Path(source)
    m = json.loads((out/'manifest.json').read_text())
    lower = solid(out/'edit_table_up/column_lower.step')
    from source_identity import git_bytes, read_bytes, prove_name_only, prove_geometry, registration, geometry
    revision=json.loads((source/'revision_validation.json').read_text())
    root=Path(__file__).resolve().parents[1]
    baseline_ref=revision['baseline_git_commit']
    original=read_bytes(git_bytes(root,baseline_ref,'design/source/edit_table_up/column_lower.step')).solids()[0]
    print_registrations={}
    for row in m['parts']:
        if row['is_printed']:
            n=row['name']
            print_registrations[n]=registration(solid(source/'edit_table_up'/f'{n}.step'),solid(source/'print'/f'{n}.step'),[np.array(row['print_transform'])[:3,:3]],n)
            require(np.max(abs(np.array(row['print_transform'])-np.array(print_registrations[n]['matrix'])))<=1e-6,f'C3: manifest transform differs for {n}')
    expected = original.volume + 27000 - 4*math.pi*2.75**2*6 - 4*math.pi*(5.2**2-2.75**2)*6
    error = abs(lower.volume-expected)
    require(error <= 1e-3, f'C1: analytic volume error {error}')
    sections = [dict(z_mm=float(z), source_area_mm2=section_area(original, z), revised_area_mm2=section_area(lower, z))
                for z in np.linspace(24.8, 86.7, 10)]
    above = box(-100, 100, -100, 100, 24.75, 100)
    missing, added = volume((original-lower) & above), volume((lower-original) & above)
    require(missing <= 1e-6 and added <= 1e-6 and all(abs(r['source_area_mm2']-r['revised_area_mm2']) <= 1e-6 for r in sections),
            'C1: geometry above flange changed')
    holes = [r for r in cylinders(lower) if abs(r['radius_mm']-5.2) <= 1e-6]
    require(len(holes) == 4 and all(np.allclose(np.array(r['bounds_mm'])[:, 2], [18.75, 24.75], atol=1e-6, rtol=0) for r in holes),
            'C1: counterbore diameter/depth differs from design')
    checks = []
    for r in m['unchanged_sources']:
        n=r['part'];rel=f'design/source/edit_table_up/{n}.step'
        before=git_bytes(root,baseline_ref,rel);after=(root/rel).read_bytes()
        tokens=prove_name_only(before,after)
        proof=prove_geometry(read_bytes(before),solid(out/'edit_table_up'/f'{n}.step'),n)
        require(after==(out/'edit_table_up'/f'{n}.step').read_bytes(),f'C2: build differs from English source: {n}')
        checks.append(dict(part=n,name_tokens_changed=len(tokens),all_non_name_bytes_identical=True,**proof))
    require(len(checks)==34 and any(r['part']=='slider_upper_jaw' for r in checks),'C2: expected 34 retained sources including slider_upper_jaw')
    prints=[]
    for row in m['parts']:
        if row['is_printed'] and row['name']!='column_lower':
            n=row['name']+'.stl';before=git_bytes(root,baseline_ref,'design/source/print/'+n)
            require(before==(source/'print'/n).read_bytes()==(out/'print'/n).read_bytes(),f'C2: changed print STL {n}')
            prints.append(dict(file=n,sha256=hashlib.sha256(before).hexdigest(),byte_identical=True))
    require(len(prints)==5,'C2: expected five unchanged print STLs')
    base = solid(out/'edit_table_up/base_aluminum.step')
    require(np.max(abs(np.array(bounds(base))-np.array([[-120, -130, .75], [120, 0, 10.75]]))) <= 1e-6, 'C5: plate bounds differ')
    base_holes = cylinders(base)
    require(len(base_holes) == 8 and all(abs(r['radius_mm']-3.02) <= 1e-6 for r in base_holes), 'C4: insert hole envelopes differ')
    names = ['base_aluminum', 'column_lower'] + [r['name'] for r in m['parts'] if r['name'].startswith('hardware_base_')]
    solids = {n:solid(out/'edit_table_up'/f'{n}.step') for n in names}
    collisions, measured_pairs = [], []
    for a, b in itertools.combinations(names, 2):
        ba, bb = np.array(bounds(solids[a])), np.array(bounds(solids[b]))
        # Disjoint bounding boxes prove zero intersection; touching faces are allowed.
        if np.any(np.minimum(ba[1], bb[1])-np.maximum(ba[0], bb[0]) <= 0):
            v = 0.
        else:
            v = volume(solids[a] & solids[b])
        measured_pairs.append(dict(parts=[a, b], volume_mm3=v))
        if v > 1e-5:
            collisions.append(measured_pairs[-1])
    require(not collisions, f'C4: penetrating intersections: {collisions}')
    stacks = []
    for i in range(4):
        bolt = solids[f'hardware_base_M5_{i}']; b = np.array(bounds(bolt))
        x, y = b[:, :2].mean(0)
        old = np.array(bounds(read_bytes(git_bytes(root,baseline_ref,f'design/source/edit_table_up/hardware_base_M5_{i}.step')).solids()[0]))[:, :2].mean(0)
        require(np.max(abs(old-[x, y])) <= 1e-6, f'C5: bolt index mapping changed: {i}')
        require(np.max(abs(b[:, 2]-[1.75, 26.75])) <= 1e-6, f'C4: bolt Z stack changed: {i}')
        head = [c for c in cylinders(bolt) if abs(c['radius_mm']-4.25) <= 1e-6]
        require(len(head) == 1 and np.max(abs(np.array(head[0]['bounds_mm'])[:, 2]-[21.75, 26.75])) <= 1e-6, f'C4: bolt bearing Z changed: {i}')
        washers = []
        for j in range(3):
            z = np.array(bounds(solids[f'hardware_base_top_washer_{i}_{j}']))[:, 2]
            require(np.max(abs(z-[18.75+j, 19.75+j])) <= 1e-6, f'C4: washer Z changed: {i},{j}')
            washers.append(z.tolist())
        insert = next(s for n, s in solids.items() if n.startswith('hardware_base_insert_') and np.max(abs(np.array(bounds(s))[:, :2].mean(0)-[x, y])) <= 1e-6)
        iz = np.array(bounds(insert))[:, 2]
        require(np.max(abs(iz-[2.85, 10.35])) <= 1e-6 and b[0, 2] < iz[0], f'C4: full insert traversal failed: {i}')
        stacks.append(dict(index=i, xy_mm=[x, y], bolt_tip_z_mm=b[0, 2], bolt_head_z_mm=[21.75, 26.75],
                           washers_z_mm=washers, insert_z_mm=iz.tolist(), tip_above_underside_mm=b[0, 2]-.75,
                           tip_beyond_insert_mm=iz[0]-b[0, 2]))
    contact = seat_check(base, lower)
    for ext in ('.step', '.stl'):
        require((source/'reference'/('controller_table_up'+ext)).read_bytes() == (out/'reference'/('controller_table_up'+ext)).read_bytes(), 'C5: controller reference changed')
    require(m['table_from_pad_mm'] == json.loads((source/'manifest.json').read_text())['v3_2_table_from_pad'], 'C5: controller transform changed')
    from base_plate import make_plate
    from part_names import export_named_step
    negative = out/'validation/negative_plate_9.step'
    export_named_step(make_plate(9), negative)
    try:
        seat_check(solid(negative), lower)
    except GateFailure as exc:
        negative_message = str(exc)
    else:
        raise GateFailure('C6: negative control unexpectedly passed')
    # Reproduce the nearest above-flange material distance to each vertical bolt axis.
    upper = original & above
    distances = [dict(xy_mm=[x, y], radius_mm=upper.distance_to(Edge.make_line((x, y, 24.75), (x, y, 86.75))))
                 for x in (-35, 35) for y in (-14, -46)]
    height_holes = {n:[r for r in cylinders(solid(source/'edit_table_up'/f'{n}.step'))
                      if abs(r['axis_direction'][0]) > .999 and 2.8 < r['radius_mm'] < 3.6]
                    for n in ('column_lower', 'column_sleeve')}
    result = dict(geometry_pass=True, physical_test_executed=False, physical_strength_certified=False,
        C1=dict(pass_=True, single_valid_solid=True, source_volume_mm3=original.volume, exported_volume_mm3=lower.volume,
                analytic_volume_mm3=expected, volume_error_mm3=error, sections=sections,
                missing_above_flange_mm3=missing, added_above_flange_mm3=added, counterbores=holes),
        C2=dict(pass_=True, unchanged_sources=checks, unchanged_print_files=prints),
        C3=dict(pass_=True,prints=print_registrations,baseline_column_print=revision['derivation']['registered_source_print_transform']),
        C4=dict(pass_=True, pair_count=len(measured_pairs), max_penetration_mm3=max(r['volume_mm3'] for r in measured_pairs),
                penetrating_intersections=collisions, bolt_stacks=stacks, all_pairs=measured_pairs),
        C5=dict(pass_=True, **contact, upper_identity_pose=True, table_from_pad_mm=m['table_from_pad_mm']),
        C6=dict(pass_=True, changed_condition='plate thickness 9 instead of 10; support unchanged', failing_message=negative_message),
        reproduced_source_facts=dict(column_lower_bounds_mm=bounds(original), flange_z_mm=[16.75, 24.75],
            flange_xy_mm=[90, 50], mounting_holes=[r for r in cylinders(original) if abs(r['radius_mm']-2.75) <= 1e-6],
            nearest_above_flange_material=distances, height_lock_cylinder_features=height_holes))
    (out/'validation/gates.json').write_text(json.dumps(result, indent=2)+'\n')
    named_assembly=import_step(out/'assembly_with_controller.step')
    labels=[];pending=[named_assembly]
    while pending:
        q=pending.pop();labels.append(q.label);pending.extend(q.children)
    import re
    normalized={re.sub(r'[^A-Za-z0-9+\-]','',v) for v in labels}
    require(all(re.sub(r'[^A-Za-z0-9+\-]','',r['display_name']) in normalized for r in m['parts']),'C5: assembly names missing')
    (out/'validation/package_review.json').write_text(json.dumps(dict(geometry_pass=True, all_names_readback=True,
        note='Assembly names read back here; poses independently checked by scripts/validate.py'), indent=2)+'\n')
    print('Critical gates C1-C6 passed; negative control:', negative_message, flush=True)
    return result
