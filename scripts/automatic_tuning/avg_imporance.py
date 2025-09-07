#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path

def mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float)) and math.isfinite(x)]
    return sum(xs) / len(xs) if xs else float("nan")

def main(json_path):
    json_path = Path(json_path)
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise TypeError("Top-level JSON must be an object mapping names to lists of numbers.")

    averages = {k: mean(v) for k, v in data.items()}

    # Pretty print
    width = max(len(k) for k in averages)
    for k, v in sorted(averages.items(), key=lambda item: item[1], reverse=True):
        print(f"{k:<{width}} : {v:.10f}")

if __name__ == "__main__":
    # Default file name if not provided
    path = sys.argv[1] if len(sys.argv) > 1 else "/home/arijan/Documents/Diplomski_rad/best_params_no_trans/hyperparams_arrays.json"
    main(path)
