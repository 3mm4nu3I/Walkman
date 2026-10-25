import os,pty,sys,select,time,pyte,signal,tempfile
rows,cols=42,120
home=tempfile.mkdtemp()
screen=pyte.Screen(cols,rows); stream=pyte.ByteStream(screen)
env=dict(os.environ,TERM="xterm-256color",YOUTUBE_API_KEY="TESTKEY",LINES=str(rows),COLUMNS=str(cols),HOME=home,**{k:v for k,v in [x.split("=") for x in sys.argv[1:]]})
pid,fd=pty.fork()
if pid==0:
    import fcntl,termios,struct
    fcntl.ioctl(0,termios.TIOCSWINSZ,struct.pack("HHHH",rows,cols,0,0))
    os.execvpe(sys.executable,[sys.executable,os.path.join(os.path.dirname(os.path.abspath(__file__)),"_run_stub.py")],env)
def pump(t):
    end=time.time()+t
    while time.time()<end:
        r,_,_=select.select([fd],[],[],0.05)
        if r:
            try: d=os.read(fd,65536)
            except OSError: return
            if not d: return
            stream.feed(d)
def snap(): return "\n".join(l.rstrip() for l in screen.display)
pump(1.0); s1=snap(); pump(1.5); s2=snap()
print("--- t~1.0s"); print("\n".join(l for l in s1.split("\n") if l.strip())[:1800])
print("--- t~2.5s"); print("\n".join(l for l in s2.split("\n") if l.strip())[:1500])
os.write(fd,b"x"); pump(1.0); s3=snap()
print("--- after key: main screen?", "RED STAR" in s3 or "TRACK" in s3 or "[H]" in s3, "| traceback:", "Traceback" in s3)
print("flag file:", os.listdir(home))
pump(5.0); print("--- 2nd run flag respected; still alive screen traceback:", "Traceback" in snap())
try: os.kill(pid,signal.SIGKILL)
except Exception: pass
