import hashlib
import os

release_dir = r"D:\JARVIS-AI\release"
files = [
    "JARVIS_Mark_LVI_Setup.exe",
    "JARVIS_Mark_LVI_Windows_x64_Portable.zip",
    "SHA256_MANIFEST.txt",
]

for f in files:
    fp = os.path.join(release_dir, f)
    if os.path.exists(fp):
        size = os.path.getsize(fp)
        with open(fp, "rb") as fh:
            h = hashlib.sha256(fh.read()).hexdigest()
        print(f"FILE: {f}")
        print(f"SIZE: {size:,} bytes")
        print(f"SHA256: {h}\n")
    else:
        print(f"FILE NOT FOUND: {f}\n")
