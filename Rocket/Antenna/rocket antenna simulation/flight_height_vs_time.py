import os
import numpy as np
import matplotlib.pyplot as plt

# Flight height vs time generator and plotter

def generate_flight_path():
    # Define segment durations (seconds) for the 4 flight stages
    seg_durations = [10, 30, 60, 20]

    # Create time arrays and heights (meters) for each segment
    ts = []
    hs = []
    t_offset = 0.0

    # Stage 1: Boost — steep ascent
    t1 = np.linspace(0, seg_durations[0], 100)
    h1 = 1000 * (t1 / seg_durations[0])**1.5 + 50 * np.sin(0.2 * t1)
    ts.append(t_offset + t1)
    hs.append(h1)
    t_offset += seg_durations[0]

    # Stage 2: Sustained burn / transition — continued climb
    t2 = np.linspace(0, seg_durations[1], 200)
    h2 = h1[-1] + 3000 * (t2 / seg_durations[1])**0.9 + 30 * np.sin(0.15 * t2)
    ts.append(t_offset + t2)
    hs.append(h2)
    t_offset += seg_durations[1]

    # Stage 3: Coast — leveling off and slight descent
    t3 = np.linspace(0, seg_durations[2], 300)
    # ensure term is zero at t3=0 to avoid a jump: cos(0)=1 so (cos-1)=0
    h3 = h2[-1] + 200 * (np.cos((t3 / seg_durations[2]) * 1.5) - 1) - 5 * t3
    ts.append(t_offset + t3)
    hs.append(h3)
    t_offset += seg_durations[2]

    # Stage 4: Final descent — ensure final height returns to ground (0 m)
    t4 = np.linspace(0, seg_durations[3], 150)
    T4 = seg_durations[3]
    # smooth descent profile that is h3[-1] at t4=0 and 0 at t4=T4
    # use a simple quadratic: h(t) = h0 * (1 - (t/T)^2)
    h0 = h3[-1]
    h4 = h0 * (1 - (t4 / T4)**2)
    # numerical safety: do not go negative
    h4 = np.maximum(h4, 0.0)
    ts.append(t_offset + t4)
    hs.append(h4)

    # Concatenate
    t = np.concatenate(ts)
    h = np.concatenate(hs)

    # Stage boundary time positions
    boundaries = np.cumsum(seg_durations)[:-1]
    return t, h, boundaries


def plot_flight_path(t, h, boundaries, save_path=None):
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(t, h, lw=2, color="#1f77b4")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Height (m)")
    ax.set_title("Height vs Time with 4 Flight Stages")

    # Shade each stage region with different colors and label them
    stage_colors = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3"]
    stage_names = ["Stage 1: Boost", "Stage 2: Transition", "Stage 3: Coast", "Stage 4: Final"]

    t_start = t[0]
    for i, b in enumerate(list(boundaries) + [t[-1]]):
        t_end = b
        ax.axvspan(t_start, t_end, color=stage_colors[i], alpha=0.12)
        ax.text((t_start + t_end) / 2, max(h) * 0.9, stage_names[i], ha="center", va="center", fontsize=9)
        t_start = t_end

    # Mark boundaries
    for bt in boundaries:
        ax.axvline(bt, color="#555555", linestyle="--", lw=1)

    ax.grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, dpi=200)
        print(f"Saved plot to: {save_path}")

    plt.show()


if __name__ == "__main__":
    t, h, boundaries = generate_flight_path()
    out_path = os.path.join("outputs", "flight_height_vs_time.png")
    plot_flight_path(t, h, boundaries, save_path=out_path)
