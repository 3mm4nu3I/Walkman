import sys, types, time, os
# stub mpv so Player() works headlessly
fake = types.ModuleType("python_mpv_jsonipc")
class FakeMPV:
    def __init__(self,*a,**k): self._p={"idle_active":True,"pause":False,"time_pos":42,"duration":215,"volume":80,"mute":False,"audio_bitrate":131000}
    def command(self,*a,**k): pass
    def loadfile(self,*a,**k): pass
    def audio_add(self,*a,**k): pass
    def terminate(self): pass
    def __getattr__(self,n): return self.__dict__.get("_p",{}).get(n)
    def __setattr__(self,n,v):
        if n=="_p": object.__setattr__(self,n,v)
        else: self._p[n]=v
fake.MPV=FakeMPV; fake.MPVError=Exception
sys.modules["python_mpv_jsonipc"]=fake
import shutil; shutil.which=lambda x: "/usr/bin/mpv"
import importlib.util
spec=importlib.util.spec_from_file_location("wk", os.path.join(os.path.dirname(__file__),"walkman.py"))
wk=importlib.util.module_from_spec(spec); spec.loader.exec_module(wk)
import curses
SCENE=os.environ.get("SCENE","menu")
def body(scr):
    wk.curses.curs_set(0); wk.curses.noecho(); wk.setup_colors()
    p=wk.Player()
    if SCENE in ("menu","gallery","galinv","audio"):
        p.playlist=[("u","Katyusha - Red Army Choir (Official)")]; p.current_index=0
        p.status="Playing: Katyusha - Red Army Choir"
    if SCENE=="audio": p.audio_only=True
    scr.erase()
    if SCENE=="menu" or SCENE=="audio": wk.draw_page_1(scr,p,False,False,"",7)
    elif SCENE=="gallery": wk.draw_gallery(scr,p,0,0,False,False)   # piece 0
    elif SCENE=="galinv": wk.draw_gallery(scr,p,0,3,True,False)     # piece 3 inverted
    elif SCENE=="star": wk.draw_star_page(scr,p,10)
    elif SCENE.startswith("art_"):
        A=wk.ART; st=A.new_state(); page=SCENE[4:].split("@")[0]
        tk=int(SCENE.split("@")[1]) if "@" in SCENE else 40
        p.playlist=[("u","Katyusha - Red Army Choir (Official)")]; p.current_index=0
        if page=="main":
            wk.draw_page_1(scr,p,False,False,"",tk)
            A.draw_main_extras(scr,tk,st,20,wk.curses.COLS-21)
        elif page=="mainfy":
            st["fy"].trigger(); st["fy"].t0-=3.5
            wk.draw_page_1(scr,p,False,False,"",tk)
            A.draw_main_extras(scr,tk,st,20,wk.curses.COLS-21)
        else:
            if page=="hall": st["idx"]=int(os.environ.get("IDX","0")); st["auto"]=False; st["inv"]=os.environ.get("INV")=="1"
            if page=="fyodor": st["fy_idx"]=int(os.environ.get("IDX","0"))
            if page=="launch":
                st["lt0"]=time.time()-float(os.environ.get("LT","0")); st["lt_seen"]=time.time()
            A.draw(page,scr,p,tk,st,wk.draw_side_art)
    scr.refresh(); time.sleep(0.2)
curses.wrapper(body)
