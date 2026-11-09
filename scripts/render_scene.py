"""Extend the approved Xbox Cycles scene with actual fixture CAD meshes.
Run with Blender4.5 in background, approved.blend loaded, -- payload_dir round.
The controller freeze/mesh evaluation follows xbox_gamepad_physics.web.cycles_worker.
"""
import bpy,json,math,sys,hashlib,itertools
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector
import argparse
parser=argparse.ArgumentParser();parser.add_argument('input_dir',type=Path);parser.add_argument('round',type=int,choices=(1,2,3));parser.add_argument('--palette',type=Path,required=True);parser.add_argument('--only',choices=('overview','mounted','acrylic'));args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
root=args.input_dir;round_id=args.round;palette=json.loads(args.palette.read_text());data=json.loads((root/'payload.json').read_text());arrays=np.load(root/'meshes.npz');scene=bpy.context.scene
scene.frame_set(0);graph=bpy.context.evaluated_depsgraph_get();originals=list(scene.objects)
helpers={p.custom_shape for o in originals if o.type=='ARMATURE' for p in o.pose.bones if p.custom_shape}
objects=sorted((o for o in originals if o.type=='MESH' and o not in helpers),key=lambda o:o.name)
controller=[];T=np.asarray(data['table_from_pad_mm']);T[:3,3]*=.001;visual_root=Matrix(T.tolist())@Matrix.Scale(data['controller_width_scale_m'],4)
for obj in objects:
 evaluated=obj.evaluated_get(graph);mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=graph);transform=evaluated.matrix_world.copy();mesh.transform(transform)
 if transform.to_3x3().determinant()<0:mesh.flip_normals()
 static=bpy.data.objects.new('controller_'+obj.name,mesh);scene.collection.objects.link(static);static.matrix_world=visual_root;controller.append(static)
for obj in originals:
 if obj.type in ('MESH','ARMATURE'):bpy.data.objects.remove(obj,do_unlink=True)
assert len(controller)==16
scene.cycles.device='CPU';scene.cycles.samples={1:16,2:32,3:64}[round_id];scene.cycles.use_denoising=True
scene.cycles.adaptive_threshold=.025 if round_id==1 else .012
scene.render.threads_mode='FIXED';scene.render.threads=8
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
scene.render.use_file_extension=True
camera=scene.camera;camera.data.type='PERSP';camera.data.sensor_fit='VERTICAL';camera.data.angle=math.radians(35);camera.data.clip_start=.0001;camera.data.clip_end=100
# Original controller materials, packed maps, color management and HDRWorld
# are retained. Only fixture/camera/background composition are added.
def rgba(h):
 v=[int(h[i:i+2],16)/255 for i in (1,3,5)]
 return [x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in v]+[1]
def material(name,color,rough=.4,metal=0,transparent=0,glass=False):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;links=m.node_tree.links;p=n.get('Principled BSDF');p.inputs['Base Color'].default_value=rgba(color);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 if glass:p.inputs['Transmission Weight'].default_value=1.;p.inputs['IOR'].default_value=1.49
 if transparent:
  out=n.get('Material Output');tr=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader');mix.inputs[0].default_value=transparent;links.new(p.outputs['BSDF'],mix.inputs[1]);links.new(tr.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],out.inputs['Surface'])
 return m
purchase=material('Purchased_uniform_gray',palette['purchased_parts']['hex'],.36,.15)
metal=material('Hardware_satin_steel',palette['presentation_materials']['metal_hex'],.25,.72)
glass=material('Acrylic_clear',palette['presentation_materials']['clear_acrylic_hex'],.075,glass=True)
technicalglass=material('Acrylic_technical_transparency',palette['presentation_materials']['technical_acrylic_hex'],.18,transparent=.76)
blue=material('Through_hole_blue',palette['hole_annotations']['through']['hex'],.28,transparent=.38);orange=material('Counterbore_orange',palette['hole_annotations']['counterbore']['hex'],.3,transparent=.4)
colors={k:material('Print_'+k,v['hex'],.38) for k,v in palette['printed_parts'].items()}
fixture=[];byname={}
for row in data['parts']:
 name=row['name'];me=bpy.data.meshes.new(name);me.from_pydata(arrays[name+'_v'].tolist(),[],arrays[name+'_f'].tolist());me.update();me.set_sharp_from_angle(angle=math.radians(35))
 for poly in me.polygons:poly.use_smooth=True
 obj=bpy.data.objects.new(name,me);scene.collection.objects.link(obj);fixture.append(obj);byname[name]=obj
 obj.data.materials.append(colors[name] if row['printed'] else purchase)
 # Subtle edge highlight only, below the manufacturing feature sizes.
 if row['printed'] or name=='base_acrylic':
  bevel=obj.modifiers.new('Presentation_micro_edge','BEVEL');bevel.width=.00012;bevel.segments=2;bevel.limit_method='ANGLE';bevel.angle_limit=.65
normal_floor=material('Studio_floor','#edece7',.75)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0));floor=bpy.context.object;floor.name='Presentation_floor';floor.data.materials.append(normal_floor)
# Highlight precisely the two disjoint portions of the removed hole volume.
markers=[]
def annulus(name,x,y,r0,r1,z0,z1):
 n=96;v=[]
 for z in (z0,z1):
  for rad in (r0,r1):v.extend([(x+rad*math.cos(2*math.pi*i/n),y+rad*math.sin(2*math.pi*i/n),z) for i in range(n)])
 f=[]
 for i in range(n):
  j=(i+1)%n
  f.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new(name,me);scene.collection.objects.link(o);o.data.materials.append(orange);markers.append(o)
for idx,(x,y) in enumerate(data['board']['holes']):
 x,y=x*.001,y*.001
 bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=.00325,depth=.016,location=(x,y,.00875));o=bpy.context.object;o.name=f'through_{idx}';o.data.materials.append(blue);markers.append(o)
 annulus(f'counterbore_{idx}',x,y,.00325,.009,.00075,.01025)
# Thin outline of the acrylic outer edges makes all transparent boundaries clear.
outline=material('Acrylic_outline','#5d7c89',.5);corners=list(itertools.product((-.120,.120),(-.130,0),(.00075,.01675)))
for i,a in enumerate(corners):
 for b in corners[i+1:]:
  if sum(abs(x-y)>1e-7 for x,y in zip(a,b))!=1:continue
  cu=bpy.data.curves.new('outline','CURVE');cu.dimensions='3D';cu.bevel_depth=.00009;cu.bevel_resolution=2;sp=cu.splines.new('POLY');sp.points.add(1)
  for point,co in zip(sp.points,(a,b)):point.co=(*co,1)
  o=bpy.data.objects.new('Acrylic_outline',cu);scene.collection.objects.link(o);o.data.materials.append(outline);markers.append(o)
out=root/f'round{round_id}';out.mkdir(exist_ok=True)
records=[]
for mode in ([args.only] if args.only else ('overview','mounted','acrylic')):
 for o in controller:o.hide_render=mode!='mounted'
 for o in fixture:o.hide_render=mode=='acrylic' and o.name!='base_acrylic'
 for o in markers:o.hide_render=mode!='acrylic'
 for row in data['parts']:
  o=byname[row['name']];o.data.materials.clear()
  mat=(colors[row['name']] if row['printed'] else purchase) if mode=='overview' else (colors[row['name']] if row['printed'] else (glass if row['name']=='base_acrylic' else metal))
  if mode=='acrylic':mat=technicalglass
  o.data.materials.append(mat)
 floor.location.z=-.025 if mode=='acrylic' else 0
 if mode=='overview':eye=(-.42,-.48,.34);target=(0,-.055,.13)
 elif mode=='mounted':eye=(.42,-.50,.37);target=(0,-.05,.145)
 else:eye=(.23,-.29,.24);target=(0,-.065,.008)
 if round_id>=2:
  if mode=='overview':eye=(-.46,-.54,.37);target=(0,-.055,.115)
  elif mode=='mounted':eye=(.45,-.55,.40);target=(0,-.055,.12)
  else:eye=(.21,-.25,.22);target=(0,-.065,.008)
 camera.location=eye;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
 scene.render.resolution_x=800 if round_id==1 else (1200 if round_id==2 else 2000)
 scene.render.resolution_y=800 if mode!='acrylic' else int(scene.render.resolution_x*.72)
 if mode!='acrylic':scene.render.resolution_y=scene.render.resolution_x
 # Exact fit of visible-object bounds in the real camera frustum.
 from bpy_extras.object_utils import world_to_camera_view
 scene.view_layers[0].update()
 visible=[o for o in fixture+controller if not o.hide_render]
 points=[o.matrix_world@Vector(v) for o in visible for v in o.bound_box]
 rotation=camera.rotation_euler.to_matrix();right=rotation@Vector((1,0,0));up=rotation@Vector((0,1,0));forward=rotation@Vector((0,0,-1))
 rr=[v.dot(right) for v in points];uu=[v.dot(up) for v in points];ff=[v.dot(forward) for v in points]
 aim=right*((min(rr)+max(rr))/2)+up*((min(uu)+max(uu))/2)+forward*((min(ff)+max(ff))/2)
 frame=camera.data.view_frame(scene=scene)
 tan_x=max(abs(v.x/v.z) for v in frame);tan_y=max(abs(v.y/v.z) for v in frame)
 offsets=[v-aim for v in points]
 distance=max(max(abs(v.dot(right))/(.82*tan_x)-v.dot(forward),abs(v.dot(up))/(.82*tan_y)-v.dot(forward)) for v in offsets)*1.02
 camera.location=aim-forward*distance
 scene.view_layers[0].update()
 projected=[world_to_camera_view(scene,camera,v) for v in points]
 projection_bounds=[min(v.x for v in projected),max(v.x for v in projected),min(v.y for v in projected),max(v.y for v in projected)]
 assert min(projection_bounds[0],projection_bounds[2])>.03 and max(projection_bounds[1],projection_bounds[3])<.97,projection_bounds
 eye=list(camera.location);target=list(aim)
 scene.render.filepath=str(out/(mode+'.png'));bpy.ops.render.render(write_still=True)
 records.append(dict(mode=mode,eye=eye,target=target,resolution=[scene.render.resolution_x,scene.render.resolution_y],samples=scene.cycles.samples,projection_bounds=projection_bounds))
record=dict(blender=bpy.app.version_string,engine=scene.render.engine,device=scene.cycles.device,scene_sha256=hashlib.sha256((root/'approved.blend').read_bytes()).hexdigest(),view_transform=scene.view_settings.view_transform,look=scene.view_settings.look,exposure=scene.view_settings.exposure,gamma=scene.view_settings.gamma,controller_parts=16,controller_materials_preserved=True,printed_part_colors={k:v['hex'] for k,v in palette['printed_parts'].items()},palette_sha256=hashlib.sha256(args.palette.read_bytes()).hexdigest(),world='Approved Boiler Room, strength1.0; no new light objects',composition_changes='New fixture meshes, floor, presentation camera and transparent film; controller materials/UV/maps untouched',round=round_id,renders=records)
(out/'record.json').write_text(json.dumps(record,indent=2));print('ROUND_COMPLETE',round_id)
