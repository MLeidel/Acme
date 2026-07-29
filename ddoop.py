# ddoop.py
# de-dupe a text file of strings, 1 string per line

import sys

if len(sys.argv) < 2:
    print("specify file to dedupe")
    sys.exit()

file = sys.argv[1]

# Read lines, remove duplicates preserving order, and write back
with open(file, "r") as f:
    lines = f.readlines()

unique_lines = list(dict.fromkeys(lines))

with open(file, "w") as f:
    f.writelines(unique_lines)

