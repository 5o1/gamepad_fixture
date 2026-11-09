import json,sys,hashlib
from importlib.metadata import version
from pathlib import Path
import numpy as np
from yourdfpy import URDF
root=Path(sys.argv[1]);model=URDF.load(str(root/'fixture.urdf'),build_scene_graph=True,load_meshes=True)
assert len(model.robot.links)==57 and len(model.robot.joints)==56
assert len(model.scene.geometry)==56
expected=json.loads((root/'parts.json').read_text());checked=[];materials={m.name:m for m in model.robot.materials}
for row in expected:
 link=model.link_map[row['part_id']];visual=link.visuals[0]
 material=visual.material
 color=material.color if material.color is not None else materials[material.name].color
 values=np.asarray(color.rgba);assert np.allclose(values,row['rgba'],atol=1e-8),(row['part_id'],values,row['rgba'])
 matrix=model.get_transform(row['part_id'],model.base_link);assert np.allclose(matrix[:3,3],row['origin_m'],atol=1e-9)
 assert link.inertial is None and not link.collisions
 checked.append(row['part_id'])
expected_colors=[np.rint(np.asarray(row['rgba'])*255) for row in expected]
actual_colors=[np.asarray(g.visual.main_color,dtype=float) for g in model.scene.geometry.values()]
maximum_channel_error=max(min(float(abs(a-b).max()) for b in expected_colors) for a in actual_colors)
assert maximum_channel_error<=1
result=dict(actual_URDF_consumer='yourdfpy',consumer_version=version('yourdfpy'),urdf_sha256=hashlib.sha256((root/'fixture.urdf').read_bytes()).hexdigest(),links=len(model.robot.links),fixed_joints=len(model.robot.joints),loaded_meshes=len(model.scene.geometry),checked_materials=len(checked),all_colors_and_transforms_match=True,base_link=model.base_link,loaded_visual_color_channel_error_max=maximum_channel_error)
(root/'consumer_check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
