import sys,types,os,importlib.util
fake=types.ModuleType("python_mpv_jsonipc")
class F:
    def __init__(s,*a,**k): s._p={"idle_active":True,"time_pos":42,"duration":215,"volume":80,"audio_bitrate":126000}
    def command(s,*a,**k):pass
    def loadfile(s,*a,**k):pass
    def audio_add(s,*a,**k):pass
    def terminate(s):pass
    def __getattr__(s,n): return s.__dict__.get("_p",{}).get(n)
    def __setattr__(s,n,v):
        if n=="_p": object.__setattr__(s,n,v)
        else: s._p[n]=v
fake.MPV=F;fake.MPVError=Exception;sys.modules["python_mpv_jsonipc"]=fake
import shutil;shutil.which=lambda x:"/usr/bin/mpv"
here=os.path.dirname(os.path.abspath(__file__))
spec=importlib.util.spec_from_file_location("wk",os.path.join(here,os.environ.get("WK","walkman.py")));wk=importlib.util.module_from_spec(spec);spec.loader.exec_module(wk)
wk.main()
