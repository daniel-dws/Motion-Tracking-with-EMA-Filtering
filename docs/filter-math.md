# Filter math

## Measurement model

The camera samples a continuous-time position corrupted by noise:

```
x_m(t) = x_true(t) + n(t)
x_m[n] = x_m(n * Ts),   Ts = 1 / FPS
```

## Continuous first-order low-pass filter

```
tau * dy/dt + y(t) = x_m(t)        H(s) = 1 / (tau*s + 1)
```

Slow changes pass; fast changes (noise) are attenuated. The cutoff frequency is `f_c = 1 / (2*pi*tau)`.

## Discrete implementation: EMA

```
y[n] = alpha * x[n] + (1 - alpha) * y[n-1],    0 < alpha <= 1
```

Matching the EMA's per-sample decay `(1 - alpha)` to the continuous filter's `exp(-Ts / tau)` gives:

```
tau = -Ts / ln(1 - alpha)
```

| Run | fps | alpha | tau | f_c |
|---|---|---|---|---|
| V1 | 30 | 0.1 | 0.314 s | 0.51 Hz |
| V2 | 90 | 0.1 | 0.105 s | 1.51 Hz |

The same alpha at a higher frame rate is a shorter time constant, which is why V2 lags less in time even though alpha did not change.

## Lag

A low-pass filter delays its input by roughly one time constant, so in frames the lag is about `tau * FPS` (9-10 frames at alpha = 0.1, independent of fps). In pixels it is that many frames times the per-frame displacement of the object, which is why V1 (larger per-frame jumps) shows more pixel lag than V2.

## Metrics used in `analysis/analyze.py`

```
jitter = sqrt((x[n] - x[n-1])^2 + (y[n] - y[n-1])^2)        (raw and filtered)
lag    = sqrt((x_raw - x_filt)^2 + (y_raw - y_filt)^2)
```

Both are averaged over the recording. The measured fps is computed from timestamps, so the tau in `results/summary.csv` can differ slightly from the nominal values above.
