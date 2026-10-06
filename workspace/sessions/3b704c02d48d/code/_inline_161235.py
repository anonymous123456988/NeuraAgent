p=r"C:\Users\Anony\Videos\Captures\NeuraAgent-完整项目 (1)\agent\tools\app_control.py"
lines=open(p,encoding="utf-8").read().splitlines()
print("total",len(lines))
for i in range(662,len(lines)):
    print(i+1, lines[i])
