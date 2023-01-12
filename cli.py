import sys
from interpreter import interpret

if len(sys.argv) != 2:
    print("use: `python3 cli.py sourcefile")
    exit(1)

with open(sys.argv[1]) as f:
    interpret(f.read(), opts={"debug": False})
