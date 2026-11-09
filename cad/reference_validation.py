"""Cross-check the generated print order and URDF against the single palette."""
import csv,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import trimesh
from palette import load_palette,part_color,rgba

def check(out,palette_path=None,render_record=None):
    out=Path(out);palette=load_palette() if palette_path is None else load_palette(palette_path)
    manifest=json.loads((out/'manifest.json').read_text());parts={p['name']:p for p in manifest['parts']}
    rows=list(csv.DictReader((out/'color_reference/print_colors.csv').open(encoding='utf-8-sig')))
    expected={p['name'] for p in parts.values() if p['is_printed']}
    assert {r['part_id'] for r in rows}==expected
    for r in rows:
        assert r['sRGB_HEX']==part_color(palette,r['part_id'],True)['hex']
        assert (out/'print'/r['STL_file']).is_file()
    folder=out/'simulation_reference';tree=ET.parse(folder/'fixture.urdf').getroot()
    assert len(tree.findall('link'))==len(parts)+1 and len(tree.findall('joint'))==len(parts)
    assert not tree.findall('.//inertial') and not tree.findall('.//collision')
    materials={m.get('name'):np.fromstring(m.find('color').get('rgba'),sep=' ') for m in tree.findall('material')}
    measured={p['part_id']:p for p in json.loads((folder/'parts.json').read_text())}
    origins={j.find('child').get('link'):np.fromstring(j.find('origin').get('xyz'),sep=' ') for j in tree.findall('joint')}
    for link in tree.findall('link'):
        name=link.get('name')
        if name=='fixture_root':continue
        visual=link.find('visual');mesh_node=visual.find('geometry/mesh');mesh_path=folder/mesh_node.get('filename')
        assert mesh_path.is_file() and mesh_node.get('scale')=='1 1 1'
        assert np.allclose(materials[visual.find('material').get('name')],rgba(part_color(palette,name,parts[name]['is_printed'])['hex']),rtol=0,atol=1e-8)
        mesh=trimesh.load(mesh_path,force='mesh',process=False);world=mesh.bounds*1000+origins[name]*1000
        assert np.max(abs(world-np.asarray(measured[name]['CAD_bounds_mm'])))<=.05
    for filename in ('fixture.urdf','fixture_ros.urdf'):
        r=ET.parse(folder/filename).getroot();assert len(r.findall('./link/visual'))==len(parts)
        assert all(j.get('type')=='fixed' for j in r.findall('joint'))
    result=dict(pass_=True,printed_color_rows=len(rows),URDF_visuals=len(parts),all_color_values_match=True,all_meshes_load=True,all_world_bounds_match=True,inertial_or_collision_parameters_supplied=False)
    if render_record is not None:
        render=json.loads(Path(render_record).read_text());assert render['printed_part_colors']=={n:c['hex'] for n,c in palette['printed_parts'].items()};result['render_colors_match']=True
    (out/'validation/color_reference.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Color reference checks:',result,flush=True)
    return result
