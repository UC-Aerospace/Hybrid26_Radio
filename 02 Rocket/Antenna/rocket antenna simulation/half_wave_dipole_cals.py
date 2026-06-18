"""
Half Wave Dipole Antenna Design Calculator
Based on Balanis - Antenna Theory: Analysis and Design
Chapters 2 (Fundamental Parameters) and 4 (Linear Wire Antennas)

Application: 915 MHz ISM band telemetry for SRAD hybrid rocket
Author: Joella Tomkins
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

# ============================================================
# CONSTANTS
# ============================================================
c = 299_792_458.0   # speed of light in vacuum (m/s)
eta = 120 * np.pi  # intrinsic impedance of free space (Ohms) ~377 Ohms
# Balanis Eq. 2-33: eta = sqrt(mu0/eps0) = 120*pi

# ============================================================
# 1. OPERATING FREQUENCY AND WAVELENGTH
# ============================================================
f = 915e6        # operating frequency (Hz)

# Balanis Eq. 4-2: wavelength in free space
lam = c / f      # wavelength (m)
lam_mm = lam * 1000  # wavelength in mm

print("=" * 60)
print("  HALF WAVE DIPOLE ANTENNA CALCULATOR — 915 MHz")
print("=" * 60)
print(f"\n1. FREQUENCY AND WAVELENGTH")
print(f"   Frequency:              f  = {f/1e6:.1f} MHz")
print(f"   Free space wavelength:  λ  = {lam:.4f} m = {lam_mm:.2f} mm")

# ============================================================
# 2. PHYSICAL ELEMENT LENGTH
# ============================================================
# Balanis Ch. 4: half wave dipole element length = lambda/2
# Velocity factor correction for bare copper wire in air
VF = 0.95        # velocity factor for bare copper wire in air
# Wave travels at VF * c along the conductor due to small
# distributed inductance and capacitance of the wire

L_ideal = lam / 2               # ideal half wavelength (m)
L_corrected = L_ideal * VF      # velocity factor corrected length (m)
L_arm = L_corrected / 2         # each arm length (m)

L_ideal_mm = L_ideal * 1000
L_corrected_mm = L_corrected * 1000
L_arm_mm = L_arm * 1000

print(f"\n2. PHYSICAL ELEMENT LENGTH")
print(f"   Velocity factor (bare Cu wire in air): VF = {VF}")
print(f"   Ideal half wavelength:    λ/2        = {L_ideal_mm:.2f} mm")
print(f"   Corrected total length:   L_total    = {L_corrected_mm:.2f} mm")
print(f"   Each arm length:          L_arm      = {L_arm_mm:.2f} mm")
print(f"   >> Start at 80 mm per arm and trim to resonance with VNA")

# ============================================================
# 3. INPUT IMPEDANCE
# ============================================================
# Balanis Eq. 4-70: input impedance of half wave dipole
# Z_in = 73 + j42.5 Ohms (theoretical, infinite thin wire)
# Real part = radiation resistance Rr = 73 Ohms
# Imaginary part = reactive part, tuned out at resonance
# At exact resonance (slightly shorter than lambda/2) Im -> 0

R_in = 73.0          # radiation resistance (Ohms) Balanis Eq. 4-70
X_in = 42.5          # reactive part (Ohms) at lambda/2
Z_in = complex(R_in, X_in)

# At resonance (slightly shorter element) impedance is purely real
R_resonance = 73.0   # Ohms — this is what you design to

print(f"\n3. INPUT IMPEDANCE")
print(f"   Theoretical Z_in (λ/2):  {R_in} + j{X_in} Ω  (Balanis Eq. 4-70)")
print(f"   At resonance (trimmed):  Z_in = {R_resonance} Ω (purely resistive)")

# ============================================================
# 4. IMPEDANCE MISMATCH TO 50 OHM SYSTEM
# ============================================================
# Balanis Ch. 2 — Reflection coefficient and return loss
Z_source = 50.0      # system impedance (Ohms) — SMA, SX1262, PCB trace

# Balanis Eq. 2-64: voltage reflection coefficient
Gamma = (R_resonance - Z_source) / (R_resonance + Z_source)
Gamma_mag_sq = abs(Gamma)**2

# Return loss (dB) — Balanis Eq. 2-66
RL_dB = -20 * np.log10(abs(Gamma))

# VSWR — Balanis Eq. 2-68
VSWR = (1 + abs(Gamma)) / (1 - abs(Gamma))

# Mismatch loss — power lost to reflection
mismatch_loss_dB = -10 * np.log10(1 - Gamma_mag_sq)
pct_reflected = Gamma_mag_sq * 100

print(f"\n4. IMPEDANCE MISMATCH ANALYSIS (73 Ω dipole into 50 Ω system)")
print(f"   Reflection coefficient:  Γ    = {Gamma:.4f}")
print(f"   Return loss:             RL   = {RL_dB:.2f} dB")
print(f"   VSWR:                         = {VSWR:.2f} : 1")
print(f"   Mismatch loss:                = {mismatch_loss_dB:.3f} dB")
print(f"   Power reflected:              = {pct_reflected:.2f} %")
print(f"   >> Acceptable for SRAD telemetry — no matching network needed")

# ============================================================
# 5. RADIATION RESISTANCE AND EFFICIENCY
# ============================================================
# Balanis Eq. 4-67: radiation resistance of half wave dipole
# Rr = 73 Ohms (same as input resistance at resonance for lossless antenna)
Rr = 73.0   # Ohms

# For a practical copper wire antenna, ohmic loss resistance is very small
# Balanis Ch. 2: radiation efficiency e_cd = Rr / (Rr + R_loss)
# For a short copper wire at 915 MHz, R_loss << Rr
R_loss_estimate = 0.5   # Ohms — estimated ohmic loss for short Cu wire

e_cd = Rr / (Rr + R_loss_estimate)    # conduction-dielectric efficiency
e_cd_dB = 10 * np.log10(e_cd)

print(f"\n5. RADIATION RESISTANCE AND EFFICIENCY")
print(f"   Radiation resistance:    Rr       = {Rr} Ω  (Balanis Eq. 4-67)")
print(f"   Estimated ohmic loss:    R_loss   ≈ {R_loss_estimate} Ω")
print(f"   Radiation efficiency:    e_cd     = {e_cd:.4f} = {e_cd_dB:.3f} dB")

# ============================================================
# 6. DIRECTIVITY AND GAIN
# ============================================================
# Balanis Eq. 4-69: directivity of half wave dipole
D0 = 1.643          # dimensionless — Balanis Eq. 4-69
D0_dBi = 10 * np.log10(D0)

# Balanis Eq. 2-49: gain = efficiency * directivity
G0 = e_cd * D0
G0_dBi = 10 * np.log10(G0)

# Total antenna gain including impedance mismatch
# Balanis Eq. 2-49b: realised gain = (1 - |Gamma|^2) * G0
G_realised = (1 - Gamma_mag_sq) * G0
G_realised_dBi = 10 * np.log10(G_realised)

print(f"\n6. DIRECTIVITY AND GAIN")
print(f"   Directivity:             D0       = {D0} = {D0_dBi:.3f} dBi  (Balanis Eq. 4-69)")
print(f"   Gain (with efficiency):  G0       = {G0:.4f} = {G0_dBi:.3f} dBi")
print(f"   Realised gain (with mismatch): Gr = {G_realised:.4f} = {G_realised_dBi:.3f} dBi")

# ============================================================
# 7. EFFECTIVE APERTURE AND EFFECTIVE LENGTH
# ============================================================
# Balanis Ch. 2: effective aperture relation
# Ae = (lambda^2 / 4*pi) * G
# Use realised gain for practical link budgets, and ideal (D0) for reference.
Aem_ideal = (lam**2 / (4 * np.pi)) * D0
Aem_realised = (lam**2 / (4 * np.pi)) * G_realised

# Balanis Ch. 4: effective length (effective height) at maximum for a thin half-wave dipole
# le = lambda / pi
le = lam / np.pi
le_mm = le * 1000

print(f"\n7. EFFECTIVE APERTURE AND EFFECTIVE LENGTH")
print(f"   Ideal effective aperture (from D0):   Aem,ideal = {Aem_ideal*1e4:.4f} cm²")
print(f"   Realised effective aperture (from Gr): Aem,real  = {Aem_realised*1e4:.4f} cm²")
print(f"   Effective length:        le  = {le_mm:.2f} mm  (Balanis Eq. 4-59)")

# ============================================================
# 8. RADIATION PATTERN — ELEVATION PLANE (E-PLANE)
# ============================================================
# Balanis Eq. 4-58a: normalised field pattern of half wave dipole
# F(theta) = [ cos(pi/2 * cos(theta)) / sin(theta) ]^2
# theta = elevation angle from antenna axis (0 = along axis, 90 = broadside)

theta = np.linspace(0.001, np.pi - 0.001, 3600)   # avoid sin(0) = 0

# Balanis Eq. 4-58a field pattern
F_theta = (np.cos((np.pi / 2) * np.cos(theta)) / np.sin(theta))**2

# Normalise to maximum
F_norm = F_theta / np.max(F_theta)
F_norm_dB = 10 * np.log10(F_norm + 1e-10)   # add small offset to avoid log(0)

# Pattern in terms of elevation from ground (phi = 90 - theta in Balanis convention)
# For rocket application: theta=90 deg = broadside (horizontal) = max gain
# theta=0 or 180 deg = along antenna axis = null

print(f"\n8. RADIATION PATTERN")
print(f"   Pattern function: F(θ) = [cos(π/2·cosθ) / sinθ]²  (Balanis Eq. 4-58a)")
print(f"   Maximum gain at θ = 90° (broadside, perpendicular to antenna axis)")
print(f"   Null at θ = 0° and θ = 180° (along antenna axis)")

# Half power beamwidth — find angles where F = 0.5
idx_half = np.where(F_norm >= 0.5)[0]
if len(idx_half) > 0:
    theta_hp1 = np.degrees(theta[idx_half[0]])
    theta_hp2 = np.degrees(theta[idx_half[-1]])
    HPBW = theta_hp2 - theta_hp1
    print(f"   Half Power Beamwidth:    HPBW = {HPBW:.1f}°")

# ============================================================
# 9. GAIN AS FUNCTION OF ELEVATION ANGLE (for link budget)
# ============================================================
# This is what feeds into the time-stepped link budget model
# elevation_angle = angle above horizon (0 = horizontal, 90 = directly above)
# In Balanis convention: theta_balanis = 90 - elevation_angle

elevation_deg = np.linspace(0, 90, 91)    # 0 to 90 degrees above horizon
theta_balanis = np.radians(90 - elevation_deg)   # convert to Balanis theta

# Avoid singularity at theta=0 (antenna axis)
theta_balanis = np.clip(theta_balanis, 0.001, np.pi - 0.001)

F_elevation = (np.cos((np.pi / 2) * np.cos(theta_balanis)) / np.sin(theta_balanis))**2
F_elevation_norm = F_elevation / np.max(F_elevation)

# Realised gain in dBi at each elevation angle
G_elevation_dBi = G_realised_dBi + 10 * np.log10(F_elevation_norm + 1e-10)

print(f"\n9. GAIN VS ELEVATION ANGLE (for link budget model)")
print(f"   {'Elevation (°)':<20} {'Gain (dBi)':<15}")
print(f"   {'-'*35}")
for elev in [0, 10, 20, 30, 45, 60, 75, 90]:
    idx = elev
    print(f"   {elev:<20} {G_elevation_dBi[idx]:<15.2f}")

# ============================================================
# 10. FREE SPACE LINK BUDGET PARAMETERS
# ============================================================
# Balanis Ch. 2 — Friis transmission equation
# Pr/Pt = Gt * Gr * (lambda / 4*pi*R)^2
# In dB: Pr_dBm = Pt_dBm + Gt_dBi + Gr_dBi - FSPL_dB

# SX1262 parameters
Pt_dBm = 22.0       # transmit power (dBm) — SX1262 max
# Receiver sensitivity varies with spreading factor
sensitivity = {
    'SF7':  -124,
    'SF8':  -127,
    'SF9':  -130,
    'SF10': -133,
    'SF11': -136,
    'SF12': -139,
}

Gr_ground_dBi = 10.0    # ground station Yagi gain (dBi)

print(f"\n10. LINK BUDGET PARAMETERS")
print(f"    Transmit power:          Pt  = {Pt_dBm} dBm")
print(f"    Rocket antenna gain:     Gt  = {G_realised_dBi:.2f} dBi (realised)")
print(f"    Ground station gain:     Gr  = {Gr_ground_dBi} dBi")
print(f"\n    SX1262 receiver sensitivity:")
for sf, sens in sensitivity.items():
    print(f"      {sf}: {sens} dBm")

# FSPL at various distances
distances_m = [100, 500, 1000, 2000, 3000, 4000, 5000]
print(f"\n    Free Space Path Loss vs Distance (Friis, Balanis Eq. 2-116):")
print(f"    {'Distance (m)':<15} {'FSPL (dB)':<12} {'Link Margin SF7':<18} {'Link Margin SF12'}")
print(f"    {'-'*65}")
for d in distances_m:
    # Balanis Eq. 2-116: FSPL = (4*pi*R/lambda)^2
    FSPL_dB = 20 * np.log10((4 * np.pi * d) / lam)
    Pr_dBm = Pt_dBm + G_realised_dBi + Gr_ground_dBi - FSPL_dB
    margin_SF7  = Pr_dBm - sensitivity['SF7']
    margin_SF12 = Pr_dBm - sensitivity['SF12']
    print(f"    {d:<15} {FSPL_dB:<12.1f} {margin_SF7:<18.1f} {margin_SF12:.1f}")

# ============================================================
# 11. PLOTS
# ============================================================
fig = plt.figure(figsize=(14, 10))
fig.suptitle('Half Wave Dipole Antenna — 915 MHz\nBalanis Chapters 2 & 4', fontsize=13)
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.35)

# --- Plot 1: Polar radiation pattern (elevation plane) ---
ax1 = fig.add_subplot(gs[0, 0], projection='polar')
ax1.plot(theta, F_norm, color='steelblue', linewidth=2)
ax1.plot(-theta, F_norm, color='steelblue', linewidth=2)  # mirror for full pattern
ax1.set_theta_zero_location('N')
ax1.set_theta_direction(-1)
ax1.set_title('Elevation plane\nradiation pattern', pad=15, fontsize=10)
ax1.set_rticks([0.25, 0.5, 0.75, 1.0])
ax1.set_rlabel_position(90)

# --- Plot 2: Gain vs elevation angle ---
ax2 = fig.add_subplot(gs[0, 1])
ax2.plot(elevation_deg, G_elevation_dBi, color='steelblue', linewidth=2)
ax2.axhline(y=0, color='gray', linestyle='--', linewidth=0.8, alpha=0.6)
ax2.set_xlabel('Elevation angle (degrees above horizon)')
ax2.set_ylabel('Gain (dBi)')
ax2.set_title('Antenna gain vs elevation angle\n(for link budget model)', fontsize=10)
ax2.set_xlim(0, 90)
ax2.grid(True, alpha=0.3)
ax2.annotate('Null at 90°\n(directly overhead)', xy=(90, G_elevation_dBi[-1]),
             xytext=(70, -10), fontsize=8,
             arrowprops=dict(arrowstyle='->', color='gray'))

# --- Plot 3: Link margin vs distance for all SFs ---
ax3 = fig.add_subplot(gs[1, 0])
distances_plot = np.linspace(100, 6000, 500)
colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0', '#00BCD4']
for (sf, sens), col in zip(sensitivity.items(), colors):
    FSPL_plot = 20 * np.log10((4 * np.pi * distances_plot) / lam)
    Pr_plot = Pt_dBm + G_realised_dBi + Gr_ground_dBi - FSPL_plot
    margin_plot = Pr_plot - sens
    ax3.plot(distances_plot, margin_plot, label=sf, color=col, linewidth=1.5)
ax3.axhline(y=10, color='red', linestyle='--', linewidth=1.2, label='10 dB min margin')
ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
ax3.set_xlabel('Slant range (m)')
ax3.set_ylabel('Link margin (dB)')
ax3.set_title('Link margin vs range\n(broadside, Yagi ground station 10 dBi)', fontsize=10)
ax3.legend(fontsize=7, loc='upper right')
ax3.grid(True, alpha=0.3)
ax3.set_xlim(100, 6000)

# --- Plot 4: Pattern in dB ---
ax4 = fig.add_subplot(gs[1, 1])
ax4.plot(np.degrees(theta), F_norm_dB, color='steelblue', linewidth=2)
ax4.axhline(y=-3, color='orange', linestyle='--', linewidth=1, label='-3 dB (HPBW)')
ax4.set_xlabel('θ (degrees from antenna axis)')
ax4.set_ylabel('Normalised gain (dB)')
ax4.set_title('Radiation pattern (dB)\nvs angle from antenna axis', fontsize=10)
ax4.set_xlim(0, 180)
ax4.set_ylim(-40, 2)
ax4.axvline(x=90, color='gray', linestyle=':', linewidth=1, label='Broadside (max gain)')
ax4.legend(fontsize=8)
ax4.grid(True, alpha=0.3)

output_dir = Path(__file__).resolve().parent / "outputs"
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / "halfwave_dipole_915MHz.png"
plt.savefig(output_path, dpi=150, bbox_inches='tight')
plt.close()

print(f"\n{'=' * 60}")
print(f"  DESIGN SUMMARY")
print(f"{'=' * 60}")
print(f"  Frequency:          915 MHz")
print(f"  Total length:       {L_corrected_mm:.1f} mm  ({L_arm_mm:.1f} mm per arm)")
print(f"  Feed impedance:     73 Ω  (73 + j0 at resonance)")
print(f"  VSWR into 50 Ω:    {VSWR:.2f} : 1")
print(f"  Return loss:        {RL_dB:.1f} dB")
print(f"  Mismatch loss:      {mismatch_loss_dB:.3f} dB  (negligible)")
print(f"  Directivity:        {D0_dBi:.3f} dBi")
print(f"  Realised gain:      {G_realised_dBi:.3f} dBi")
print(f"  HPBW:               {HPBW:.1f}°")
print(f"  Effective length:   {le_mm:.1f} mm")
print(f"\n  Plot saved to: {output_path}")
print(f"{'=' * 60}")