#!/usr/bin/env python3
"""Build walkman_upgrade_1_6_1.py: embeds the 1.6.1 player + art and the known-good 1.6 and 1.5 builds
(zlib+base64, each with a SHA-256 the installer verifies before it touches anything)."""
import base64, hashlib, os, py_compile, zlib
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
def pack(rel):
    data = open(os.path.join(ROOT, rel), "rb").read()
    return hashlib.sha256(data).hexdigest(), base64.b64encode(zlib.compress(data, 9)).decode()
SRC = {"MAIN": "walkman_build_v14_1.6.1.py", "ART": "walkman_art.py",
       "V15": "releases/1.5/walkman_build_v13_1.5.py",
       "V16": "releases/1.6/walkman_build_v14_1.6.py", "V16A": "releases/1.6/walkman_art_1.6.py"}
t = open(os.path.join(HERE, "installer_template.py")).read()
for k, rel in SRC.items():
    sha, b64 = pack(rel)
    for tag, val in (("@@SHA_%s@@" % k, sha), ("@@B64_%s@@" % k, b64)):
        assert t.count(tag) == 1, tag
        t = t.replace(tag, val)
out = os.path.join(ROOT, "walkman_upgrade_1_6_1.py")
open(out, "w").write(t)
py_compile.compile(out, doraise=True)
print("wrote", out, hashlib.sha256(t.encode()).hexdigest()[:16])
