"""Add engineering legends to the actual Cycles renders; no image synthesis."""
from pathlib import Path
import json,sys
from PIL import Image,ImageDraw,ImageFont
root=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path(__file__).resolve().parent;r=int(sys.argv[1]);src=root/f'round{r}';dst=src/'composed';dst.mkdir(exist_ok=True)
font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
def F(n):return ImageFont.truetype(font,n)
def line(draw,xy,text,size=32,color='#45616b'):draw.text(xy,text,font=F(size),fill=color)
for mode in ('overview','mounted','acrylic'):
 if mode=='acrylic':
  im=Image.new('RGB',(2400,1900),'#fffef8');d=ImageDraw.Draw(im);line(d,(130,65),'底板 · 透明孔型透视',58,'#163b48');line(d,(130,150),'240 × 130 × 16 mm   /   高亮色仅用于区分孔型',31)
  photo=Image.open(src/(mode+'.png')).convert('RGB');factor=min(2200/photo.width,1420/photo.height);photo=photo.resize((round(photo.width*factor),round(photo.height*factor)),Image.Resampling.LANCZOS);im.paste(photo,((2400-photo.width)//2,210))
  d=ImageDraw.Draw(im);d.ellipse((150,1690,194,1734),fill='#258ec7');line(d,(225,1676),'8 × Ø6.5 通孔',42,'#163b48');line(d,(225,1740),'贯穿 16 mm',32)
  d.ellipse((1190,1690,1234,1734),fill='#ea9041');line(d,(1265,1676),'8 × Ø18 平底沉孔',42,'#163b48');line(d,(1265,1740),'自底面向上深 9.5 mm',32)
  line(d,(130,1840),'加工位置、孔径和深度以尺寸图及 STEP 为准。',25)
 else:
  im=Image.new('RGB',(2200,2500),'#fffef8');d=ImageDraw.Draw(im)
  line(d,(130,60),'装配总览' if mode=='overview' else '手柄安装效果',62,'#163b48')
  line(d,(130,150),'打印部件分色 · 购买部件统一灰色' if mode=='overview' else '16 mm 亚克力底板 · 保留原装配高度',32)
  photo=Image.open(src/(mode+'.png')).convert('RGB').resize((2020,2020),Image.Resampling.LANCZOS);im.paste(photo,(90,225));d=ImageDraw.Draw(im)
  if mode=='overview':
   entries=[('立柱底座','#329d94'),('套筒与耳板','#588ac5'),('托架','#dba165'),('上夹爪滑块','#d67e79'),('固定齿盘','#9a80b5'),('转动齿盘','#d9bd5f'),('购买部件','#b7bdc4')]
   for i,(title,col) in enumerate(entries):
    x=130+(i%4)*515;y=2280+(i//4)*88;d.rounded_rectangle((x,y+6,x+36,y+42),radius=5,fill=col);line(d,(x+55,y),title,31,'#304d58')
  else:
   line(d,(130,2300),'Blender / Cycles · 原手柄材质与贴图',32,'#304d58')
   line(d,(130,2372),'Controller: BatonyRobson · CC BY 4.0   |   Boiler Room: Poly Haven · CC0',23)
 im.save(dst/(mode+'.png'))
print('Composed review round',r)
