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

def draw_x(d,x,y,scale=1,pose="idle",angry=False):
    lw=max(3,int(5*scale)); head=17*scale
    d.ellipse((x-head,y-head,x+head,y+head),fill=BG,outline=INK,width=lw)
    sh=(x,y+20*scale); hip=(x,y+57*scale)
    d.line((sh[0],sh[1],hip[0],hip[1]),fill=INK,width=lw)
    poses={"idle":((-30,32),(30,32),(-25,90),(25,90)),"jump":((-48,2),(48,0),(-45,92),(45,92)),"grab":((-48,22),(58,18),(-20,92),(20,92)),"run":((-45,20),(42,48),(-55,88),(58,66))}
    a1,a2,l1,l2=poses.get(pose,poses["idle"])
    for a,b in ((a1,sh),(a2,sh)) : d.line((b[0],b[1],x+a[0]*scale,y+a[1]*scale),fill=INK,width=lw)
    for a,b in ((l1,hip),(l2,hip)) : d.line((b[0],b[1],x+a[0]*scale,y+a[1]*scale),fill=INK,width=lw)
    ey=y-2*scale
    d.ellipse((x-9*scale,ey-2*scale,x-3*scale,ey+4*scale),fill=INK); d.ellipse((x+3*scale,ey-2*scale,x+9*scale,ey+4*scale),fill=INK)
    if angry:
        d.line((x-11*scale,ey-10*scale,x-3*scale,ey-6*scale),fill=INK,width=lw); d.line((x+3*scale,ey-6*scale,x+11*scale,ey-10*scale),fill=INK,width=lw)
        d.line((x-7*scale,ey+12*scale,x+8*scale,ey+12*scale),fill=INK,width=max(2,lw-1))
def cursor(d,x,y,kind="arrow"):
    if kind=="arrow":
        pts=[(x,y),(x+18,y+31),(x+9,y+27),(x+6,y+40),(x-1,y+36),(x+2,y+26),(x-7,y+30)]; d.polygon(pts,fill=INK)
    elif kind=="hand":
        d.ellipse((x-11,y-3,x+11,y+19),fill=BG,outline=INK,width=4)
        for k in (-8,-2,4,10): d.line((x+k,y+2,x+k,y-15),fill=INK,width=4)
    else:
        d.polygon([(x,y),(x+31,y-18),(x+39,y-10),(x+8,y+9)],fill=INK); d.polygon([(x,y),(x+8,y+9),(x-9,y+15)],fill=INK)
def saw(d,x,y,phase=0):
    # Cartoon prop: wooden handle + toothed blade, purely slapstick.
    d.line((x,y,x+58,y-22),fill=INK,width=7)
    d.line((x+38,y-15,x+73,y-28),fill=INK,width=5)
    for k in range(6):
        q=x+42+k*6
        d.line((q,y-17-(k%2)*3,q+5,y-25-(k%2)*3),fill=INK,width=3)

def render(t,rows):
    im=Image.new("RGB",(W,H),BG); d=ImageDraw.Draw(im)
    total=sum(len(x) for x in rows); end=min(18,3+total/55)
    if t<2.8: draw_x(d,125+4*math.sin(t*5),H-105,1.08,"idle"); return im
    if t<end:
        chars=int((t-2.8)*55); shown=[]; rem=chars
        for r in rows:
            n=min(len(r),max(0,rem)); rem=max(0,rem-len(r)); shown.append(r[:n])
        visible=[x for x in shown if x][-12:]; y=28; last=None
        for s in visible:
            clean=s.lstrip("# "); f=TITLE if s.startswith("# ") else H2 if s.startswith("## ") else H3 if s.startswith("### ") else BODY
            d.text((50,y),clean,font=f,fill=INK); b=d.textbbox((50,y),clean,font=f); last=(b[2]+5,y+2); y+=43 if f==TITLE else 34 if f==H2 else 29 if f==H3 else 24
        if last: cursor(d,*last)
        p=(t-2.8)/(end-2.8)
        if p<.18: draw_x(d,135,H-105,1,"idle")
        elif p<.62:
            q=(p-.18)/.44; draw_x(d,145+260*q,H-105-245*math.sin(math.pi*q),1,"jump")
        else:
            q=(p-.62)/.38; draw_x(d,405+210*q,H-105-185*math.sin(math.pi*q),1,"grab")
        return im
    chaos=t-end; y=28
    for i,s in enumerate(rows[:16]):
        clean=s.lstrip("# "); f=TITLE if s.startswith("# ") else H2 if s.startswith("## ") else H3 if s.startswith("### ") else BODY
        x=50; yy=y
        if i in (5,9): x+=70*math.sin(chaos*2+i); yy+=35*math.sin(chaos*1.5+i)
        d.text((x,yy),clean,font=f,fill=INK); y+=43 if f==TITLE else 34 if f==H2 else 29 if f==H3 else 24
    if chaos<2.5:
        cursor(d,650,110); draw_x(d,650,155,.9,"grab",True); d.rectangle((585,75,715,275),outline=INK,width=4)
    elif chaos<5:
        d.rectangle((585,75,715,275),outline=INK,width=4); draw_x(d,650+7*math.sin(chaos*15),155,.9,"grab",True); cursor(d,700,110,"hand")
    else:
        draw_x(d,650+min(170,(chaos-5)*75),155-35*math.sin((chaos-5)*3),.95,"run",True); cursor(d,740+35*math.sin(chaos*2.2),330+70*math.sin(chaos*1.4),"hand")
        bx=390+130*math.sin(chaos*1.3); by=390+30*math.sin(chaos*2.1); d.rounded_rectangle((bx,by,bx+260,by+45),radius=7,outline=INK,width=3); d.text((bx+12,by+11),"Selected Work",font=H3,fill=INK)
    return im
def main():
    OUT.parent.mkdir(parents=True,exist_ok=True); rows=read_text(); end=min(18,3+sum(len(x) for x in rows)/55); duration=min(28,end+10)
    frames=[render(i/FPS,rows).convert("P",palette=Image.Palette.ADAPTIVE) for i in range(int(duration*FPS))]
    frames[0].save(OUT,save_all=True,append_images=frames[1:],duration=int(1000/FPS),loop=0,optimize=True,disposal=2)
    print("generated",OUT,len(frames),"frames")

if __name__=="__main__": main()
