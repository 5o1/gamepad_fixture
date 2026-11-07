"""A3 paper drawings, six specified faces plus board/fastener sections."""
import json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle,Circle


def make(out):
 p=Path(out);folder=p/'machining/paper';folder.mkdir(parents=True,exist_ok=True)
 plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False,'font.size':9})
 perspective=p/'acrylic_perspective.png';total=9 if perspective.exists() else 8
 m=json.loads((p/'manifest.json').read_text());holes=[(i+1,x+120,y+130) for i,(x,y) in enumerate(m['board']['holes'])]
 def sheet(title,num,scale='1:1'):
  fig=plt.figure(figsize=(420/25.4,297/25.4));a=fig.add_axes([0,0,1,1]);a.set(xlim=(0,420),ylim=(0,297));a.set_aspect('equal');a.axis('off')
  a.add_patch(Rectangle((10,10),400,277,fill=False,lw=.8));a.text(18,275,title,fontsize=16)
  a.text(18,265,'单位 mm · 第三角法（独立视图） · 尺寸数值优先 · 按100%打印保持标注比例',fontsize=9)
  a.add_patch(Rectangle((210,10),200,29,fill=False,lw=.6));a.plot([210,410],[22,22],color='k',lw=.5);a.plot([325,325],[10,39],color='k',lw=.5)
  a.text(214,31,'零件：底板 / 浇铸PMMA / 成品厚16');a.text(329,31,'图号 GP-FIX-PMMA16-A0',fontsize=8)
  a.text(214,15,f'比例 {scale}    图幅 A3    {num}/{total}    2026-11-07',fontsize=8)
  a.text(329,15,'几何核对；非承载认证',fontsize=8)
  a.text(18,15,'基准：左下角为X0/Y0，底面B为Z0；CAD加工坐标同图纸。',fontsize=8)
  return fig,a
 def line(a,p1,p2,hidden=False):a.plot([p1[0],p2[0]],[p1[1],p2[1]],color='#3b4146' if hidden else 'k',lw=.55 if hidden else .8,ls=(0,(3,2)) if hidden else '-')
 def dim(a,p1,p2,text,shift=(0,0)):
  p1,p2,o=map(lambda x:__import__('numpy').array(x,float),(p1,p2,shift));line(a,p1,p1+o*1.15,True);line(a,p2,p2+o*1.15,True)
  a.annotate('',xy=p1+o,xytext=p2+o,arrowprops=dict(arrowstyle='<->',lw=.6,shrinkA=0,shrinkB=0));c=(p1+p2)/2+o
  a.text(c[0]+(2 if p1[0]==p2[0] else 0),c[1]+(2 if p1[1]==p2[1] else 0),text,fontsize=9,rotation=90 if p1[0]==p2[0] else 0,ha='left' if p1[0]==p2[0] else 'center',bbox=dict(facecolor='white',edgecolor='none',pad=.4))
 def textlines(a,lines,x=18,y=84,dy=6,size=8.3):
  for i,s in enumerate(lines):a.text(x,y-i*dy,s,fontsize=size)
 def circles(a,ox,oy,bottom=False):
  for n,x,y in holes:
   X=240-x if bottom else x
   for r,hidden in ((9,not bottom),(3.25,False)):
    a.add_patch(Circle((ox+X,oy+y),r,fill=False,lw=.7,ls=(0,(3,2)) if hidden else '-'))
   line(a,(ox+X-5,oy+y),(ox+X+5,oy+y),True);line(a,(ox+X,oy+y-5),(ox+X,oy+y+5),True)
   a.text(ox+X+10,oy+y+2,f'H{n:02d}',fontsize=7)
 def profile(a,ox,oy,width,axis,mirror=False):
  a.add_patch(Rectangle((ox,oy),width,16,fill=False,lw=.9));positions=(85,155) if axis=='X' else (20,52,84,116)
  for x in positions:
   X=width-x if mirror else x
   for r in (3.25,9):
    z0=0 if r==9 else 9.5;z1=9.5 if r==9 else 16
    for sign in (-1,1):line(a,(ox+X+sign*r,oy+z0),(ox+X+sign*r,oy+z1),True)
   line(a,(ox+X-9,oy+9.5),(ox+X+9,oy+9.5),True)
  dim(a,(ox,oy),(ox+width,oy),str(width),(0,-13));dim(a,(ox+width,oy),(ox+width,oy+16),'16±0.1',(12,0))
  a.text(ox,oy+23,'A 上表面 Z16');a.text(ox,oy-24,'B 下表面 Z0')
 pages=[]
 # Page1 top face.
 f,a=sheet('上表面 A / 俯视图（由 +Z 看向 −Z）',1);ox,oy=35,110;a.add_patch(Rectangle((ox,oy),240,130,fill=False,lw=1));circles(a,ox,oy)
 dim(a,(ox,oy+130),(ox+240,oy+130),'240±0.2',(0,12));dim(a,(ox+240,oy),(ox+240,oy+130),'130±0.2',(12,0))
 for x0,x1 in ((0,85),(85,155),(155,240)):dim(a,(ox+x0,oy),(ox+x1,oy),str(x1-x0),(0,-12))
 for y0,y1 in ((0,20),(20,52),(52,84),(84,116),(116,130)):dim(a,(ox,oy+y0),(ox,oy+y1),str(y1-y0),(-14,0))
 a.text(307,239,'孔位表 / 加工坐标');a.text(307,232,'孔号       X       Y',fontsize=8)
 for i,(n,x,y) in enumerate(holes):a.text(307,225-i*7,f'H{n:02d}       {x:.0f}      {y:.0f}',fontsize=8)
 textlines(a,['8×Ø6.5 +0.2/0 通孔，贯穿16mm；本面不做沉孔、不攻丝。','虚线Ø18为底面B加工特征。全部孔位按右侧表，不按图上量取。','位置目标±0.15mm；外轮廓±0.2mm；底板成品厚16±0.1mm。','H01/H02/H05/H06默认使用；其余4孔为立柱后移备用。'])
 # Section marker at X85, through four holes.
 line(a,(ox+85,oy-2),(ox+85,oy+132),True);a.text(ox+78,oy+134,'A');a.text(ox+78,oy-5,'A');pages.append((f,'01_上表面'))
 f,a=sheet('下表面 B / 仰视图（由 −Z 看向 +Z）',2);ox,oy=35,110;a.add_patch(Rectangle((ox,oy),240,130,fill=False,lw=1));circles(a,ox,oy,True)
 dim(a,(ox,oy+130),(ox+240,oy+130),'240',(0,12));dim(a,(ox+240,oy),(ox+240,oy+130),'130',(12,0));a.annotate('X+',xy=(ox+160,oy+145),xytext=(ox+210,oy+145),arrowprops=dict(arrowstyle='->'),ha='center')
 textlines(a,['8×Ø18 +0.2/0 平底沉孔，自B面向上深9.5±0.1mm，和Ø6.5通孔同轴。','不是锥形沉头孔。沉孔支承面保持平整；内角R≤0.5且不得干涉Ø15垫片。','仰视图左右翻转，孔号随实体对应；加工孔位坐标统一以第1张俯视图为准。','最近沉孔到板边名义剩5mm；沉孔上方剩6.5mm；本图不认证其承载。'])
 textlines(a,['沉孔半径计算：','螺母：AF8 → 外接圆R=8/√3=4.62','螺母径向余量 ≥1.0','厚垫片：R7.5 + 余量1.5','工具：外径≤16 → R8 + 余量1','R=max(5.62,9,9)=9 → Ø18'],x=303,y=235,dy=8,size=8);pages.append((f,'02_下表面'))
 # Four side faces; side holes are hidden interior features only.
 profiles=[('前侧面 / Y=0，朝向桌内一侧',240,'X',False),('后侧面 / Y=130，靠桌边一侧',240,'X',True),('左侧面 / X=0',130,'Y',True),('右侧面 / X=240',130,'Y',False)]
 for num,(title,w,axis,mirror) in enumerate(profiles,3):
  f,a=sheet(title,num);ox=55 if w==240 else 95;oy=175;profile(a,ox,oy,w,axis,mirror)
  textlines(a,['此侧面不钻孔、不攻丝。虚线仅表示板内通孔与底面沉孔投影。','8个孔全部沿Z方向加工；孔位见第1张，深度见第2张和A—A剖面。','去毛刺，避免崩边及可见裂纹；保留保护膜加工。'],y=125,size=9)
  pages.append((f,f'{num:02d}_'+title.split(' /')[0]))
 # Page7 longitudinal section through X85. Scale2:1 coordinate drawing.
 f,a=sheet('A—A 剖面 / X=85，穿过 H01—H04',7,'2:1');ox,oy=55,175;s=2
 a.add_patch(Rectangle((ox,oy),130*s,16*s,facecolor='#edf1f3',edgecolor='k',hatch='///',lw=.8))
 for y in (20,52,84,116):
  a.add_patch(Rectangle((ox+(y-9)*s,oy),18*s,9.5*s,facecolor='white',edgecolor='k',lw=.8))
  a.add_patch(Rectangle((ox+(y-3.25)*s,oy+9.5*s),6.5*s,6.5*s,facecolor='white',edgecolor='k',lw=.8))
 dim(a,(ox,oy),(ox+260,oy),'130',(0,-18));dim(a,(ox+260,oy),(ox+260,oy+32),'16',(13,0))
 dim(a,(ox+38,oy),(ox+38,oy+19),'9.5±0.1',(-55,0));dim(a,(ox+38,oy+19),(ox+38,oy+32),'剩6.5',(-68,0))
 textlines(a,['本剖面以毫米尺寸值标注，图形比例2:1。','沉孔深度由底面B量取：9.5；通孔贯穿：16；沉孔上方名义剩余材料6.5。','同轴度以加工孔轴一致为目标；所有8组孔的截面形式相同。'],y=125,size=9);pages.append((f,'07_AA剖面'))
 # Page8 fastener nominal stack, independent of capacity claims.
 f,a=sheet('连接剖面 / 默认一处M5连接（名义尺寸）',8,'3:1');ox,oy=110,120;s=3
 for x0,w,z0,h,col in [(-12,24,0,16,'#d6e8ef'),(-11,22,16,8,'#b8d5ca')]:a.add_patch(Rectangle((ox+x0*s,oy+z0*s),w*s,h*s,fc=col,ec='k',lw=.8))
 for x0,w,z0,h in [(-9,18,0,9.5),(-3.25,6.5,9.5,6.5),(-2.75,5.5,16,8)]:a.add_patch(Rectangle((ox+x0*s,oy+z0*s),w*s,h*s,fc='white',ec='k',lw=.6))
 for x0,w,z0,h in [(-5,10,24,1),(-5,10,25,1),(-7.5,15,7.5,2),(-4,8,2.8,4.7),(-2.5,5,1,25),(-4.25,8.5,26,5)]:a.add_patch(Rectangle((ox+x0*s,oy+z0*s),w*s,h*s,fc='#99a8b3',ec='#32434e',lw=.65))
 a.plot([ox-45,ox+45],[oy,oy],color='#a44',ls='--',lw=.6)
 textlines(a,['M5×25，8.8级，4颗','螺丝头下：每颗2片ISO7089 M5平垫','每片OD10 / ID5.3 / 厚1.0','立柱法兰：原打印件，名义厚8','底板：成品厚16','底面：每颗1片DIN7349 M5厚垫','OD15 / ID5.3 / 厚2.0','螺母：ISO4032:2023 M5 / 8级','AF8，包络按最大高4.7绘制','沉孔底部用8mm套筒；工具外径≤16'],x=190,y=235,dy=9,size=9)
 textlines(a,['名义叠层：螺丝端高于底板底面1.0mm；螺母底面高于底板底面2.8mm；螺丝伸过螺母1.8mm。','尺寸检验：先量成品板厚、法兰厚、垫片厚及螺丝长度，装配后端部不得凸出底面，并保持完整啮合。','以上为名义几何；加工和打印公差不能只看标称值。钢螺丝静力计算不等于PMMA板体或法兰承载合格。'],y=90,size=8.5)
 pages.append((f,'08_连接剖面'))
 if perspective.exists():
  f,a=sheet('透明透视示意 / 通孔与平底沉孔分色',9,'不按比例')
  image=plt.imread(perspective);height=202;width=height*image.shape[1]/image.shape[0]
  if width>376:width=376;height=width*image.shape[0]/image.shape[1]
  left=(420-width)/2;bottom=55+(202-height)/2;a.imshow(image,extent=(left,left+width,bottom,bottom+height),aspect='equal',zorder=2)
  a.text(18,45,'蓝色：8×Ø6.5通孔，贯穿16；橙色：8×Ø18平底沉孔，自底面深9.5。颜色仅作孔型说明。',fontsize=8)
  pages.append((f,'09_透明孔型透视'))
 with PdfPages(folder/'底板_六面与剖面_A3.pdf') as pdf:
  for f,name in pages:
   pdf.savefig(f);f.savefig(folder/(name+'.pdf'));f.savefig(folder/(name+'.png'),dpi=120);plt.close(f)
 # Geometry coordinates for machine/shop, without assembly translation.
 import csv
 with (folder/'孔位表.csv').open('w',encoding='utf-8-sig',newline='') as file:
  w=csv.writer(file);w.writerow(['孔号','X_mm','Y_mm','Z方向通孔','通孔深_mm','底面沉孔','沉孔深_mm','默认使用'])
  for n,x,y in holes:w.writerow([f'H{n:02d}',x,y,'Ø6.5',16,'Ø18平底',9.5,'是' if y in (84,116) else '后移备用'])
 # CAD/DXF machining coordinates match the dimensioned face views.
 import ezdxf
 d=ezdxf.new('R2010');d.units=ezdxf.units.MM;ms=d.modelspace()
 for name,color in [('OUTLINE',7),('THROUGH_D6_5',3),('BOTTOM_COUNTERBORE_D18_DEPTH9_5',1),('NOTES',5)]:d.layers.new(name,dxfattribs={'color':color})
 ms.add_lwpolyline([(0,0),(240,0),(240,130),(0,130)],close=True,dxfattribs={'layer':'OUTLINE'})
 for number,x,y in holes:
  ms.add_circle((x,y),3.25,dxfattribs={'layer':'THROUGH_D6_5'});ms.add_circle((x,y),9,dxfattribs={'layer':'BOTTOM_COUNTERBORE_D18_DEPTH9_5'})
 ms.add_text('PMMA CAST; FINISHED THICKNESS16; MM; SEE PDF FOR DATUM/TOLERANCES',dxfattribs={'height':3,'insert':(0,144),'layer':'NOTES'})
 ms.add_text('RED CIRCLES: BOTTOM FLAT COUNTERBORES DEPTH9.5; NOT THROUGH CUTS',dxfattribs={'height':3,'insert':(0,137),'layer':'NOTES'})
 d.saveas(p/'machining/base_acrylic_16.dxf')
 print(str(total)+'-sheet A3 paper drawing ready',folder,flush=True)
