import os
import numpy as np
import matplotlib.pyplot as plt

# Sample flight path generator and plotter
# Produces a 2D downrange vs altitude trajectory split into 4 stages.

def generate_flight_path():
    # Define segment lengths (downrange distance units)
    seg_lengths = [10, 20, 30, 15]

    # Create x coordinates for each segment
    xs = []
    ys = []
    x_offset = 0.0

    # Stage 1: Boost — steep ascent
    x1 = np.linspace(0, seg_lengths[0], 100)
    y1 = 100 * (x1 / seg_lengths[0])**1.5 + 10 * np.sin(0.2 * x1)
    xs.append(x_offset + x1)
    ys.append(y1)
    x_offset += seg_lengths[0]

    # Stage 2: Sustained burn / transition — continued climb
    x2 = np.linspace(0, seg_lengths[1], 200)
    y2 = y1[-1] + 150 * (x2 / seg_lengths[1])**0.9 + 5 * np.sin(0.15 * x2)
    xs.append(x_offset + x2)
    ys.append(y2)
    x_offset += seg_lengths[1]

    # Stage 3: Coast — leveling off and slight descent
    x3 = np.linspace(0, seg_lengths[2], 300)
    y3 = y2[-1] + 50 * np.cos((x3 / seg_lengths[2]) * 1.5) - 0.5 * x3
    xs.append(x_offset + x3)
    ys.append(y3)
    x_offset += seg_lengths[2]

    # Stage 4: Final burn / descent to apogee / descent
    x4 = np.linspace(0, seg_lengths[3], 150)
    y4 = y3[-1] - 30 * (x4 / seg_lengths[3]) + 20 * np.exp(-0.3 * x4)
    xs.append(x_offset + x4)
    ys.append(y4)

    # Concatenate
    x = np.concatenate(xs)
    y = np.concatenate(ys)

    # Stage boundary x positions
    boundaries = np.cumsum(seg_lengths)[:-1]
    return x, y, boundaries


def plot_flight_path(x, y, boundaries, save_path=None):
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(x, y, lw=2, color="#1f77b4")
    ax.set_xlabel("Downrange distance (km)")
    ax.set_ylabel("Altitude (km)")
    ax.set_title("Flight Path with 4 Stages")

    # Shade each stage region with different colors and label them
    stage_colors = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3"]
    stage_names = ["Stage 1: Boost", "Stage 2: Transition", "Stage 3: Coast", "Stage 4: Final"]

    x_start = x[0]
    for i, b in enumerate(list(boundaries) + [x[-1]]):
        x_end = b
        ax.axvspan(x_start, x_end, color=stage_colors[i], alpha=0.12)
        ax.text((x_start + x_end) / 2, max(y) * 0.9, stage_names[i], ha="center", va="center", fontsize=9)
        x_start = x_end

    # Mark boundaries
    for bx in boundaries:
        ax.axvline(bx, color="#555555", linestyle="--", lw=1)

    ax.grid(True, linestyle=':', alpha=0.6)

    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, dpi=200)
        print(f"Saved plot to: {save_path}")

    plt.show()


if __name__ == "__main__":
    x, y, boundaries = generate_flight_path()
    out_path = os.path.join("outputs", "flight_path_stages.png")
    plot_flight_path(x, y, boundaries, save_path=out_path)
