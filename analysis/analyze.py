"""Offline analysis of the tracking CSVs recorded by src/sensor_project_code.py.

Computes the metrics used in the EECS 150 report and saves plots to results/.

    python analysis/analyze.py

Metrics
-------
jitter : mean frame-to-frame displacement (px/frame), raw vs filtered
lag    : mean distance between the raw and filtered position (px)
tau    : theoretical EMA time constant, tau = -Ts / ln(1 - alpha)
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)

ALPHA = 0.1
RUNS = {
    "V1 (30 fps, Pi 4)": DATA / "tracking_data_v1_30fps.csv",
    "V2 (90 fps, Pi 5)": DATA / "tracking_data_v2_90fps.csv",
}


def load(path):
    df = pd.read_csv(path)
    df["raw_jitter"] = np.hypot(df.raw_x.diff(), df.raw_y.diff())
    df["filt_jitter"] = np.hypot(df.filtered_x.diff(), df.filtered_y.diff())
    df["lag"] = np.hypot(df.raw_x - df.filtered_x, df.raw_y - df.filtered_y)
    return df


def summarize(name, df):
    fps = len(df) / (df.timestamp.iloc[-1] - df.timestamp.iloc[0])
    ts = 1.0 / fps
    tau = -ts / np.log(1 - ALPHA)
    raw_j, filt_j = df.raw_jitter.mean(), df.filt_jitter.mean()
    return {
        "run": name,
        "samples": len(df),
        "fps": round(fps, 1),
        "raw jitter (px)": round(raw_j, 1),
        "filtered jitter (px)": round(filt_j, 1),
        "jitter reduction (%)": round(100 * (1 - filt_j / raw_j), 1),
        "mean lag (px)": round(df.lag.mean(), 1),
        "tau (s)": round(tau, 3),
        "cutoff (Hz)": round(1 / (2 * np.pi * tau), 2),
    }


def style(ax, title, xlabel, ylabel):
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25)


def plot_jitter(name, df, tag):
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(df.timestamp, df.raw_jitter, color="tab:red", lw=0.8, label=f"raw (mean {df.raw_jitter.mean():.0f} px)")
    ax.plot(df.timestamp, df.filt_jitter, color="tab:green", lw=1.2, label=f"filtered (mean {df.filt_jitter.mean():.0f} px)")
    style(ax, f"Frame-to-frame jitter, {name}", "Time (s)", "px / frame")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / f"jitter_{tag}.png", dpi=150)
    plt.close(fig)


def plot_xy(name, df, tag):
    fig, axes = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
    for ax, axis in zip(axes, ("x", "y")):
        ax.plot(df.timestamp, df[f"raw_{axis}"], color="tab:red", lw=0.8, label="raw")
        ax.plot(df.timestamp, df[f"filtered_{axis}"], color="tab:green", lw=1.4, label="filtered")
        style(ax, "", "", f"{axis.upper()} (px)")
    axes[0].set_title(f"X / Y position over time, {name}")
    axes[1].set_xlabel("Time (s)")
    axes[0].legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / f"xy_over_time_{tag}.png", dpi=150)
    plt.close(fig)


def plot_trajectory(name, df, tag):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sc = ax.scatter(df.raw_x, df.raw_y, c=df.timestamp, s=6, cmap="autumn_r", alpha=0.7, label="raw")
    ax.plot(df.filtered_x, df.filtered_y, color="tab:green", lw=1.0, label="filtered")
    ax.invert_yaxis()
    fig.colorbar(sc, ax=ax, label="Time (s)")
    style(ax, f"2D trajectory, {name}", "X (px)", "Y (px)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / f"trajectory_{tag}.png", dpi=150)
    plt.close(fig)


def plot_lag(name, df, tag):
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.fill_between(df.timestamp, df.lag, color="tab:purple", alpha=0.5)
    ax.axhline(df.lag.mean(), color="k", ls="--", lw=1, label=f"mean {df.lag.mean():.0f} px")
    style(ax, f"Filter tracking lag, {name}", "Time (s)", "lag (px)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / f"lag_{tag}.png", dpi=150)
    plt.close(fig)


def plot_alpha_sweep(df, name, tag):
    """Re-filter the recorded raw signal offline with different alphas to show
    the smoothness vs lag trade-off. Raw coordinates are fixed, so this isolates alpha."""
    alphas = np.array([0.05, 0.1, 0.2, 0.3, 0.5, 0.8])
    jit, lag = [], []
    rx, ry = df.raw_x.to_numpy(float), df.raw_y.to_numpy(float)
    for a in alphas:
        fx, fy = np.empty_like(rx), np.empty_like(ry)
        fx[0], fy[0] = rx[0], ry[0]
        for i in range(1, len(rx)):
            fx[i] = a * rx[i] + (1 - a) * fx[i - 1]
            fy[i] = a * ry[i] + (1 - a) * fy[i - 1]
        jit.append(np.hypot(np.diff(fx), np.diff(fy)).mean())
        lag.append(np.hypot(rx - fx, ry - fy).mean())
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(lag, jit, "o-", color="tab:blue")
    for a, x, y in zip(alphas, lag, jit):
        ax.annotate(f"a={a}", (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)
    style(ax, f"Alpha sweep (offline), {name}", "mean lag (px)", "mean jitter (px/frame)")
    fig.tight_layout()
    fig.savefig(OUT / f"alpha_sweep_{tag}.png", dpi=150)
    plt.close(fig)
    return pd.DataFrame({"alpha": alphas, "jitter_px": np.round(jit, 1), "lag_px": np.round(lag, 1)})


def main():
    rows, sweeps = [], []
    for name, path in RUNS.items():
        tag = path.stem.split("_")[2]  # v1 / v2
        df = load(path)
        rows.append(summarize(name, df))
        plot_jitter(name, df, tag)
        plot_xy(name, df, tag)
        plot_trajectory(name, df, tag)
        plot_lag(name, df, tag)
        sw = plot_alpha_sweep(df, name, tag)
        sw.insert(0, "run", name)
        sweeps.append(sw)

    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / "summary.csv", index=False)
    pd.concat(sweeps).to_csv(OUT / "alpha_sweep.csv", index=False)
    print(summary.to_string(index=False))
    print("\nplots written to", OUT)


if __name__ == "__main__":
    main()
