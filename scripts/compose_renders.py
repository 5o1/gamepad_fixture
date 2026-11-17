"""Add engineering legends to the actual Cycles renders; no image synthesis."""
from pathlib import Path
import json,sys
from PIL import Image,ImageDraw,ImageFont
import argparse
parser=argparse.ArgumentParser();parser.add_argument('round',type=int);parser.add_argument('input_dir',type=Path);parser.add_argument('--palette',type=Path,required=True);parser.add_argument('--only',choices=('overview','mounted','base'));args=parser.parse_args()
root=args.input_dir.resolve();r=args.round;src=root/f'round{r}';dst=src/'composed';dst.mkdir(exist_ok=True)
palette=json.loads(args.palette.read_text())
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def F(n):return ImageFont.truetype(font,n)
def line(draw,xy,text,size=32,color='#45616b'):draw.text(xy,text,font=F(size),fill=color)
for mode in ([args.only] if args.only else ('overview','mounted','base')):
 if mode=='base':
  im=Image.new('RGB',(2400,1900),'#fffef8');d=ImageDraw.Draw(im);line(d,(130,65),'Aluminum base · Wire thread inserts',58,'#163b48');line(d,(130,150),'240 × 130 × 10 mm   /   Opaque aluminum presentation',31)
  photo=Image.open(src/(mode+'.png')).convert('RGB');factor=min(2200/photo.width,1420/photo.height);photo=photo.resize((round(photo.width*factor),round(photo.height*factor)),Image.Resampling.LANCZOS);im.paste(photo,((2400-photo.width)//2,210))
  d=ImageDraw.Draw(im);d.ellipse((150,1690,194,1734),fill=palette['hole_annotations']['through']['hex']);line(d,(225,1676),'4 × active column mounts',42,'#163b48')
  d.ellipse((1190,1690,1234,1734),fill=palette['hole_annotations']['counterbore']['hex']);line(d,(1265,1676),'4 × spare rear-shift positions',42,'#163b48')
  line(d,(130,1750),'All 8: M5×0.8 wire thread insert, 1.5D tangless (7.5 mm), recess 0.4; drill Ø5.2, STI tap through',30)
  line(d,(130,1800),'Colors are annotations only, not paint or manufactured geometry.',25)
  line(d,(130,1850),'For machining locations, diameters and depths, refer to the drawings and STEP.',25)
 else:
  im=Image.new('RGB',(2200,2600 if mode=='mounted' else 2500),'#fffef8');d=ImageDraw.Draw(im)
  line(d,(130,60),'Assembly overview' if mode=='overview' else 'Controller mounted',62,'#163b48')
  line(d,(130,150),'Printed parts in distinct colors · Purchased parts in gray' if mode=='overview' else '10 mm aluminum base · Controller frame preserved',32)
  photo=Image.open(src/(mode+'.png')).convert('RGB').resize((2020,2020),Image.Resampling.LANCZOS);im.paste(photo,(90,225));d=ImageDraw.Draw(im)
  if mode in ('overview','mounted'):
   entries=[(c['name'],c['hex']) for c in palette['printed_parts'].values()]+[(palette['purchased_parts']['name'],palette['purchased_parts']['hex'])]
   for i,(title,col) in enumerate(entries):
    x=130+(i%4)*515;y=2280+(i//4)*88;d.rounded_rectangle((x,y+6,x+36,y+42),radius=5,fill=col);line(d,(x+55,y),title,31,'#304d58')
  if mode=='mounted':
   line(d,(130,2450),'Blender / Cycles · Original controller materials and textures',32,'#304d58')
   line(d,(130,2520),'Controller: BatonyRobson · CC BY 4.0   |   Boiler Room: Poly Haven · CC0',23)
 im.save(dst/(mode+'.png'))
print('Composed review round',r)
