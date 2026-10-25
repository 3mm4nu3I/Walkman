import sys, time, math
exec(open('p1_engine.py').read()); exec(open('p2_models.py').read())
W,H=int(sys.argv[2]) if len(sys.argv)>2 else 76, int(sys.argv[3]) if len(sys.argv)>3 else 30
which=sys.argv[1].split(',') if len(sys.argv)>1 else [d[0] for d in MODEL_DEFS]
angs=[float(a) for a in (sys.argv[4].split(',') if len(sys.argv)>4 else ['0.6'])]
for d in MODEL_DEFS:
    if d[0] not in which and which!=['all']: continue
    t=time.time(); idx=[x[0] for x in MODEL_DEFS].index(d[0]); name,specs,tilt,speed,mesh,roll=get_model(idx); t1=time.time()
    for a in angs:
        t2=time.time(); g=render3d(mesh,a,tilt,W,H,roll); t3=time.time()
        print("### %s  verts=%d faces=%d build=%.0fms render=%.0fms ay=%.2f"%(d[1],len(mesh.v),len(mesh.f),(t1-t)*1000,(t3-t2)*1000,a))
        for row in g: print("".join(c[0] if c else " " for c in row).rstrip())
