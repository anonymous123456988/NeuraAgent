import os
base = r"C:\Users\Anony\AppData\Local"
targets = []
for d in os.listdir(base):
    low = d.lower()
    if low.startswith('n') or 'mine' in low or 'ntm' in low:
        targets.append(d)
print("候选目录:", targets)
for t in targets:
    p = os.path.join(base, t)
    print("=" * 60)
    print("路径:", p, "是目录:", os.path.isdir(p))
    if os.path.isdir(p):
        for root, dirs, files in os.walk(p):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    sz = os.path.getsize(fp)
                except Exception:
                    sz = -1
                print("  ", fp, sz)
