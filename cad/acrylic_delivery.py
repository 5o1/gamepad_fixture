"""Archive an acrylic-base review for machining, printing and procurement."""
import csv,fnmatch,hashlib,json,math,shutil,zipfile
from pathlib import Path
from build123d import import_step,Location
from part_names import export_named_step,repair_step_names


def package(out):
 p=Path(out).resolve();m=json.loads((p/'manifest.json').read_text());review=json.loads((p/'validation/package_review.json').read_text())
 assert review['geometry_pass'] and review['all_names_readback']
 stage=p/'final_package'
 if stage.exists():shutil.rmtree(stage)
 stage.mkdir()
 def cp(src,rel):
  target=stage/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target);return rel
 def write(rel,text):
  target=stage/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,encoding='utf-8');return rel
 def table(rel,head,rows):
  target=stage/rel;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.writer(f);w.writerow(head);w.writerows(rows)
 def mdtable(head,rows):return '| '+' | '.join(head)+' |\n|'+'|'.join('---' for _ in head)+'|\n'+'\n'.join('| '+' | '.join(str(x).replace('\n','；') for x in r)+' |' for r in rows)+'\n'
 # Purchasing specifications; standard/dimension model is explicit when there
 # is no selected manufacturer SKU. No invented catalogue part numbers.
 definitions=[
 ('B01','亚克力底板',1,'件','按图定做 GP-FIX-PMMA16-A0；透明浇铸PMMA-GS，240×130×16mm','替代原打印底板；保留8组原孔位','必需','base_acrylic'),
 ('B02','底座固定螺丝',4,'颗','ISO4762 / M5×25 / 8.8级 / 全螺纹 / 内六角头','穿过原8mm法兰和上平垫，拧入底部M5螺母','必需','hardware_base_M5_*'),
 ('B03','底座螺丝上平垫',8,'片','ISO7089 M5；ID5.3×OD10×厚1.0mm；钢制','每颗M5螺丝头下2片；叠层已按2mm计','必需','hardware_base_top_washer_*'),
 ('B04','底座螺母厚平垫',4,'片','DIN7349 M5；ID5.3×OD15×厚2.0mm；钢制','放入亚克力底面沉孔，位于螺母和孔内台阶之间','必需','hardware_base_bottom_washer_*'),
 ('B05','底座螺母',4,'颗','ISO4032:2023 / M5×0.8 / 8级 / AF8 / 高度上限4.7mm','底面沉孔内，与M5×25螺丝配套；勿替换加高/尼龙防松螺母','必需','hardware_base_nut_*'),
 ('B06','钢销导杆',2,'根','ISO2338 Ø6h8×100mm，未淬硬；原规格例KILLICH 23381006100','两根导向杆，贯穿一体横梁、弹簧及滑块，底端压入下座','必需','guide_rod_*'),
 ('B07','压缩弹簧',2,'根','按参数选型/定制：OD11 / 线径1.1 / 自由长40mm；目标k=2N/mm；并紧长≤13mm','套在导杆上，名义装长30mm；每根目标20N；无已锁定厂商品号，供应商需确认力—位移','必需','hardware_compression_spring_*'),
 ('B08','M8转轴螺栓',1,'颗','ISO4017 M8×100，全螺纹，钢制8.8级；六角头AF13，头高5.3mm','贯穿两耳、齿盘和托架中心，配星形通孔把手','必需','hardware_M8_axis_bolt'),
 ('B09','M8大垫圈',3,'片','ISO7093类 M8；ID8.4×OD24×厚2.0mm；钢制','左螺栓头侧、托架凸台侧、右钢套管外侧，各1片','必需','hardware_M8_washer_*;hardware_M8_hub_washer'),
 ('B10','滑动钢套管',1,'件','按尺寸加工：外径12 / 内径8.4 / 长22mm；钢制，两端平整去毛刺','转轴右侧，穿过右耳；原装配X11..33，外伸4mm','必需','hardware_M8_sliding_sleeve'),
 ('B11','星形通孔把手',1,'件','Ganter DIN6336-KT-40-M8-D；PA本体/钢螺纹嵌件，M8通孔，外径40，总高25mm','M8转轴锁紧与释放；型号D必须为通孔，不能买盲孔版本','必需','hardware_M8_star_knob_envelope'),
 ('B12','调高螺栓',1,'颗','ISO4017 M6×70，全螺纹，钢制8.8级；六角头AF10','横向贯穿斜板、套筒和内立柱，选择三档高度','必需','hardware_M6_height_bolt'),
 ('B13','调高防松螺母',1,'颗','DIN985 M6×1，钢制尼龙圈防松螺母，AF10，总高约6mm','M6调高螺栓末端；规格按模型包络核对','必需','hardware_M6_locknut'),
 ('B14','M6大垫圈',2,'片','ISO7093类 M6；ID6.4×OD18×厚1.6mm；钢制','调高轴两侧，各1片','必需','hardware_M6_washer_*'),
 ('B15','固定齿盘安装螺丝',3,'颗','ISO4762 M3×12，钢制8.8级，圆柱头内六角','固定齿盘与左耳连接，0°/120°/240°三个位置','必需','hardware_fixed_ring_M3_*'),
 ('B16','转动齿盘安装螺丝',3,'颗','ISO4762 M3×20，钢制8.8级，圆柱头内六角','转动齿盘与托架连接，60°/180°/300°三个位置','必需','hardware_moving_ring_M3_*'),
 ('B17','齿盘安装螺母',6,'颗','DIN934 M3（旧版ISO4032尺寸）；AF5.5，高2.4mm，钢制','固定齿盘3颗、转动齿盘3颗，放入已有六角窝','必需','hardware_fixed_ring_nut_*;hardware_moving_ring_nut_*'),
 ('B18','手柄软垫材料',1,'张（裁3片）','2mm厚自粘硅胶片，建议至少100×100mm；按附带1:1模板裁出3片','上夹爪、下夹爪、背托；CAD含3片安装状态，实际采购为片材','必需','pad_*'),
 ('B19','桌夹',2,'把','C型螺旋桌夹；开口≥50mm；压脚建议≥Ø20；须能在桌边内10..20mm位置夹紧','将底板和25mm桌板夹在一起；保留左右两处；未锁定厂商品号/不在总装CAD里','必需',''),
 ('B20','底板防滑薄垫',1,'片','硅胶/相容防滑片，240×130×约1mm，自裁避开底面沉孔','底板与桌面之间；原装配按名义受压厚0.75mm建模，真实压缩量待确认；不在总装CAD里','必需',''),
 ('O01','M3热熔螺母',2,'颗','M3，外径4.6×长4mm；对应已有pilotØ4.1','一体横梁的可选止付孔；默认不安装','可选，默认不买',''),
 ('O02','M3平端止付螺钉',2,'颗','DIN913 / M3×6 / 平端内六角','与O01配套，顶住钢销；默认不安装','可选，默认不买','')]
 part_to_bom={};bom=[]
 for ident,name,qty,unit,model,use,status,patterns in definitions:
  matched=[r['name'] for r in m['parts'] if not r['is_printed'] and any(fnmatch.fnmatchcase(r['name'],s) for s in patterns.split(';') if s)]
  for n in matched:
   if n in part_to_bom:raise RuntimeError('Duplicate purchase mapping '+n)
   part_to_bom[n]=ident
  bom.append([ident,name,qty,unit,model,use,status,'；'.join(matched) or '无CAD（片材/桌夹/可选件）'])
 purchased=[r for r in m['parts'] if not r['is_printed']];assert set(part_to_bom)=={r['name'] for r in purchased}
 # Board machining CAD uses originX0,Y0,Z0, matching the paper and DXF.
 board=import_step(p/'edit_table_up/base_acrylic.step').solids()[0].moved(Location((120,130,-.75)));board.label='底板（16mm浇铸亚克力，加工坐标） [base_acrylic]'
 target=stage/'02_购买件/01_亚克力底板/CAD/base_acrylic_16.step';target.parent.mkdir(parents=True,exist_ok=True);export_named_step(board,target)
 cp(p/'machining/base_acrylic_16.dxf','02_购买件/01_亚克力底板/CAD/base_acrylic_16.dxf')
 for f in (p/'machining/paper').glob('*'):
  if f.is_file():cp(f,'02_购买件/01_亚克力底板/纸面图纸/'+f.name)
 print_rows=[];file_rows=[]
 for r in m['parts']:
  n=r['name'];title=r['display_name']
  if r['is_printed']:
   rel=cp(p/'print'/(n+'.stl'),'01_打印件/STL/'+n+'.stl');cp(p/'print'/(n+'.step'),'01_打印件/CAD/'+n+'.step')
   print_rows.append([n,title,1,'PETG',rel,'原已确认打印朝向；托架保留侧放；支撑由打印中心设置'])
   file_rows.extend([[rel,title,'正式打印件，1件，STL毫米'],['01_打印件/CAD/'+n+'.step',title,'对应打印方向CAD，非装配坐标']])
  else:
   folder='01_亚克力底板/CAD' if n=='base_acrylic' else ('03_软垫/CAD' if n.startswith('pad_') else '02_五金CAD')
   name=n+'_assembly.step' if n=='base_acrylic' else n+'.step'
   rel=cp(p/'edit_table_up'/(n+'.step'),'02_购买件/'+folder+'/'+name)
   file_rows.append([rel,title,'装配坐标；采购编号 '+part_to_bom[n]])
 table('01_打印件/打印清单.csv',['零件ID','名称', '数量','材料','STL文件','说明'],print_rows)
 write('01_打印件/打印说明.md','# 给打印中心\n\n正式打印件共6件，每件1个STL、数量1。STL单位mm，保持原尺寸。底板改为外购亚克力，不打印。托架保留当前侧放朝向；其余方向沿用已确认版本。\n\n'+mdtable(['零件ID','名称','数量','材料','STL文件','说明'],print_rows)+'\n材料PETG。齿盘齿面向上，沿用0.08–0.12mm层高的齿面计划；其余部件由打印中心按实际设备切片。套筒闭顶/耳孔、托架横孔/侧窗和悬臂、滑块R3下方需要局部可拆支撑。清除支撑，保持导孔、齿面和硅胶垫座面可用。现有文件是几何，不包含切片参数。\n\n钢销配合小样放在04_验证资料/导销配合小样，不属于上述6个正式部件，是否一并加工单独列项。\n')
 head=['编号','名称','数量','单位','型号及完整规格','用途和位置','采购状态','对应CAD零件ID']
 table('02_购买件/采购清单.csv',head,bom);write('02_购买件/采购清单.md','# 采购清单\n\n安装CAD含50个外购/加工实体；采购按商品合并，另列未建模桌夹、底垫及可选件。下表尺寸单位mm。标准件以标准、尺寸及等级作为订货型号；只有已确认厂家型号的项目写品牌，未确定厂商品号的如实标注。\n\n'+mdtable(head,bom)+'\n原底板8个M5热熔螺母和4颗M5×16取消；本版使用4套M5×25通孔连接。备用4孔暂不装五金。不要把采购50个CAD实体理解为50种商品。\n')
 write('02_购买件/装配工具清单.md','# 装配工具（已有则无需重复采购）\n\n|工具|数量|用途|\n|---|---:|---|\n|8mm薄壁套筒或螺母起子，外径≤16mm|1|进入Ø18底面沉孔，握持M5螺母；购买时核对实际外径|\n|4mm内六角工具|1|M5底座圆柱头螺丝|\n|2.5mm内六角工具|1|M3齿盘安装螺丝|\n|10mm扳手|2|M6调高螺栓与防松螺母|\n|13mm扭矩扳手/适配头|1|M8转轴头侧；沿用目标1.2N·m，不适用于M5底板螺丝|\n|卡尺、直尺|各1|核对厚度、孔径和端部内凹|\n\nM5底座没有已验证的拧紧扭矩；不可直接照搬全金属连接的扭矩表压紧亚克力和PETG法兰。\n')
 cp(Path(__file__).resolve().parents[1]/'design/source/pad_templates_A4.svg','02_购买件/03_软垫/pad_templates_A4.svg')
 # All requested display and grouped assemblies retain original positions.
 for n in ('assembly_with_controller.step','assembly.step','assembly_printed_parts.step','assembly_purchased_parts.step'):cp(p/n,'03_总装展示/'+n)
 if (p/'assembly_with_controller.png').exists():cp(p/'assembly_with_controller.png','03_总装展示/assembly_with_controller.png')
 for n in ('acrylic_geometry.json','package_review.json'):cp(p/'validation'/n,'04_验证资料/'+n)
 for n in ('results.json','螺丝强度计算说明.md'):cp(Path(__file__).resolve().parents[1]/'docs/validation'/n,'04_验证资料/螺丝静力计算/'+n)
 for ext in ('.stl','.step'):cp(p/'reference'/('guide_pin_coupon'+ext),'04_验证资料/导销配合小样/guide_pin_coupon'+ext)
 radius=dict(nut_AF_mm=8,nut_circumradius_mm=8/math.sqrt(3),nut_radial_margin_mm=1,
   washer_OD_mm=15,washer_radial_margin_mm=1.5,socket_max_OD_mm=16,socket_radial_margin_mm=1,
   required_R_mm=max(8/math.sqrt(3)+1,7.5+1.5,8+1),chosen_R_mm=9,chosen_diameter_mm=18)
 write('02_购买件/01_亚克力底板/沉孔尺寸依据.md','# 沉孔半径与深度\n\nM5螺母AF8，六角外接圆半径8/√3≈4.62mm；给螺母径向留1mm后需R≥5.62。底部DIN7349厚垫片外径15，给垫片径向留1.5mm需R≥9。8mm套筒实际外径限定≤16，给工具径向留1mm需R≥9。因此取R=max(5.62,9,9)=9mm，即Ø18。\n\n沉孔深9.5mm，从底面向上量。厚垫片2mm+M5螺母高度包络4.7mm，合计6.7mm；螺母底面名义内凹2.8mm。上方2片1mm普通垫片与8mm法兰配M5×25，螺丝端名义内凹1mm、伸过螺母1.8mm。沉孔上方还剩6.5mm亚克力。\n\n加工前确认板厚16mm成品目标可实现；装配前实测板厚、法兰厚、垫片和螺丝，核对端部不凸出且啮合完整。此计算是几何/工具余量，不是亚克力板体强度认证。\n\n依据：\n- [ISO4032:2023 M5螺母](https://cdn.standards.iteh.ai/samples/75016/5b1f83bd2dc44fc199973e9957a75086/ISO-4032-2023.pdf)\n- [DIN7349厚垫圈](https://fullerfasteners.com/tech/din-7349-specifications-thick-flat-washer/)\n- [ISO7089普通平垫](https://www.jcfasteners.com/wp-content/uploads/2019/10/ISO-7089-Plin-Washer-B4iD02-SS304.pdf)\n- [PLEXIGLAS连接指南](https://www.plexiglas.de/files/plexiglas-content/pdf/verarbeitungsrichtlinie/311-3-EN-joining-PLEXIGLAS.pdf)\n')
 write('02_购买件/01_亚克力底板/给加工商说明.md','# 亚克力底板加工说明\n\n加工1件透明浇铸PMMA底板，成品240×130×16mm。以纸面图纸中的坐标和深度加工：8×Ø6.5通孔；底面同轴8×Ø18平底沉孔、深9.5。不攻丝、不安装热熔母。外轮廓、孔位和目标公差见9页A3图册。\n\nCAD/base_acrylic_16.step及DXF使用加工坐标，外形范围X0..240、Y0..130、Z0..16；纸面图纸同坐标。base_acrylic_assembly.step保留原总装坐标，勿混用其原点下料。DXF的BOTTOM_COUNTERBORE层是底面定深加工，不是通切；深度以PDF/STEP为准。\n\n四个侧面不打孔。请按PMMA相容工艺钻铣、去毛刺与处理加工应力；避免崩边、裂纹和不必要的火焰抛光。目标公差需按加工能力确认，不能用原板标称厚度替代成品尺寸检验。装配采用垫片和螺母分散力，不将螺纹攻在PMMA里。\n')
 (stage/'04_验证资料/沉孔半径计算.json').write_text(json.dumps(radius,indent=2)+'\n')
 table('文件说明.csv',['文件','名称/对应零件','用途与坐标'],file_rows+[['02_购买件/01_亚克力底板/CAD/base_acrylic_16.step','亚克力底板CAD','加工坐标，单位mm，已切通孔和底面沉孔'],['03_总装展示/assembly_with_controller.step','带手柄总装','展示；56个夹具实体+手柄参考面壳；非打印文件']])
 write('文件说明.md','# 逐文件说明\n\n'+mdtable(['文件','名称/对应零件','用途与坐标'],file_rows)+'\n图纸目录内01..06为上、下、前、后、左、右六面，07为A—A板体剖面，08为五金连接剖面；每页有PDF及PNG，合并9页PDF为底板_六面与剖面_A3.pdf。孔位表.csv给出8孔中心、孔型、深度与默认使用状态。CAD加工原点与总装原点的区别见给加工商说明.md。\n')
 write('00_交付说明.md','# 16mm亚克力底板交付包\n\n1. 给打印中心：01_打印件/STL，6个正式PETG件，每件1份。清单见01_打印件/打印清单.csv。\n2. 给亚克力加工商：02_购买件/01_亚克力底板，含已挖孔的STEP、分层DXF、9页A3六面/剖面图及孔位表。底板16mm，保持原安装高度。\n3. 采购：02_购买件/采购清单.csv或.md，逐项列出型号/完整规格、数量、用途和CAD对应关系；工具另列。\n4. 展示：03_总装展示/assembly_with_controller.step，为安装手柄后的整体；手柄只作参考面壳，不打印、不计采购。另有不带手柄总装及打印/购买分组装配STEP，均保留位置。\n5. 每个打印/购买CAD文件的说明见文件说明.csv；标准五金CAD为尺寸包络，不含精细螺纹。\n\n本次改动：底板换为16mm浇铸PMMA，8组通孔与底面平底沉孔；底座螺丝改M5×25、明确8.8级，并配上下垫片和M5螺母。取消底板热熔母。其余35个原部件的几何和装配位置不变，6个正式打印件STL保持原文件。\n\n已执行：实体几何、完整STEP中文名称读回、56个实体及6/50分组核对、新五金与底板/法兰及彼此的实体交叠检查、名义底面不凸出检查。螺母按最大高4.7mm，螺丝端名义内凹1mm。\n\n范围：本轮未实物打印/机加工，未执行新的原生重放或材料有限元；PMMA孔边、沉孔剩余材料、打印法兰及桌夹承载/蠕变未获实物认证。钢螺丝静力报告仅适用于列明假设。上部保留此前用户接受的局部弹簧接触项，没有据此改成全部强度通过。加工尺寸/采购实物尺寸需按图核对。\n')
 summary=dict(kind='acrylic16_machining_and_printing_delivery',requirements=dict(acrylic_base_with_holes=True,nut_radius_and_clearance_calculated=True,six_faces_and_sections=True,print_purchase_archived=True,itemized_file_list=True,detailed_procurement=True,full_step_with_controller=True),
  geometry_review=review,production_print_parts=6,purchased_modeled_bodies=50,controller_reference='surface reference only',physical_strength_certified=False,physical_test_executed=False)
 (stage/'DELIVERY.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
 canonical=[r['display_name'] for r in m['parts']]+[
  '夹具（16mm亚克力底板） [fixture_acrylic16]',
  '夹具及手柄参考 [assembly_acrylic16]',
  '需要打印的部件（保留装配位置） [printed_parts]',
  '需要购买加工的部件（保留装配位置） [purchased_parts]',
  '手柄参考面壳（勿打印） [controller_reference_SURFACE]']
 for f in stage.rglob('*.step'):repair_step_names(f,canonical)
 repo=Path(__file__).resolve().parents[1]
 for name in ('LICENSE','THIRD_PARTY_NOTICES.md'):
  cp(repo/name,name)
  for directory in ('01_打印件','02_购买件/01_亚克力底板'):
   cp(repo/name,directory+'/'+name)
 for name in ('overview','mounted','acrylic'):
  f=repo/'docs/media'/(name+'.png')
  if f.exists():cp(f,'03_总装展示/'+name+'.png')
 # Make one ready-to-send bundle for each service, without mixing the display
 # assembly into production STL files.
 for archive,folder in [('给打印中心_STL.zip','01_打印件'),('给亚克力加工商.zip','02_购买件/01_亚克力底板')]:
  with zipfile.ZipFile(stage/archive,'w',zipfile.ZIP_DEFLATED) as z:
   for f in sorted((stage/folder).rglob('*')):
    if f.is_file() and not (archive.startswith('给打印') and '/CAD/' in f.as_posix()):
     z.write(f,f.relative_to(stage/folder).as_posix())
 descriptions={r[0]:r[1:] for r in file_rows}
 descriptions.update({
  '00_交付说明.md':['本轮交付入口','如何分别发送打印、加工和采购文件'],
  'DELIVERY.json':['交付状态摘要','五项要求及几何检查状态，不代表实物强度通过'],
  '给打印中心_STL.zip':['打印中心压缩包','6个正式STL、打印清单和说明，不含底板'],
  '给亚克力加工商.zip':['底板加工压缩包','底板CAD、9页A3图册、孔位表及加工说明'],
  '03_总装展示/assembly_with_controller.step':['带手柄总装STEP','56个夹具实体及手柄参考面壳，原装配坐标'],
  '03_总装展示/assembly.step':['不带手柄总装STEP','56个夹具实体，原装配坐标'],
  '03_总装展示/assembly_printed_parts.step':['打印件分组装配STEP','6件，保留装配位置；实际打印使用单件STL'],
  '03_总装展示/assembly_purchased_parts.step':['购买件分组装配STEP','50个实体，保留装配位置'],
  '03_总装展示/assembly_with_controller.png':['总装预览图','对应总STEP，亚克力用浅蓝实体显示'],
  '02_购买件/采购清单.csv':['采购清单','型号/完整规格、数量、用途及CAD对应'],
  '02_购买件/采购清单.md':['可读采购清单','与采购CSV相同内容'],
  '02_购买件/01_亚克力底板/CAD/base_acrylic_16.step':['亚克力底板CAD','加工坐标X0..240/Y0..130/Z0..16，单位mm'],
  '02_购买件/01_亚克力底板/CAD/base_acrylic_16.dxf':['底板分层DXF','轮廓、通孔、底面定深沉孔；不得全部通切'],
  '文件说明.csv':['逐文件索引','本表'], '文件说明.md':['逐文件索引','本表的Markdown版本']})
 complete=[]
 for f in sorted(stage.rglob('*')):
  if not f.is_file():continue
  rel=f.relative_to(stage).as_posix()
  if rel in descriptions:title,use=descriptions[rel]
  elif '/纸面图纸/' in rel:
   title='底板9页A3图册' if f.name.startswith('底板_') else ('孔位表' if f.suffix=='.csv' else '底板面视图/剖面 '+f.stem)
   use='标准图幅PDF，按100%打印' if f.suffix=='.pdf' else ('8孔坐标/孔型/深度' if f.suffix=='.csv' else '对应纸面图的PNG预览')
  elif rel.startswith('04_验证资料/'):
   title=f.stem;use='验证记录或独立配合小样，不属于6个正式打印件'
  elif rel.endswith('.svg'):title='软垫裁切模板';use='A4按100%打印，含100mm校准线'
  else:title=f.stem;use='对应目录的加工/打印/采购说明'
  complete.append([rel,title,use])
 complete.append(['SHA256SUMS','文件哈希清单','核对全部交付文件'])
 table('文件说明.csv',['文件','名称/对应零件','用途与坐标'],complete)
 write('文件说明.md','# 每个文件是什么\n\n'+mdtable(['文件','名称/对应零件','用途与坐标'],complete))
 hashes=[hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.relative_to(stage).as_posix() for f in sorted(stage.rglob('*')) if f.is_file() and f.name!='SHA256SUMS']
 (stage/'SHA256SUMS').write_text('\n'.join(hashes)+'\n')
 print('PACKAGE READY',stage,'payloads',len(hashes),flush=True)
 return stage

if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]/'build/acrylic16');args=a.parse_args();package(args.out)
