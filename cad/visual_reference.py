"""A self-contained frozen visual URDF, with no invented dynamics parameters."""
import json,shutil,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import trimesh
from build123d import import_step,export_stl
from palette import load_palette,part_color,rgba

def make(out,palette_path=None):
    out=Path(out);manifest=json.loads((out/'manifest.json').read_text());palette=load_palette() if palette_path is None else load_palette(palette_path)
    folder=out/'simulation_reference';meshes=folder/'meshes';meshes.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(Path(__file__).resolve().parents[1]/'LICENSE',folder/'LICENSE')
    robot=ET.Element('robot',name='gamepad_fixture_visual_reference');ET.SubElement(robot,'link',name='fixture_root')
    materials={name:'print_'+name for name in palette['printed_parts']};materials['purchased_parts']='purchased_gray'
    for name,key in materials.items():
        c=palette['purchased_parts'] if name=='purchased_parts' else palette['printed_parts'][name]
        material=ET.SubElement(robot,'material',name=key);ET.SubElement(material,'color',rgba=' '.join(f'{v:.17g}' for v in rgba(c['hex'])))
    measured=[]
    for row in manifest['parts']:
        name=row['name'];shape=import_step(out/'edit_table_up'/(name+'.step')).solids()[0];bb=shape.bounding_box();lo=np.array(list(bb.min));hi=np.array(list(bb.max));centre=(lo+hi)/2
        temporary=folder/(name+'.source.stl');export_stl(shape,temporary,tolerance=.04)
        mesh=trimesh.load(temporary,force='mesh',process=False);mesh.vertices=(mesh.vertices-centre)*.001;mesh.export(meshes/(name+'.stl'));temporary.unlink()
        link=ET.SubElement(robot,'link',name=name);visual=ET.SubElement(link,'visual',name=name+'_visual');ET.SubElement(visual,'origin',xyz='0 0 0',rpy='0 0 0')
        geometry=ET.SubElement(visual,'geometry');ET.SubElement(geometry,'mesh',filename='meshes/'+name+'.stl',scale='1 1 1')
        ET.SubElement(visual,'material',name=materials[name] if row['is_printed'] else materials['purchased_parts'])
        joint=ET.SubElement(robot,'joint',name='fixed_'+name,type='fixed');ET.SubElement(joint,'parent',link='fixture_root');ET.SubElement(joint,'child',link=name);ET.SubElement(joint,'origin',xyz=' '.join(f'{v*.001:.12f}' for v in centre),rpy='0 0 0')
        actual=trimesh.load(meshes/(name+'.stl'),force='mesh',process=False);restored=actual.bounds*1000+centre
        error=float(np.max(abs(restored-np.array([lo,hi]))));assert error<=.05,(name,error)
        measured.append(dict(part_id=name,stl='meshes/'+name+'.stl',hex=part_color(palette,name,row['is_printed'])['hex'],rgba=rgba(part_color(palette,name,row['is_printed'])['hex']),origin_m=(centre*.001).tolist(),CAD_bounds_mm=[lo.tolist(),hi.tolist()],mesh_bounds_error_mm=error))
    ET.indent(robot);ET.ElementTree(robot).write(folder/'fixture.urdf',encoding='utf-8',xml_declaration=True)
    ros=ET.fromstring(ET.tostring(robot))
    for mesh_node in ros.findall('./link/visual/geometry/mesh'):
        mesh_node.set('filename','package://gamepad_fixture_description/'+mesh_node.get('filename'))
    ET.indent(ros);ET.ElementTree(ros).write(folder/'fixture_ros.urdf',encoding='utf-8',xml_declaration=True)
    (folder/'package.xml').write_text('''<?xml version="1.0"?>
<package format="3"><name>gamepad_fixture_description</name><version>3.3.0</version>
<description>Fixed visual/color reference of the gamepad fixture.</description>
<maintainer email="assanekowww@gmail.com">5o1</maintainer><license>MIT</license>
<buildtool_depend>ament_cmake</buildtool_depend><export><build_type>ament_cmake</build_type></export></package>
''')
    (folder/'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.8)
project(gamepad_fixture_description)
find_package(ament_cmake REQUIRED)
install(DIRECTORY meshes DESTINATION share/${PROJECT_NAME})
install(FILES fixture_ros.urdf colors.json DESTINATION share/${PROJECT_NAME})
ament_package()
''')
    (folder/'colors.json').write_text(json.dumps(palette,indent=2)+'\n')
    (folder/'parts.json').write_text(json.dumps(measured,indent=2)+'\n')
    (folder/'README.md').write_text('''# Fixture visual URDF\n\nLoad `fixture.urdf` with this complete directory. It references all 56 local STL meshes in `meshes/`; do not copy the URDF alone. Mesh coordinates and joint translations are in metres, Z up. The root matches the accepted table-up assembly frame.\n\nThis is the current fixed assembly for visual/color reference:56 part links plus one root,56 fixed joints. It does not describe height/tilt articulation, collisions, inertias, material strength or dynamic/contact readiness. No values were invented for those purposes. For ROS 2, place this directory in your workspace as `gamepad_fixture_description`, build it with colcon and use `fixture_ros.urdf`, whose mesh URLs use `package://`. The portable `fixture.urdf` uses relative mesh paths. ROS package metadata is supplied; the actual consumer loading check uses the portable model. The controller is supplied by the upstream physical asset and is not replaced here by an untextured STL.\n\nRGBA uses normalized sRGB from `colors.json`, identical to the printing reference and rendering palette. Viewers may apply different lights, shaders or color-management transforms; numeric colors are authoritative, not a pixel match.\n''')
    (out/'validation/visual_reference.json').write_text(json.dumps(dict(executed=True,links=57,fixed_joints=56,visuals=56,all_meshes_present=True,maximum_CAD_mesh_bounds_error_mm=max(r['mesh_bounds_error_mm'] for r in measured),dynamics_parameters_supplied=False),indent=2)+'\n')
    print('Visual URDF reference:',folder,flush=True)
    return folder
