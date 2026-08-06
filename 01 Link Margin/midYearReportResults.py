"""
Report-ready RF downlink plots for the SX1262 at 915 MHz.

This script generates a compact set of figures suitable for a report/results section:
1. Idealised flight profile (altitude and velocity vs. time)
2. Link margin vs. range for LoRa spreading factors SF7-SF12
3. Sensitivity analysis heatmap for spreading factor and transmit power
4. A simple 5-element Yagi layout sketch for the ground station antenna

Sources used (factual references for the modelling choices):
- Semtech SX1262 Datasheet: LoRa sensitivity and transmit power values used for the
  link-budget calculations. The values included here are representative typical values
  for 125 kHz bandwidth and 915 MHz operation; exact values depend on the exact
  implementation and test conditions.
- H. T. Friis (1946), "A note on a simple transmission formula," Proceedings of the IRE.
- C. A. Balanis, Antenna Theory: Analysis and Design, 3rd ed. (2005), Chapter 4:
  monopole and dipole antenna theory with transmission-line matching networks.
- DL6WU Yagi calculator design values for the 5-element Yagi geometry used in the
  layout sketch and radiation pattern.
- KE5FX J-pole antenna reference (standard quarter-wave transmission-line stub matching
  design used for vertical monopole rockets).

Notes:
- The flight profile is an idealised report figure and is not a validated rocket flight
  simulation. It is intended to illustrate the report narrative and the link-budget
  analysis workflow.
- The Yagi pattern/geometry is approximate and is used here as a schematic report figure.
  For a publication-grade antenna study, a full EM simulation (e.g. NEC2/4NEC2 or FEKO)
  should be used.
"""

from pathlib import Path
from math import pi
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ----------------------------
# 1) Basic RF and antenna assumptions
# ----------------------------
FREQ_MHZ = 915.0
FREQ_HZ = FREQ_MHZ * 1e6
C0 = 299_792_458.0  # speed of light in m/s
WAVELENGTH_M = C0 / FREQ_HZ

# Representative SX1262 values, based on Semtech SX1262 data sheet (LoRa, 125 kHz BW)
# These are typical sensitivity values used in the report example.
SENSITIVITY_DBM = {
    "SF7": -124.0,
    "SF8": -127.0,
    "SF9": -130.0,
    "SF10": -133.0,
    "SF11": -136.0,
    "SF12": -139.0,
}

# Practical antenna assumptions for the report
TX_POWER_DBM = 22.0
TX_ANTENNA_GAIN_DBI = 2.15  # half-wave dipole / simple PCB antenna reference
RX_ANTENNA_GAIN_DBI = 10.0  # practical 5-element Yagi gain estimate
CABLE_LOSS_DB = 1.0
MIN_MARGIN_DB = 10.0

# ----------------------------
# 2) Idealised flight profile
# ----------------------------
TIME_S = np.array([0, 6, 12, 16, 24, 30, 36, 42, 50, 60, 70], dtype=float)
ALTITUDE_M = np.array([0, 600, 1800, 2500, 3200, 3600, 3500, 3000, 2400, 1400, 200], dtype=float)
VELOCITY_M_S = np.array([0, 80, 140, 160, 120, 70, 45, 35, 25, 20, 15], dtype=float)

# Smooth the profile for nicer plots
ALTITUDE_M = np.interp(np.linspace(0, 70, 400), TIME_S, ALTITUDE_M)
VELOCITY_M_S = np.interp(np.linspace(0, 70, 400), TIME_S, VELOCITY_M_S)
TIME_S = np.linspace(0, 70, 400)

# ----------------------------
# 3) Link budget model (Friis)
# ----------------------------
RANGES_M = np.linspace(100, 6000, 400)
FSPL_DB = 20 * np.log10((4 * pi * RANGES_M) / WAVELENGTH_M)

P_RX_DBM = TX_POWER_DBM + TX_ANTENNA_GAIN_DBI + RX_ANTENNA_GAIN_DBI - FSPL_DB - CABLE_LOSS_DB

# Link margin by spreading factor
LINK_MARGIN_BY_SF = {sf: P_RX_DBM - sens for sf, sens in SENSITIVITY_DBM.items()}

MAX_RANGE_BY_SF = {}
for sf, margin in LINK_MARGIN_BY_SF.items():
    # Solve Friis equation for the range at which the margin just reaches the threshold.
    fspl_at_threshold = TX_POWER_DBM + TX_ANTENNA_GAIN_DBI + RX_ANTENNA_GAIN_DBI - CABLE_LOSS_DB - SENSITIVITY_DBM[sf] - MIN_MARGIN_DB
    range_m = (WAVELENGTH_M / (4 * pi)) * 10 ** (fspl_at_threshold / 20)
    MAX_RANGE_BY_SF[sf] = range_m

# ----------------------------
# 4) Sensitivity sweep over transmit power and SF
# ----------------------------
TX_POWERS_DBM = np.array([10, 14, 18, 22], dtype=float)
SF_ORDER = ["SF7", "SF8", "SF9", "SF10", "SF11", "SF12"]

# For a fixed range, show how margin changes with SF and Tx power
RANGE_FOR_SWEEP_M = 3000.0
FSPL_SWEEP_DB = 20 * np.log10((4 * pi * RANGE_FOR_SWEEP_M) / WAVELENGTH_M)
HEATMAP = np.zeros((len(SF_ORDER), len(TX_POWERS_DBM)))
for i, sf in enumerate(SF_ORDER):
    for j, p_tx in enumerate(TX_POWERS_DBM):
        p_rx = p_tx + TX_ANTENNA_GAIN_DBI + RX_ANTENNA_GAIN_DBI - FSPL_SWEEP_DB - CABLE_LOSS_DB
        HEATMAP[i, j] = p_rx - SENSITIVITY_DBM[sf]

# ----------------------------
# 5) Plot helpers
# ----------------------------
OUTPUT_DIR = Path(__file__).resolve().parent / "plots"
OUTPUT_DIR.mkdir(exist_ok=True)


def save_plot(fig, name):
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / name, dpi=300, bbox_inches="tight")


# ----------------------------
# 6) Plot 1: flight profile
# ----------------------------
fig1, ax1 = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
ax1[0].plot(TIME_S, ALTITUDE_M / 1000.0, color="#1f77b4", linewidth=2)
ax1[0].set_ylabel("Altitude (km)")
ax1[0].set_title("Idealised Rocket Flight Profile at 915 MHz Downlink Study")
ax1[0].grid(alpha=0.3)

ax1[1].plot(TIME_S, VELOCITY_M_S, color="#d62728", linewidth=2)
ax1[1].set_xlabel("Time (s)")
ax1[1].set_ylabel("Velocity (m/s)")
ax1[1].grid(alpha=0.3)

for ax in ax1:
    ax.set_xlim(0, 70)

ax1[1].axvspan(0, 12, color="lightgray", alpha=0.2, label="Powered ascent")
ax1[1].axvspan(12, 30, color="lightgray", alpha=0.4, label="Coast to apogee")
ax1[1].axvspan(30, 40, color="lightgray", alpha=0.6, label="Deployment")
ax1[1].axvspan(40, 70, color="lightgray", alpha=0.8, label="Descent")
ax1[1].legend(loc="upper right", fontsize=8)

save_plot(fig1, "flight_profile.png")

# ----------------------------
# 7) Plot 2: link margin vs range
# ----------------------------
fig2, ax2 = plt.subplots(figsize=(8, 4.5))
for sf in SF_ORDER:
    ax2.plot(RANGES_M / 1000.0, LINK_MARGIN_BY_SF[sf], linewidth=2, label=sf)
ax2.axhline(MIN_MARGIN_DB, color="red", linestyle="--", linewidth=1.2, label=f"{MIN_MARGIN_DB} dB target")
ax2.set_xlabel("Range (km)")
ax2.set_ylabel("Link margin (dB)")
ax2.set_title("Link Margin vs Range for SX1262 at 915 MHz")
ax2.grid(alpha=0.3)
ax2.legend(loc="lower left", ncol=2)

# Annotate the 10 dB crossing for SF7 and SF12
for sf in ["SF7", "SF12"]:
    margin = LINK_MARGIN_BY_SF[sf]
    idx = np.where(margin >= MIN_MARGIN_DB)[0]
    if len(idx) > 0:
        x_cross = RANGES_M[idx[-1]] / 1000.0
        ax2.scatter(x_cross, MIN_MARGIN_DB, color="black", s=20)
        ax2.annotate(f"{sf}: {x_cross:.1f} km", (x_cross, MIN_MARGIN_DB), xytext=(5, 8), textcoords="offset points")

save_plot(fig2, "link_margin_vs_range.png")

# ----------------------------
# 8) Plot 3: sensitivity heatmap
# ----------------------------
fig3, ax3 = plt.subplots(figsize=(7.5, 4.5))
im = ax3.imshow(HEATMAP, cmap="viridis", aspect="auto")
ax3.set_xticks(np.arange(len(TX_POWERS_DBM)))
ax3.set_xticklabels([f"{p:.0f} dBm" for p in TX_POWERS_DBM])
ax3.set_yticks(np.arange(len(SF_ORDER)))
ax3.set_yticklabels(SF_ORDER)
ax3.set_title("Link Margin Sensitivity at 3 km Range")
ax3.set_xlabel("Transmit power")
ax3.set_ylabel("Spreading factor")

for i in range(HEATMAP.shape[0]):
    for j in range(HEATMAP.shape[1]):
        ax3.text(j, i, f"{HEATMAP[i, j]:.1f}", ha="center", va="center", color="white", fontsize=8)

cbar = fig3.colorbar(im, ax=ax3)
cbar.set_label("Link margin (dB)")

save_plot(fig3, "link_margin_heatmap.png")

# ----------------------------
# 9) Plot 4: simplified 5-element Yagi layout sketch
# ----------------------------
# Geometry values are illustrative and based on the common DL6WU-style 5-element Yagi
# layout used in the report example, not a full EM-optimised design.
fig4, ax4 = plt.subplots(figsize=(8, 2.8))
ax4.set_facecolor("white")
boom_length_mm = 224.0
ax4.fill_betweenx([-8, 8], 0, boom_length_mm, color="0.90")

elements = [
    ("Reflector", 159.0, 0.0),
    ("Driven", 152.0, 65.5),
    ("Director 1", 138.0, 90.1),
    ("Director 2", 136.0, 149.0),
    ("Director 3", 134.0, 220.0),
]
for name, length_mm, pos_mm in elements:
    color = "red" if name == "Reflector" else "green" if name == "Driven" else "blue"
    ax4.plot([pos_mm, pos_mm], [-18, 18], color=color, linewidth=2)
    ax4.text(pos_mm, 22, f"{name}\n{length_mm:.0f} mm", ha="center", fontsize=8)
ax4.set_xlim(-10, boom_length_mm + 10)
ax4.set_ylim(-30, 35)
ax4.axis("off")
ax4.set_title("Simplified 5-Element Yagi Layout at 915 MHz")

save_plot(fig4, "yagi_layout.png")

# ----------------------------
# 9b) Plot 5: Yagi radiation pattern (polar, azimuth plane)
# ----------------------------
# Simplified end-fire pattern: narrow main lobe forward with back lobe suppression
theta_deg = np.linspace(0, 360, 361)
theta_rad = np.deg2rad(theta_deg)

# End-fire pattern (simplified): maximum at 90 deg (broadside), sharper narrowing toward endfire
# Using a modified cosine pattern to represent approximate Yagi gain vs angle
gain_forward = np.cos(np.pi * (theta_rad - np.pi/2) / (np.pi/3))**2
gain_forward = np.where(np.abs(theta_rad - np.pi/2) <= np.pi/3, gain_forward, 0.1)
yagi_pattern = np.maximum(gain_forward, 0.05)
yagi_pattern_db = 10 * np.log10(yagi_pattern + 1e-6)
yagi_pattern_db = yagi_pattern_db - np.max(yagi_pattern_db)

fig5 = plt.figure(figsize=(6, 6))
ax5 = fig5.add_subplot(111, projection='polar')
ax5.plot(theta_rad, 10**(yagi_pattern_db/10), linewidth=2, color='#1f77b4')
ax5.set_theta_zero_location('E')
ax5.set_theta_direction(-1)
ax5.set_rlim(0, 1.0)
ax5.set_title('5-Element Yagi Radiation Pattern\n(Azimuth Plane, 915 MHz)', pad=20)
ax5.grid(True, alpha=0.3)

save_plot(fig5, "yagi_radiation_pattern.png")

# ----------------------------
# 10) Plot 6: JPole radiation pattern (polar, azimuth plane)
# ----------------------------
# JPole antenna: vertical monopole with quarter-wave matching stub transmission line.
# Source: Balanis CA. Antenna Theory: Analysis and Design. 3rd ed. Wiley 2005.
#   Chapter 4 (monopole and dipole antennas with matching networks).
# The radiation pattern is essentially that of a vertical monopole:
# omnidirectional in azimuth, maximum in the horizontal plane.
# In practice, presence of feedline and ground plane causes minor asymmetry (~1-2 dB ripple).

# Vertical monopole azimuth pattern (omnidirectional, slight ripple from feedline):
jpole_pattern = 0.97 + 0.03 * np.cos(2 * theta_rad)  # ~3% ripple typical for mounted JPole
jpole_pattern_db = 10 * np.log10(jpole_pattern + 1e-6)
jpole_pattern_db = jpole_pattern_db - np.max(jpole_pattern_db)

fig6 = plt.figure(figsize=(6, 6))
ax6 = fig6.add_subplot(111, projection='polar')
ax6.plot(theta_rad, 10**(jpole_pattern_db/10), linewidth=2, color='#ff7f0e')
ax6.set_theta_zero_location('E')
ax6.set_theta_direction(-1)
ax6.set_rlim(0, 1.0)
ax6.set_title('JPole Antenna Radiation Pattern\n(Azimuth Plane, 915 MHz)', pad=20)
ax6.grid(True, alpha=0.3)

save_plot(fig6, "jpole_radiation_pattern.png")

# ----------------------------
# 11) Plot 7: JPole dimensions diagram (actual J-shape)
# ----------------------------
# JPole antenna design at 915 MHz based on standard vertical monopole with quarter-wave feed stub.
# Source: Balanis CA. Antenna Theory: Analysis and Design. 3rd ed. Wiley 2005.
#   Chapter 4: transmission-line fed monopoles; matching stub length λ/4.
# Also: KE5FX J-pole antenna design reference (amateur radio standard).
# Wavelength at 915 MHz: λ = c/f = 327.6 mm.
# The J-pole gets its name from the shape: vertical radiator on top, parallel stub below forming the "J".
# Standard J-pole proportions:
#   - Driven element (vertical radiator): ~0.62 λ (for 915 MHz, ~203 mm).
#   - Stub element (quarter-wave transformer, parallel to driven): ~0.25 λ (~82 mm).
#   - Spacing between driven and stub: ~0.05-0.1 λ (typical 15-30 mm for coax feed).
#   - Feed point: at top of stub, bottom of radiator.

wavelength_mm = 327.6  # at 915 MHz

fig7, ax7 = plt.subplots(figsize=(6, 10))
ax7.set_facecolor("white")

# Radiator element (vertical, top part of "J")
radiator_length_mm = 0.62 * wavelength_mm  # ~203 mm
radiator_x = 50
radiator_top = 150
radiator_bottom = radiator_top - radiator_length_mm * 0.4  # scaled for visibility

ax7.plot([radiator_x, radiator_x], [radiator_top, radiator_bottom], 'g-', linewidth=7, label='Radiator element (~0.62λ)')
ax7.plot([radiator_x - 2, radiator_x + 2], [radiator_top, radiator_top], 'go', markersize=8)
ax7.text(radiator_x + 8, radiator_top - 5, 'Top\n(open end)', fontsize=9, fontweight='bold')

# Spacing and horizontal section (the hook of the "J")
spacing_mm = 25.0
spacing_x_offset = spacing_mm * 0.12  # scaled
horizontal_x = radiator_x + spacing_x_offset

# Draw horizontal connector (top of stub section)
ax7.plot([radiator_x, horizontal_x], [radiator_bottom, radiator_bottom], 'k-', linewidth=2)

# Stub element (parallel to radiator, forms bottom of "J")
stub_length_mm = 0.25 * wavelength_mm  # ~82 mm
stub_drawn = stub_length_mm * 0.4

ax7.plot([horizontal_x, horizontal_x], [radiator_bottom, radiator_bottom - stub_drawn], 
         'r-', linewidth=7, label='Stub element (~0.25λ, λ/4 transformer)')

# Short circuit at bottom of stub
ax7.plot([horizontal_x - 3, horizontal_x + 3], [radiator_bottom - stub_drawn, radiator_bottom - stub_drawn], 
         'r-', linewidth=8)
ax7.text(horizontal_x + 8, radiator_bottom - stub_drawn, 'Short\ncircuit', fontsize=9, fontweight='bold')

# Feed point (between radiator and stub top)
feed_x = (radiator_x + horizontal_x) / 2
feed_y = radiator_bottom + 3
ax7.plot(feed_x, feed_y, 'b*', markersize=25, label='Feed point (SMA connector)')
ax7.text(feed_x - 15, feed_y + 10, 'SMA\nConnector\n50Ω', fontsize=9, ha='center', 
         bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

# Dimension annotations
# Radiator length
ax7.annotate('', xy=(25, radiator_top), xytext=(25, radiator_bottom), 
             arrowprops=dict(arrowstyle='<->', color='green', lw=2.5))
ax7.text(18, (radiator_top + radiator_bottom) / 2, f'Radiator\n0.62λ\n≈{radiator_length_mm:.0f}mm', 
         fontsize=10, ha='right', fontweight='bold', color='darkgreen')

# Stub length
ax7.annotate('', xy=(75, radiator_bottom), xytext=(75, radiator_bottom - stub_drawn), 
             arrowprops=dict(arrowstyle='<->', color='red', lw=2.5))
ax7.text(82, (radiator_bottom + radiator_bottom - stub_drawn) / 2, f'Stub\n0.25λ\n≈{stub_length_mm:.0f}mm', 
         fontsize=10, ha='left', fontweight='bold', color='darkred')

# Spacing
ax7.annotate('', xy=(radiator_x - 3, radiator_bottom + 8), xytext=(horizontal_x + 3, radiator_bottom + 8), 
             arrowprops=dict(arrowstyle='<->', color='purple', lw=2))
ax7.text((radiator_x + horizontal_x) / 2, radiator_bottom + 15, f'Spacing ≈{spacing_mm:.0f}mm\n(coax feed)', 
         fontsize=9, ha='center', color='purple', fontweight='bold')

ax7.set_xlim(5, 100)
ax7.set_ylim(0, 160)
ax7.axis('off')
ax7.set_title('J-Pole Antenna Geometry at 915 MHz\n(Quarter-Wave Matching Stub + Monopole Radiator)', 
              fontsize=12, fontweight='bold')
ax7.legend(loc='upper right', fontsize=9, framealpha=0.95)

save_plot(fig7, "jpole_dimensions.png")

# ----------------------------
# 12) Print a concise report summary and the references
# ----------------------------
print("Generated report plots in:")
print(OUTPUT_DIR)
print("\nKey link-budget results:")
for sf in SF_ORDER:
    print(f"- {sf}: {MAX_RANGE_BY_SF[sf]/1000:.2f} km max range at {MIN_MARGIN_DB} dB margin")
print("\nSources used:")
print("- Semtech SX1262 datasheet (LoRa sensitivity / transmit power values).")
print("- Friis, H. T. (1946). A note on a simple transmission formula. Proceedings of the IRE.")
print("- Balanis, C. A. (2005). Antenna Theory: Analysis and Design, 3rd ed. Wiley.")
print("  Chapter 4: monopole, dipole, and transmission-line fed antenna matching.")
print("- DL6WU Yagi calculator design values for 5-element Yagi schematic layout.")
print("- KE5FX J-pole antenna reference (amateur radio standard quarter-wave feed stub design).")

# Show figures on screen (non-blocking) and then close them cleanly if desired.
plt.show()
