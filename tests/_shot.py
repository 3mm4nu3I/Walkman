import os,pty,sys,select,pyte,subprocess
from PIL import Image, ImageDraw, ImageFont
scene=sys.argv[1]; out=sys.argv[2]
rows,cols=42,120
screen=pyte.Screen(cols,rows); stream=pyte.ByteStream(screen)
env=dict(os.environ,TERM="xterm-256color",YOUTUBE_API_KEY="TESTKEY",LINES=str(rows),COLUMNS=str(cols),SCENE=scene)
pid,fd=pty.fork()
if pid==0:
    import fcntl,termios,struct
    fcntl.ioctl(0,termios.TIOCSWINSZ,struct.pack("HHHH",rows,cols,0,0))
    os.execvpe(sys.executable,[sys.executable,os.path.join(os.path.dirname(os.path.abspath(__file__)),"_harness.py")],env)
buf=b""
while True:
    r,_,_=select.select([fd],[],[],2.0)
    if not r: break
    try: d=os.read(fd,65536)
    except OSError: break
    if not d: break
    buf+=d
stream.feed(buf)
COL={"default":None,"black":(0,0,0),"red":(205,49,49),"green":(13,188,121),"brown":(229,229,16),"yellow":(229,229,16),"blue":(36,114,200),"magenta":(188,63,188),"cyan":(17,168,205),"white":(229,229,229)}
def col(c,default):
    if c=="default": return default
    if c in COL: return COL[c]
    try: return tuple(int(c[i:i+2],16) for i in (0,2,4))
    except Exception: return default
f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",15)
fb=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",15)
cw,ch=9,18
img=Image.new("RGB",(cols*cw,rows*ch),(0,0,0)); dr=ImageDraw.Draw(img)
for y in range(rows):
    for x in range(cols):
        c=screen.buffer[y][x]
        bg=col(c.bg,(0,0,0)); fg=col(c.fg,(200,200,200))
        if c.reverse: fg,bg=bg,fg
        if c.bold and c.fg in ("red","brown","yellow","green","cyan","blue","magenta","black"):
            fg=tuple(min(255,int(v*1.25)+30) for v in fg)
        if bg!=(0,0,0): dr.rectangle([x*cw,y*ch,x*cw+cw,y*ch+ch],fill=bg)
        if c.data.strip(): dr.text((x*cw,y*ch),c.data,font=fb if c.bold else f,fill=fg)
img.save(out)
