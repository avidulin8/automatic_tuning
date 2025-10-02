from pathlib import Path
import re
from collections import defaultdict
import math
import json

# === CONFIG ===
FOLDER = Path("/home/arijan/Documents/Diplomski_rad/best_params_no_trans")   # <-- change this
FILE_GLOB = "*.txt"                     # adjust if needed

# If you know the full set of hyperparameters, list them here to enforce presence/order
#translation_weight REMOVED
HYPERPARAMS = [
    "low_resolution","max_range","low_res_min_num_points",
    "high_resolution","high_res_min_num_points","rotation_weight","low_res_max_range",
    "num_range_data","high_res_max_length","voxel_filter_size","high_res_max_range",
    "low_res_max_length"
]

# Natural sort for filenames like scene1, scene2, ..., scene16
def natural_key(s):
    import re
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(s))]

# Parse "name: value" lines
line_re = re.compile(r"^\s*([A-Za-z0-9_]+)\s*:\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*$")

files = sorted(FOLDER.glob(FILE_GLOB), key=natural_key)
if len(files) != 16:
    print(f"Warning: expected 16 files, found {len(files)}")

# Collect per-parameter arrays
per_param = {p: [] for p in HYPERPARAMS}
missing_report = defaultdict(list)

for f in files:
    with f.open("r", encoding="utf-8") as fh:
        found = {}
        for line in fh:
            m = line_re.match(line)
            if m:
                name, val = m.group(1), float(m.group(2))
                found[name] = val

    # Append in fixed HYPERPARAM order; use NaN if missing
    for p in HYPERPARAMS:
        if p in found:
            per_param[p].append(found[p])
        else:
            per_param[p].append(math.nan)
            missing_report[p].append(f.name)

# per_param now has 13 keys, each a list of 16 values
# Example access:
#   per_param["translation_weight"]  -> [v_scene1, v_scene2, ..., v_scene16]

# Optional: print a brief summary
for p in HYPERPARAMS:
    vals = per_param[p]
    n_missing = sum(math.isnan(v) for v in vals)
    print(f"{p}: {len(vals)} values (missing: {n_missing})")

# Optional: save to JSON for reuse
output_json = FOLDER / "hyperparams_arrays.json"
with output_json.open("w", encoding="utf-8") as out:
    json.dump(per_param, out, indent=2)
print(f"Saved arrays to: {output_json}")
