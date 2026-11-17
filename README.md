# gta6-twitch-ccu-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/belaayi89-byte/gta6-twitch-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/belaayi89-byte/gta6-twitch-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Weighted empirical-quantile forecaster for GTA VI's launch-day Twitch viewers,
built by an AI agent for make.fun's
[`gta6-twitch-ccu-forecast-01`](https://make.fun/bounty/gta6-twitch-ccu-forecast-01)
bounty.

## Method

Reads a case (everything recorded up to the end of the release day's first
hour, that hour's viewer count included), then emits five quantiles
(5/25/50/75/95%) for each of hours 2 to 24.

The case ships `comparables`: past big launches' Twitch categories, each with a
full release-day hourly curve. Per comparable we use the ratio
`r(h) = viewers(h) / viewers(1)`, so curves of very different scale align. For
a target hour the five quantiles are weighted quantiles of that ratio pool,
multiplied by this case's hour-1 print. Each comparable's weight is a product
of two Gaussian kernels:

- **magnitude** — how close its hour-1 print is to this case's, in log space
  (bandwidth 1.0);
- **hour** — how close an observed hour is to the target hour (bandwidth 3.0),
  which smooths the ratio surface and denoises single-hour spikes.

Hour 24 has no observed comparable hour, so its kernel centres on hour 23.
Every value is clamped to a positive floor. Deterministic: stdlib only, no
network, no RNG, no wall clock — two runs on the same input write identical
bytes.

## Run

The grader runs `python3 -P -s /bot/main.py` per case. Locally:

```sh
mkdir -p out
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## License

MIT
