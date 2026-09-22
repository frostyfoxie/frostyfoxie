from pathlib import Path
import math, os
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'animated-profile.gif'
README = ROOT / 'README.md'
W, H, FPS = 900, 760, 8
BG = (250,250,248); INK=(25,25,28); MUTED=(110,110,118); ACCENT=(60,95,180)

def F(size, bold=False):
    p = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    return ImageFont.truetype(p, size)

TITLE=F(38,True); H2=F(29,True); H3=F(23,True); BODY=F(20); SMALL=F(16)

def read_text():
    rows=[]
    for line in README.read_text(encoding='utf8').splitlines():
        if line.startswith('![Animated profile]') or line.strip() in ('','---'): continue
        s=line.replace('**','').replace('__','').replace('`','')
        if '](' in s: s=s.replace('](', ' - ').replace(']','').replace('[','')
        rows.append(s.strip())
    return rows

def wrap(s,n=55):
    words=s.split(); out=[]; cur=''
    for w in words:
        t=(cur+' '+w).strip()
        if len(t)>n and cur: out.append(cur); cur=w
        else: cur=t
    if cur: out.append(cur)
    return out

def draw_x(d,x,y,scale=1,pose='idle',angry=False):
    lw=max(2,int(4*scale)); r=13*scale
    d.ellipse((x-r,y-r,x+r,y+r),outline=INK,width=lw)
    sh=(x,y+17*scale); hip=(x,y+52*scale)
    if pose=='jump': arms=((x-30*scale,y+4*scale),(x+30*scale,y+4*scale)); legs=((x-24*scale,y+78*scale),(x+24*scale,y+78*scale))
    elif pose=='grab': arms=((x-35*scale,y+12*scale),(x+35*scale,y+12*scale)); legs=((x-18*scale,y+78*scale),(x+18*scale,y+78*scale))
    else: arms=((x-28*scale,y+35*scale),(x+28*scale,y+35*scale)); legs=((x-25*scale,y+82*scale),(x+25*scale,y+82*scale))
    d.line((*sh,*hip),fill=INK,width=lw)
    d.line((*sh,*arms[0]),fill=INK,width=lw); d.line((*sh,*arms[1]),fill=INK,width=lw)
    d.line((*hip,*legs[0]),fill=INK,width=lw); d.line((*hip,*legs[1]),fill=INK,width=lw)
    ey=y-3*scale
    d.ellipse((x-6*scale,ey-2*scale,x-2*scale,ey+2*scale),fill=INK); d.ellipse((x+2*scale,ey-2*scale,x+6*scale,ey+2*scale),fill=INK)
    if angry: d.line((x-9*scale,ey-7*scale,x-2*scale,ey-4*scale),fill=INK,width=lw); d.line((x+2*scale,ey-4*scale,x+9*scale,ey-7*scale),fill=INK,width=lw)

def cursor(d,x,y,held=False):
    d.line((x,y,x+13,y+18),fill=INK,width=3); d.line((x+13,y+18,x+8,y+16),fill=INK,width=3); d.line((x+8,y+16,x+8,y+22),fill=INK,width=3)
    if held: d.ellipse((x-5,y-5,x+5,y+5),outline=ACCENT,width=2)

def render(t,rows):
    im=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(im); d.line((25,H-42,W-25,H-42),fill=(210,210,210),width=2)
    if t<3:
        draw_x(d,130+10*math.sin(t*1.4),H-105); d.text((W-235,H-75),'…',font=H2,fill=MUTED); return im
    total=sum(len(x) for x in rows); end=min(25,3+total/38)
    if t<end:
        chars=int((t-3)*38); shown=[]; rem=chars
        for r in rows:
            n=min(len(r),max(0,rem)); rem=max(0,rem-len(r)); shown.append(r[:n])
        visible=[x for x in shown if x]; visible=visible[-9:]
        y=35
        for s in visible:
            f=TITLE if s.startswith('# ') else H2 if s.startswith('## ') else H3 if s.startswith('### ') else BODY
            d.text((54,y),s.lstrip('# '),font=f,fill=INK); b=d.textbbox((54,y),s.lstrip('# '),font=f); cursor(d,b[2]+3,y+2); y+=42 if f!=BODY else 30
        phase=(t-3)%3
        if phase<1.2: draw_x(d,150+50*phase,H-110-180*math.sin(phase*math.pi/1.2),1,'jump')
        else: draw_x(d,150,H-105)
        return im
    chaos=t-end; y=30
    for i,s in enumerate(rows[:16]):
        dx=70*math.sin(chaos*2) if i==4 else (-55*math.sin(chaos*1.7) if i==6 else 0)
        d.text((54+dx,y),s.lstrip('# '),font=H3 if s.startswith('#') else BODY,fill=INK); y+=43
    if chaos<2.5:
        cursor(d,640,115,True); draw_x(d,640,145,.9,'grab',True); d.rectangle((585,108,710,245),outline=ACCENT,width=3)
    elif chaos<5:
        d.rectangle((555,95,720,255),outline=ACCENT,width=4); draw_x(d,638+8*math.sin(chaos*8),160,.9,'idle',True)
    else:
        draw_x(d,640+min(170,(chaos-5)*80),160-35*math.sin((chaos-5)*3),.9,'jump',True)
        bx=430+100*math.sin(chaos*1.4); by=380+30*math.sin(chaos*2.2)
        d.rounded_rectangle((bx,by,bx+230,by+52),radius=8,outline=INK,width=3); d.text((bx+15,by+12),'Selected Work',font=H3,fill=INK)
        d.text((590,285),'SYSTEM: PLEASE STOP.',font=SMALL,fill=MUTED)
    return im

def main():
    OUT.parent.mkdir(parents=True,exist_ok=True); rows=read_text(); end=min(25,3+sum(len(x) for x in rows)/38); duration=min(34,end+9)
    frames=[render(i/FPS,rows).convert('P',palette=Image.Palette.ADAPTIVE) for i in range(int(duration*FPS))]
    frames[0].save(OUT,save_all=True,append_images=frames[1:],duration=int(1000/FPS),loop=0,optimize=True,disposal=2)
    print('generated',OUT,len(frames),'frames')

if __name__=='__main__': main()