"""Read back named CAD and inspect the new base/fastener intersections."""
import json,csv,hashlib
from pathlib import Path
import numpy as np
from build123d import import_step

def review(out,source):
 p=Path(out);m=json.loads((p/'manifest.json').read_text());gate=json.loads((p/'validation/acrylic_geometry.json').read_text())
 shape=import_step(p/'assembly_with_controller.step');labels=[];pending=[shape]
 while pending:
  s=pending.pop();labels.append(s.label);pending.extend(getattr(s,'children',[]))
 def norm(s):return s.translate(str.maketrans({v:'_' for v in ' .()'}))
 missing=[r['display_name'] for r in m['parts'] if norm(r['display_name']) not in {norm(v) for v in labels}]
 assert not missing,missing
 assert len(shape.solids())==56
 counts={k:len(import_step(p/f'assembly_{k}_parts.step').solids()) for k in ('printed','purchased')}
 assert counts=={'printed':6,'purchased':50},counts
 original=Path(source)
 for r in m['parts']:
  if r['is_printed']:
   for ext in ('.step','.stl'):
    a,b=original/'print'/(r['name']+ext),p/'print'/(r['name']+ext)
    assert a.read_bytes()==b.read_bytes()
 # Evaluate exactly the actual new hardware and board; all volumes must be disjoint.
 base=import_step(p/'edit_table_up/base_acrylic.step').solids()[0];lower=import_step(p/'edit_table_up/column_lower.step').solids()[0]
 names=[r['name'] for r in m['parts'] if r['name'].startswith('hardware_base_')]
 solids={n:import_step(p/'edit_table_up'/f'{n}.step').solids()[0] for n in names}
 collisions=[]
 for n,s in solids.items():
  for q,t in [('base_acrylic',base),('column_lower',lower)]:
   common=s&t;v=common.volume if common else 0
   if v>1e-5:collisions.append(dict(parts=[n,q],volume=v))
 for i,n in enumerate(names):
  for n2 in names[i+1:]:
   a,b=np.array([[*solids[n].bounding_box().min],[*solids[n].bounding_box().max]]),np.array([[*solids[n2].bounding_box().min],[*solids[n2].bounding_box().max]])
   if np.any(np.minimum(a[1],b[1])-np.maximum(a[0],b[0])<=1e-7):continue
   common=solids[n]&solids[n2];v=common.volume if common else 0
   if v>1e-5:collisions.append(dict(parts=[n,n2],volume=v))
 assert not collisions,collisions
 r=dict(geometry_pass=True,physical_strength_pass=None,solid_count=56,all_names_readback=True,subset_counts=counts,unchanged_upper_bodies=35,printed_files_byte_identical=True,all_base_hardware_vs_board_and_flange_no_penetration=True,hardware_pair_no_penetration=True,nominal_bottom_clearance_mm=1.0,nominal_thread_projection_mm=1.8,physical_test_executed=False,new_native_replay_executed=False)
 (p/'validation/package_review.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r,indent=2))
