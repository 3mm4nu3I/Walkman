import os,pty,sys,select,time,pyte,signal
seq=sys.argv[1]            # e.g. "h|RIGHT|RIGHT|ESC|w|ESC"
rows,cols=42,120
screen=pyte.Screen(cols,rows); stream=pyte.ByteStream(screen)
env=dict(os.environ,TERM="xterm-256color",YOUTUBE_API_KEY="TESTKEY",LINES=str(rows),COLUMNS=str(cols))
pid,fd=pty.fork()
if pid==0:
    import fcntl,termios,struct
    fcntl.ioctl(0,termios.TIOCSWINSZ,struct.pack("HHHH",rows,cols,0,0))
    os.execvpe(sys.executable,[sys.executable,os.path.join(os.path.dirname(os.path.abspath(__file__)),"_run_stub.py")],env)
KEYS={"RIGHT":"\x1bOC","LEFT":"\x1bOD","UP":"\x1bOA","DOWN":"\x1bOB","ESC":"\x1b","TAB":"\t","ENTER":"\r","SPACE":" "}
def pump(t):
    end=time.time()+t; got=b""
    while time.time()<end:
        r,_,_=select.select([fd],[],[],0.05)
        if r:
            try: d=os.read(fd,65536)
            except OSError: return
            if not d: return
            stream.feed(d)
def snap(): return "\n".join(l.rstrip() for l in screen.display)
pump(1.5)
log=[]
for tok in seq.split("|"):
    os.write(fd,KEYS.get(tok,tok).encode()); pump(0.7 if tok!="ESC" else 0.9)
    s=snap(); title=s.split("\n")[1][19:100].strip(); status=[l for l in s.split("\n") if "Art error" in l or "Art disabled" in l or "Traceback" in l]
    log.append((tok,title,status))
for tok,title,status in log: print("%-6s -> %-70s %s"%(tok,title[:70],status))
print("FINAL SCREEN HAS TRACEBACK:", "Traceback" in snap())
try: os.kill(pid,signal.SIGKILL)
except Exception: pass
