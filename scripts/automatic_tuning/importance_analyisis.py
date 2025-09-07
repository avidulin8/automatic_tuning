from pathlib import Path
import re
from collections import defaultdict

# ==== CONFIG ====
FOLDER = Path("/home/arijan/Documents/Diplomski_rad/best_params")  # <-- change this
FILE_GLOB = "*.txt"                    # adjust if needed
TOP_N = 3
THRESHOLD = 0.15  # strictly greater than this

# Parse lines like: "translation_weight: 0.1713755757956611"
LINE_RE = re.compile(
    r"^\s*([A-Za-z0-9_]+)\s*:\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*$"
)

def natural_key(p):
    # Natural sort: scene1.txt < scene2.txt < ... < scene16.txt
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(p))]

files = sorted(FOLDER.glob(FILE_GLOB), key=natural_key)
if len(files) != 16:
    print(f"Warning: expected 16 files, found {len(files)}")

counts = defaultdict(int)            # hyperparam -> count of hits
seen_params = set()                  # all hyperparams encountered
hits_by_param = defaultdict(list)    # optional: where it hit (file, value)

for f in files:
    pairs = []
    with f.open("r", encoding="utf-8") as fh:
        for line in fh:
            m = LINE_RE.match(line)
            if m:
                name, val = m.group(1), float(m.group(2))
                pairs.append((name, val))
                seen_params.add(name)

    if not pairs:
        print(f"Warning: no 'name: value' lines in {f.name}")
        continue

    # Take top-N by value (robust even if file isn't perfectly sorted)
    top = sorted(pairs, key=lambda kv: kv[1], reverse=True)[:TOP_N]

    # Count only those strictly greater than threshold
    for name, val in top:
        if val > THRESHOLD:
            counts[name] += 1
            hits_by_param[name].append((f.name, val))

# Ensure zero entries are shown for all seen hyperparams
for name in seen_params:
    counts.setdefault(name, 0)

# Print summary sorted by count desc then name
print(f"Counts of appearances in top {TOP_N} with value > {THRESHOLD}")
for name, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
    print(f"{name}: {c}")

# Optional: set to True if you want to see which files each param hit
SHOW_DETAILS = False
if SHOW_DETAILS:
    for name in sorted(hits_by_param):
        print(f"\n{name} hits ({len(hits_by_param[name])}):")
        for fname, val in hits_by_param[name]:
            print(f"  {fname}: {val}")
