"""gta6-twitch-ccu-forecast-01 entry: weighted empirical-quantile forecaster.

Reads each <id>.in case, then for every forecast hour h in 2..24 emits five
quantiles (5/25/50/75/95%) of that hour's Twitch viewer count for the
Grand Theft Auto VI category.

Method (deterministic, stdlib only, no network, no RNG):
  - The case ships `comparables`: past big-launch Twitch categories, each with a
    full release-day hourly viewer curve. For each comparable we form the ratio
    r_c(h) = viewers_c(h) / viewers_c(1) (per-unit of its own hour-1 print), so
    curves of very different scale become comparable.
  - For a target hour h we build a weighted pool of ratios. Each comparable's
    weight is the product of two Gaussian kernels:
      * magnitude kernel: how close the comparable's hour-1 print is to this
        case's hour-1 print, in log space, bandwidth MAG_BW = 1.0;
      * hour kernel: how close the comparable's hour hh is to the target hour h,
        bandwidth HOUR_BW = 3.0 hours, which smooths the ratio surface across
        neighbouring hours and denoises single-hour spikes.
  - The five quantiles are the weighted quantiles of that pool, each multiplied
    by this case's hour-1 print. For h = 24 (no comparable has that hour) the
    hour kernel is centred on h = 23, the nearest observed hour.
  - Every output value is clamped to a small positive floor so logs stay finite.

Scored by mean pinball loss on the log scale (lower is better).
"""

import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
MAG_BW = 1.0    # log-space bandwidth on hour-1 magnitude
HOUR_BW = 3.0   # hour-space bandwidth on target hour
VIEWER_FLOOR = 1e-6


def weighted_quantile(pool, tau):
    """tau-quantile of [(weight, value)], weighted, pool sorted by value."""
    target = tau * sum(w for w, _ in pool)
    acc = 0.0
    for w, v in pool:
        acc += w
        if acc >= target:
            return v
    return pool[-1][1]


def forecast_hour(p1, target_hour, comparables):
    """Five quantiles for `target_hour`, from weighted comparable ratios."""
    pool = []
    for comp in comparables:
        base = comp["h1"]
        if base <= 0:
            continue
        mag_d = math.log(max(1.0, base)) - math.log(max(1.0, p1))
        mag_w = math.exp(-0.5 * (mag_d / MAG_BW) ** 2)
        # h = 24 has no observed comparable hour; centre on 23.
        centre = min(target_hour, 23)
        for hh in range(2, 24):
            v = comp["curve"].get(hh)
            if not v or v <= 0:
                continue
            hour_d = hh - centre
            hour_w = math.exp(-0.5 * (hour_d / HOUR_BW) ** 2)
            pool.append((mag_w * hour_w, v / base))
    if not pool:
        return [p1] * len(LEVELS)
    pool.sort(key=lambda x: x[1])
    out = []
    for tau in LEVELS:
        q = p1 * weighted_quantile(pool, tau)
        out.append(max(VIEWER_FLOOR, q))
    return out


def forecast_case(case, name):
    if list(case["levels"]) != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1.0, float(first["viewers"]))

    comparables = []
    for comp in case.get("comparables") or []:
        curve = {}
        day = (comp.get("day_start") or "")[:10]
        if not day:
            continue
        for pt in comp.get("hourly") or []:
            at = pt.get("from") or ""
            if at[:10] == day:
                hour = int(at[11:13])
                curve[hour] = pt.get("viewers")
        # A comparable is usable only if its own hour-1 print is present and positive.
        h1 = curve.get(1)
        if not h1 or h1 <= 0:
            continue
        comparables.append({"h1": h1, "curve": curve})

    hours = []
    for row in case["forecast"]:
        h = int(row["hour"])
        hours.append({"hour": h, "q": forecast_hour(p1, h, comparables)})
    return {"hours": hours}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()