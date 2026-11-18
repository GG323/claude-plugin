import sys

with open(sys.argv[1], encoding="utf-8") as f:
    print(len(f.read().split()))
