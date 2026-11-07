import csv,hashlib,json,re,subprocess,zipfile
from pathlib import Path
import numpy as np
from build123d import import_step,GeomType
import argparse
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'build/acrylic16');args=parser.parse_args()
p=args.out;stage=p/'final_package';m=json.loads((p/'manifest.json').read_text())
def bbox(s):
 b=s.bounding_box();return np.array([list(b.min),list(b.max)])
def named(s):
 r={};pending=[s]
 while pending:
  q=pending.pop();pending.extend(q.children);mat=re.search(r'\[([A-Za-z0-9_+\-]+)\]',q.label)
  if mat and len(q.solids())==1:r[mat.group(1)]=q.solids()[0]
 return r
assembly=import_step(stage/'03_总装展示/assembly_with_controller.step');actual=named(assembly)
assert len(assembly.solids())==56
pose=[]
for row in m['parts']:
 n=row['name'];s=import_step(p/'edit_table_up'/f'{n}.step').solids()[0];a=actual[n]
 error=float(abs(bbox(s)-bbox(a)).max());dv=abs(s.volume-a.volume)
 assert error<1e-6 and dv<1e-5,(n,error,dv)
 pose.append(dict(part=n,maximum_bbox_error_mm=error,volume_error_mm3=dv))
# Machining CAD: source origin differs intentionally from assembly, consistent
# with DXF and every dimensioned paper drawing.
base=import_step(stage/'02_购买件/01_亚克力底板/CAD/base_acrylic_16.step').solids()[0]
assert np.allclose(bbox(base),[[0,0,0],[240,130,16]],atol=1e-6)
faces=[]
for f in base.faces():
 if f.geom_type==GeomType.CYLINDER:
  c=f.geom_adaptor().Cylinder();o=c.Location();bb=bbox(f)
  faces.append(dict(radius=c.Radius(),x=o.X(),y=o.Y(),zmin=bb[0,2],zmax=bb[1,2]))
small=[r for r in faces if abs(r['radius']-3.25)<1e-6];large=[r for r in faces if abs(r['radius']-9)<1e-6]
assert len(small)==len(large)==8
assert all(abs(r['zmin']-0)<1e-6 and abs(r['zmax']-9.5)<1e-6 for r in large)
assert all(abs(r['zmin']-9.5)<1e-6 and abs(r['zmax']-16)<1e-6 for r in small)
assert sorted((round(r['x'],6),round(r['y'],6)) for r in large)==sorted((x+120,y+130) for x,y in m['board']['holes'])
import ezdxf
cad_dxf=ezdxf.readfile(stage/'02_购买件/01_亚克力底板/CAD/base_acrylic_16.dxf')
assert cad_dxf.units==ezdxf.units.MM
for layer,radius in [('THROUGH_D6_5',3.25),('BOTTOM_COUNTERBORE_D18_DEPTH9_5',9)]:
 circles=[c for c in cad_dxf.modelspace().query('CIRCLE') if c.dxf.layer==layer]
 assert len(circles)==8 and all(abs(c.dxf.radius-radius)<1e-8 for c in circles)
 assert sorted((round(c.dxf.center.x,6),round(c.dxf.center.y,6)) for c in circles)==sorted((x+120,y+130) for x,y in m['board']['holes'])
for kind,num in (('printed',6),('purchased',50)):
 s=import_step(stage/'03_总装展示'/f'assembly_{kind}_parts.step')
 assert len(s.solids())==num
 for n,a in named(s).items():assert np.max(abs(bbox(a)-bbox(actual[n])))<1e-6
stls=list((stage/'01_打印件/STL').glob('*.stl'));assert len(stls)==6
for f in stls:assert f.read_bytes()==((ROOT/'design/source/print')/f.name).read_bytes()
bom=list(csv.DictReader((stage/'02_购买件/采购清单.csv').open(encoding='utf-8-sig')))
covered=[]
for r in bom:
 assert all(r[k] for k in ('编号','名称','数量','单位','型号及完整规格','用途和位置','采购状态'))
 for n in r['对应CAD零件ID'].split('；'):
  if n in actual:covered.append(n)
assert set(covered)=={r['name'] for r in m['parts'] if not r['is_printed']}
assert len(covered)==50 and len(covered)==len(set(covered))
files={f.relative_to(stage).as_posix() for f in stage.rglob('*') if f.is_file()}
index=list(csv.DictReader((stage/'文件说明.csv').open(encoding='utf-8-sig')))
assert {r['文件'] for r in index}==files,sorted(files-{r['文件'] for r in index})
checks={name:sha for sha,name in (line.split('  ',1) for line in (stage/'SHA256SUMS').read_text().splitlines())}
assert set(checks)==files-{'SHA256SUMS'}
assert all(hashlib.sha256((stage/f).read_bytes()).hexdigest()==sha for f,sha in checks.items())
pdf=stage/'02_购买件/01_亚克力底板/纸面图纸/底板_六面与剖面_A3.pdf';info=subprocess.check_output(['pdfinfo',str(pdf)],text=True)
assert re.search(r'Pages:\s+9\b',info),info
assert 'A3' in info or re.search(r'Page size:\s+1190',info)
for name in ('给打印中心_STL.zip','给亚克力加工商.zip'):
 with zipfile.ZipFile(stage/name) as z:assert z.testzip() is None
with zipfile.ZipFile(stage/'给打印中心_STL.zip') as z:assert sum(s.endswith('.stl') for s in z.namelist())==6
result=dict(pass_=True,requirements_all_5_delivered=True,files=len(files),hashed_payloads=len(checks),
 solids_with_controller_reference=56,printed=6,purchased=50,bom_rows=len(bom),all_50_modeled_purchases_covered_once=True,
 full_named_assembly_poses_and_volumes_match_individual_parts=True,pose_measurements=pose,
 machining_board_bounds_mm=bbox(base).tolist(),measured_cylindrical_faces=faces,
 paper_sheets=9,paper_format='A3',physical_strength_certified=False,physical_test_executed=False)
(p/'final_review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('pose_measurements','measured_cylindrical_faces')},indent=2))
