"""
dipole_sim.py

Characterisation script for a 915 MHz half-wave dipole telemetry antenna
for SRAD rocket use.

References (APA):

Balanis, C. A. (2005). Antenna theory: Analysis and design (3rd ed.).
John Wiley & Sons.

Friis, H. T. (1946). A note on a simple transmission formula.
Proceedings of the IRE, 34(5), 254-256.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import constants as const


def dipole_field_power(theta_rad: np.ndarray | float) -> np.ndarray | float:
	"""Half-wave dipole normalised field power form from Balanis Eq 4-58a."""
	theta_safe_rad = np.clip(theta_rad, 0.001, np.pi - 0.001)
	numerator = np.cos((np.pi / 2.0) * np.cos(theta_safe_rad))
	denominator = np.sin(theta_safe_rad)
	return (numerator / denominator) ** 2


def main() -> None:
	# ============================================================
	# ANTENNA BUILD SPECIFICATIONS (fixed per requirement)
	# ============================================================
	f_hz = 915e6  # Hz
	f_mhz = f_hz / 1e6  # MHz
	wire_diameter_mm = 1.6  # mm
	vf = 0.95  # dimensionless
	z_sys_ohm = 50.0  # ohm
	feed_gap_mm = 10.0  # mm (maximum)

	# ============================================================
	# SECTION 1 — FUNDAMENTAL PARAMETERS
	# ============================================================
	c_mps = const.c  # m/s
	lambda_m = c_mps / f_hz  # m
	lambda_mm = lambda_m * 1e3  # mm
	k_rad_per_m = 2.0 * np.pi / lambda_m  # rad/m
	lambda_wire_m = lambda_m * vf  # m
	lambda_wire_mm = lambda_wire_m * 1e3  # mm

	print("=" * 60)
	print("SECTION 1 — FUNDAMENTAL PARAMETERS")
	print("=" * 60)
	print(f"Operating frequency: {f_mhz:.3f} MHz")
	print(f"Free space wavelength (lambda = c/f): {lambda_mm:.3f} mm")
	print(f"Wavenumber k = 2*pi/lambda: {k_rad_per_m:.6f} rad/m")
	print(f"Velocity factor (VF): {vf:.2f}")
	print(f"Corrected wavelength in wire (lambda_wire): {lambda_wire_mm:.3f} mm")
	print("Cite: Balanis 3rd ed. Chapter 2, Eq 2-1")
	print()

	# ============================================================
	# SECTION 2 — PHYSICAL ELEMENT DIMENSIONS
	# ============================================================
	l_ideal_m = lambda_m / 2.0  # m
	l_ideal_mm = l_ideal_m * 1e3  # mm
	l_total_m = l_ideal_m * vf  # m
	l_total_mm = l_total_m * 1e3  # mm
	l_arm_m = l_total_m / 2.0  # m
	l_arm_mm = l_arm_m * 1e3  # mm
	l_build_mm = l_arm_mm + 2.0  # mm

	print("=" * 60)
	print("SECTION 2 — PHYSICAL ELEMENT DIMENSIONS")
	print("=" * 60)
	print(f"{'Parameter':45s} {'Value'}")
	print("-" * 60)
	print(f"{'Ideal half wavelength (no VF correction)':45s} {l_ideal_mm:8.3f} mm")
	print(f"{'Corrected total length (VF applied)':45s} {l_total_mm:8.3f} mm")
	print(f"{'Length per arm':45s} {l_arm_mm:8.3f} mm")
	print(f"{'Recommended build length per arm':45s} {l_build_mm:8.3f} mm")
	print(f"{'Feed gap at centre (maximum)':45s} {feed_gap_mm:8.3f} mm")
	print("Cite: Balanis 3rd ed. Chapter 4, Section 4.6")
	print()

	# ============================================================
	# SECTION 3 — IMPEDANCE AND MATCHING
	# ============================================================
	z_in_ohm = 73.0 + 1j * 42.5  # ohm
	z_resonance_ohm = 73.0  # ohm (purely resistive)
	gamma = (z_resonance_ohm - z_sys_ohm) / (z_resonance_ohm + z_sys_ohm)  # dimensionless
	gamma_abs = np.abs(gamma)  # dimensionless
	vswr = (1.0 + gamma_abs) / (1.0 - gamma_abs)  # dimensionless
	rl_db = -20.0 * np.log10(gamma_abs)  # dB
	ml_db = -10.0 * np.log10(1.0 - gamma_abs**2)  # dB
	p_reflected_pct = gamma_abs**2 * 100.0  # %

	print("=" * 60)
	print("SECTION 3 — IMPEDANCE AND MATCHING")
	print("=" * 60)
	print(f"Theoretical Z_in at half-wave resonance (Balanis Eq 4-70): {z_in_ohm.real:.1f} + j{z_in_ohm.imag:.1f} Ohm")
	print(f"Resonant feed impedance (trimmed): {z_resonance_ohm:.1f} Ohm")
	print(f"System impedance: {z_sys_ohm:.1f} Ohm")
	print(f"Reflection coefficient Gamma (Eq 2-64): {gamma:.6f}")
	print(f"VSWR into 50 Ohm (Eq 2-68): {vswr:.3f}")
	print(f"Return loss RL (Eq 2-66): {rl_db:.3f} dB")
	print(f"Mismatch loss: {ml_db:.3f} dB")
	print(f"Power reflected: {p_reflected_pct:.3f} %")
	print("Note: no matching network required; mismatch loss is acceptable for SRAD telemetry.")
	print()

	# ============================================================
	# SECTION 4 — GAIN AND DIRECTIVITY
	# ============================================================
	d0_linear = 1.643  # dimensionless
	d0_dbi = 10.0 * np.log10(d0_linear)  # dBi
	rr_ohm = 73.0  # ohm
	r_loss_ohm = 0.3  # ohm
	e_cd = rr_ohm / (rr_ohm + r_loss_ohm)  # dimensionless
	e_cd_db = 10.0 * np.log10(e_cd)  # dB
	g0_linear = e_cd * d0_linear  # dimensionless
	g0_dbi = 10.0 * np.log10(g0_linear)  # dBi
	g_realised_linear = (1.0 - gamma_abs**2) * g0_linear  # dimensionless
	g_realised_dbi = 10.0 * np.log10(g_realised_linear)  # dBi
	le_m = (2.0 * lambda_m) / np.pi  # m
	le_mm = le_m * 1e3  # mm
	aem_m2 = (lambda_m**2 / (4.0 * np.pi)) * d0_linear  # m^2
	aem_cm2 = aem_m2 * 1e4  # cm^2

	print("=" * 60)
	print("SECTION 4 — GAIN AND DIRECTIVITY")
	print("=" * 60)
	print(f"Directivity D0 (Eq 4-69): {d0_linear:.3f} (dimensionless)")
	print(f"Directivity D0: {d0_dbi:.3f} dBi")
	print(f"Radiation resistance Rr (Eq 4-67): {rr_ohm:.3f} Ohm")
	print(f"Estimated ohmic loss resistance: {r_loss_ohm:.3f} Ohm")
	print(f"Radiation efficiency e_cd (Eq 2-90): {e_cd:.6f} ({e_cd*100:.3f} %) / {e_cd_db:.4f} dB")
	print(f"Gain including efficiency G0: {g0_linear:.6f} (linear) / {g0_dbi:.3f} dBi")
	print(f"Realised gain incl. mismatch (Eq 2-49b): {g_realised_linear:.6f} (linear) / {g_realised_dbi:.3f} dBi")
	print(f"Effective length le (Eq 4-59): {le_mm:.3f} mm")
	print(f"Effective aperture Aem (Eq 2-96): {aem_cm2:.3f} cm^2")
	print()

	# ============================================================
	# SECTION 5 — RADIATION PATTERN
	# ============================================================
	theta_rad = np.linspace(0.001, np.pi - 0.001, 3600)  # rad
	theta_deg = np.degrees(theta_rad)  # deg

	f_theta = dipole_field_power(theta_rad)  # linear power pattern
	f_max = np.max(f_theta)  # linear
	f_norm = f_theta / f_max  # linear normalised
	f_db = 10.0 * np.log10(f_norm + 1e-10)  # dB

	elevation_deg = 90.0 - theta_deg  # deg above horizon
	g_elevation_dbi = g0_dbi + 10.0 * np.log10(f_norm + 1e-10)  # dBi

	hp_idx = np.where(f_norm >= 0.5)[0]
	hp_theta_1_deg = theta_deg[hp_idx[0]]  # deg
	hp_theta_2_deg = theta_deg[hp_idx[-1]]  # deg
	hpbw_deg = hp_theta_2_deg - hp_theta_1_deg  # deg

	key_elevations_deg = np.array([0, 10, 20, 30, 45, 60, 75, 90], dtype=float)
	key_gains_dbi = []
	for elev_deg in key_elevations_deg:
		theta_key_rad = np.radians(90.0 - elev_deg)
		theta_key_rad = np.clip(theta_key_rad, 0.001, np.pi - 0.001)
		f_key = dipole_field_power(theta_key_rad)
		f_key_norm = f_key / f_max
		g_key_dbi = g0_dbi + 10.0 * np.log10(f_key_norm + 1e-10)
		key_gains_dbi.append(g_key_dbi)
	key_gains_dbi = np.array(key_gains_dbi)

	print("=" * 60)
	print("SECTION 5 — RADIATION PATTERN")
	print("=" * 60)
	print("Pattern model: F(theta) = [cos(pi/2*cos(theta))/sin(theta)]^2")
	print(f"Half-power beamwidth (HPBW): {hpbw_deg:.3f} deg")
	print("Cite: Balanis 3rd ed. Chapter 4")
	print("\nGain at key elevation angles:")
	print(f"{'Elevation (deg)':>16s} {'Gain (dBi)':>14s}")
	print("-" * 32)
	for elev_deg, gain_dbi in zip(key_elevations_deg, key_gains_dbi):
		print(f"{elev_deg:16.1f} {gain_dbi:14.3f}")
	print()

	# ============================================================
	# SECTION 6 — LINK BUDGET CONTRIBUTION
	# ============================================================
	p_tx_dbm = 22.0  # dBm
	g_dipole_dbi = g_realised_dbi  # dBi
	g_yagi_dbi = 10.0  # dBi
	l_cable_db = 1.0  # dB
	lm_min_db = 10.0  # dB
	sens_dbm = {
		"SF7": -124.0,
		"SF8": -127.0,
		"SF9": -130.0,
		"SF10": -133.0,
		"SF11": -136.0,
		"SF12": -139.0,
	}

	distances_m = np.array([500, 1000, 2000, 3000, 4000, 5000], dtype=float)  # m
	fspl_db = 20.0 * np.log10(4.0 * np.pi * distances_m / lambda_m)  # dB
	p_rx_dbm = p_tx_dbm + g_dipole_dbi + g_yagi_dbi - fspl_db - l_cable_db  # dBm
	lm_sf7_db = p_rx_dbm - sens_dbm["SF7"]  # dB
	lm_sf12_db = p_rx_dbm - sens_dbm["SF12"]  # dB

	print("=" * 60)
	print("SECTION 6 — LINK BUDGET CONTRIBUTION")
	print("=" * 60)
	print("Broadside link budget table (elevation = 0 deg):")
	print(f"{'Distance (m)':>12s} {'FSPL (dB)':>11s} {'P_rx (dBm)':>12s} {'LM_SF7':>10s} {'LM_SF12':>10s} {'SF7':>7s} {'SF12':>7s}")
	print("-" * 80)
	for d_m, fspl_i, prx_i, lm7_i, lm12_i in zip(distances_m, fspl_db, p_rx_dbm, lm_sf7_db, lm_sf12_db):
		sf7_pass = "PASS" if lm7_i >= lm_min_db else "FAIL"
		sf12_pass = "PASS" if lm12_i >= lm_min_db else "FAIL"
		print(f"{d_m:12.0f} {fspl_i:11.2f} {prx_i:12.2f} {lm7_i:10.2f} {lm12_i:10.2f} {sf7_pass:>7s} {sf12_pass:>7s}")

	apogee_alt_m = 3048.0  # m
	offsets_m = np.array([100.0, 300.0, 500.0])  # m
	apogee_rows = []
	for offset_m in offsets_m:
		slant_range_m = np.sqrt(apogee_alt_m**2 + offset_m**2)  # m
		elevation_angle_deg = np.degrees(np.arctan(apogee_alt_m / offset_m))  # deg
		theta_balanis_rad = np.radians(90.0 - elevation_angle_deg)  # rad
		theta_balanis_rad = np.clip(theta_balanis_rad, 0.001, np.pi - 0.001)  # rad
		f_apogee = dipole_field_power(theta_balanis_rad)  # linear
		f_apogee_norm = f_apogee / f_max  # linear
		g_apogee_dbi = g0_dbi + 10.0 * np.log10(f_apogee_norm + 1e-10)  # dBi
		fspl_apogee_db = 20.0 * np.log10(4.0 * np.pi * slant_range_m / lambda_m)  # dB
		p_rx_apogee_dbm = p_tx_dbm + g_apogee_dbi + g_yagi_dbi - fspl_apogee_db - l_cable_db  # dBm
		lm_apogee_sf7_db = p_rx_apogee_dbm - sens_dbm["SF7"]  # dB
		lm_apogee_sf12_db = p_rx_apogee_dbm - sens_dbm["SF12"]  # dB
		apogee_rows.append(
			{
				"offset_m": offset_m,
				"elev_deg": elevation_angle_deg,
				"g_dbi": g_apogee_dbi,
				"slant_m": slant_range_m,
				"fspl_db": fspl_apogee_db,
				"prx_dbm": p_rx_apogee_dbm,
				"lm7_db": lm_apogee_sf7_db,
				"lm12_db": lm_apogee_sf12_db,
			}
		)

	print("\nApogee geometry and link margin table:")
	print(f"{'Offset (m)':>10s} {'Elev (deg)':>11s} {'Dipole G (dBi)':>15s} {'Slant (m)':>11s} {'FSPL (dB)':>11s} {'P_rx (dBm)':>12s} {'LM_SF7':>10s} {'LM_SF12':>10s}")
	print("-" * 100)
	for row in apogee_rows:
		print(
			f"{row['offset_m']:10.0f} {row['elev_deg']:11.3f} {row['g_dbi']:15.3f} "
			f"{row['slant_m']:11.2f} {row['fspl_db']:11.2f} {row['prx_dbm']:12.2f} "
			f"{row['lm7_db']:10.2f} {row['lm12_db']:10.2f}"
		)
	print("\nCite: Friis 1946; Balanis 3rd ed. Eq 4-58a")
	print()

	# ============================================================
	# SECTION 7 — SUMMARY TABLE
	# ============================================================
	print("=" * 60)
	print("SECTION 7 — SUMMARY TABLE")
	print("=" * 60)
	print("Physical dimensions:")
	print(f"- Operating frequency: {f_mhz:.3f} MHz")
	print(f"- Free space wavelength: {lambda_mm:.3f} mm")
	print(f"- Velocity factor: {vf:.2f}")
	print(f"- Corrected total length: {l_total_mm:.3f} mm")
	print(f"- Length per arm: {l_arm_mm:.3f} mm")
	print(f"- Recommended build length per arm: {l_build_mm:.3f} mm")
	print(f"- Feed gap: {feed_gap_mm:.3f} mm")
	print(f"- Wire diameter: {wire_diameter_mm:.3f} mm")

	print("\nImpedance and matching:")
	print(f"- Feed impedance at resonance: {z_resonance_ohm:.3f} Ohm")
	print(f"- System impedance: {z_sys_ohm:.3f} Ohm")
	print(f"- VSWR into 50 Ohm: {vswr:.3f}")
	print(f"- Return loss: {rl_db:.3f} dB")
	print(f"- Mismatch loss: {ml_db:.3f} dB")
	print(f"- Power reflected: {p_reflected_pct:.3f} %")
	print("- Matching network required: No")

	print("\nPerformance:")
	print(f"- Directivity: {d0_dbi:.3f} dBi")
	print(f"- Radiation resistance: {rr_ohm:.3f} Ohm")
	print(f"- Radiation efficiency: {e_cd*100.0:.3f} %")
	print(f"- Gain including efficiency: {g0_dbi:.3f} dBi")
	print(f"- Realised gain including mismatch: {g_realised_dbi:.3f} dBi")
	print(f"- Effective length: {le_mm:.3f} mm")
	print(f"- Effective aperture: {aem_cm2:.3f} cm^2")
	print(f"- Half power beamwidth: {hpbw_deg:.3f} degrees")

	print("\nGain vs elevation angle table:")
	print(f"{'Elevation (deg)':>16s} {'Gain (dBi)':>14s}")
	print("-" * 32)
	for elev_deg, gain_dbi in zip(key_elevations_deg, key_gains_dbi):
		print(f"{elev_deg:16.1f} {gain_dbi:14.3f}")

	print("\nApogee link margin table:")
	print(f"{'Offset (m)':>10s} {'Elev (deg)':>11s} {'Dipole G (dBi)':>15s} {'LM_SF7 (dB)':>12s} {'LM_SF12 (dB)':>13s}")
	print("-" * 70)
	for row in apogee_rows:
		print(f"{row['offset_m']:10.0f} {row['elev_deg']:11.3f} {row['g_dbi']:15.3f} {row['lm7_db']:12.3f} {row['lm12_db']:13.3f}")
	print()

	# ============================================================
	# SECTION 8 — PLOTS
	# ============================================================
	plt.rcParams.update({"font.size": 11})

	# Plot 1 — Physical antenna diagram
	fig1, ax1 = plt.subplots(figsize=(10, 4))
	ax1.set_facecolor("white")

	arm_len = l_build_mm  # mm
	gap = feed_gap_mm  # mm
	left_end = -(gap / 2.0 + arm_len)  # mm
	left_feed = -gap / 2.0  # mm
	right_feed = gap / 2.0  # mm
	right_end = gap / 2.0 + arm_len  # mm

	coax_drop_mm = 120.0  # mm
	ferrite_from_feed_mm = 20.0  # mm
	ferrite_y = -ferrite_from_feed_mm  # mm
	ufl_y = -coax_drop_mm  # mm

	ax1.plot([left_end, left_feed], [0, 0], color="#B87333", linewidth=4)
	ax1.plot([right_feed, right_end], [0, 0], color="#B87333", linewidth=4)
	ax1.plot([0, 0], [0, ufl_y], color="#3D3D3D", linewidth=3)

	ferrite_w = 10.0
	ferrite_h = 8.0
	ax1.add_patch(
		plt.Rectangle(
			(-ferrite_w / 2.0, ferrite_y - ferrite_h / 2.0),
			ferrite_w,
			ferrite_h,
			color="#2C2C2C",
		)
	)

	ax1.add_patch(
		plt.Rectangle(
			(-7.0, ufl_y - 6.0),
			14.0,
			8.0,
			color="#CFB53B",
		)
	)

	total_span_mm = 2.0 * arm_len + gap
	ax1.annotate("", xy=(left_end, 18), xytext=(left_feed, 18), arrowprops=dict(arrowstyle="<->"))
	ax1.text((left_end + left_feed) / 2.0, 22, f"Arm length = {arm_len:.2f} mm", ha="center")
	ax1.annotate("", xy=(right_feed, 18), xytext=(right_end, 18), arrowprops=dict(arrowstyle="<->"))
	ax1.text((right_feed + right_end) / 2.0, 22, f"Arm length = {arm_len:.2f} mm", ha="center")
	ax1.annotate("", xy=(left_end, 35), xytext=(right_end, 35), arrowprops=dict(arrowstyle="<->"))
	ax1.text(0, 39, f"Total span = {total_span_mm:.2f} mm", ha="center")
	ax1.annotate("", xy=(left_feed, -10), xytext=(right_feed, -10), arrowprops=dict(arrowstyle="<->"))
	ax1.text(0, -15, f"Feed gap = {gap:.2f} mm", ha="center")
	ax1.text(8, ferrite_y, f"Ferrite = {ferrite_from_feed_mm:.1f} mm from feed", va="center")
	ax1.text(8, ufl_y - 2, "U.FL connector", va="center")
	ax1.text(8, ufl_y / 2.0, f"Coax length = {coax_drop_mm:.1f} mm", va="center")

	ax1.set_xlim(left_end - 25, right_end + 25)
	ax1.set_ylim(ufl_y - 20, 50)
	ax1.axis("off")
	ax1.set_title("Half Wave Dipole — 915 MHz — Physical Assembly")
	fig1.savefig("dipole_physical_diagram.png", dpi=1200, bbox_inches="tight")

	# Plot 2 — Polar radiation pattern (full 0..360 deg mirrored)
	phi_rad = np.linspace(0.0, 2.0 * np.pi, 3600)
	theta_equiv_rad = np.where(phi_rad <= np.pi, phi_rad, 2.0 * np.pi - phi_rad)
	theta_equiv_rad = np.clip(theta_equiv_rad, 0.001, np.pi - 0.001)
	f_full = dipole_field_power(theta_equiv_rad)
	f_full_norm = f_full / f_max
	f_full_db = 10.0 * np.log10(f_full_norm + 1e-10)
	f_full_db = np.maximum(f_full_db, -40.0)

	fig2 = plt.figure(figsize=(7, 7))
	ax2 = fig2.add_subplot(111, projection="polar")
	ax2.set_facecolor("white")
	ax2.plot(phi_rad, f_full_db, linewidth=1.8)
	ax2.set_rlim(-40, 0)
	ax2.set_rticks([-40, -30, -20, -10, 0])

	ax2.plot([np.radians(hp_theta_1_deg), np.radians(hp_theta_1_deg)], [-40, 0], "k--", linewidth=1)
	ax2.plot([np.radians(hp_theta_2_deg), np.radians(hp_theta_2_deg)], [-40, 0], "k--", linewidth=1)
	ax2.plot([np.radians(180.0 + hp_theta_1_deg), np.radians(180.0 + hp_theta_1_deg)], [-40, 0], "k--", linewidth=1)
	ax2.plot([np.radians(180.0 + hp_theta_2_deg), np.radians(180.0 + hp_theta_2_deg)], [-40, 0], "k--", linewidth=1)

	ax2.text(0.0, -3.0, "Null (axis)", ha="center")
	ax2.text(np.pi, -3.0, "Null (axis)", ha="center")
	ax2.text(np.pi / 2.0, -2.0, "Max (broadside)", ha="center")
	ax2.set_title("Half Wave Dipole — Radiation Pattern (Balanis Eq 4-58a)")
	fig2.savefig("dipole_radiation_pattern.png", dpi=1200, bbox_inches="tight")

	# Plot 3 — Gain vs elevation angle
	elev_plot_deg = np.linspace(0.0, 90.0, 901)
	theta_plot_rad = np.radians(90.0 - elev_plot_deg)
	theta_plot_rad = np.clip(theta_plot_rad, 0.001, np.pi - 0.001)
	f_plot = dipole_field_power(theta_plot_rad)
	f_plot_norm = f_plot / f_max
	g_plot_dbi = g0_dbi + 10.0 * np.log10(f_plot_norm + 1e-10)

	fig3, ax3 = plt.subplots(figsize=(8, 4.8))
	ax3.set_facecolor("white")
	ax3.plot(elev_plot_deg, g_plot_dbi, linewidth=2.0)
	ax3.axhline(0.0, linestyle="--", color="gray", linewidth=1)
	ax3.axhline(2.15, linestyle="--", color="black", linewidth=1)

	for row in apogee_rows:
		x = row["elev_deg"]
		y = row["g_dbi"]
		ax3.axvline(x, linestyle="--", color="tab:red", linewidth=1)
		ax3.scatter([x], [y], color="tab:red", s=24)
		ax3.text(x + 0.5, y, f"{int(row['offset_m'])} m: {y:.2f} dBi", fontsize=9)

	ax3.set_xlabel("Elevation angle above horizon (deg)")
	ax3.set_ylabel("Dipole gain (dBi)")
	ax3.set_title("Dipole Gain vs Elevation Angle — Impact on Link Margin at Apogee")
	fig3.savefig("dipole_gain_vs_elevation.png", dpi=1200, bbox_inches="tight")

	# Plot 4 — Link margin vs range at broadside
	range_plot_m = np.linspace(100.0, 6000.0, 400)
	fspl_range_db = 20.0 * np.log10(4.0 * np.pi * range_plot_m / lambda_m)
	p_rx_range_dbm = p_tx_dbm + g_dipole_dbi + g_yagi_dbi - fspl_range_db - l_cable_db

	fig4, ax4 = plt.subplots(figsize=(9, 5))
	ax4.set_facecolor("white")
	y_min, y_max = -40.0, 100.0
	ax4.fill_between(range_plot_m, y_min, lm_min_db, color="lightcoral", alpha=0.25)
	ax4.fill_between(range_plot_m, lm_min_db, y_max, color="lightgreen", alpha=0.20)

	sf_order = ["SF7", "SF8", "SF9", "SF10", "SF11", "SF12"]
	for sf in sf_order:
		lm_sf = p_rx_range_dbm - sens_dbm[sf]
		ax4.plot(range_plot_m, lm_sf, label=sf)

	ax4.axhline(lm_min_db, linestyle="--", color="red", linewidth=1.5)
	ax4.axvline(3048.0, linestyle="--", color="black", linewidth=1)
	ax4.set_ylim(y_min, y_max)
	ax4.set_xlabel("Range (m)")
	ax4.set_ylabel("Link Margin (dB)")
	ax4.set_title("Link Margin vs Range — Half Wave Dipole Rocket Antenna, 10 dBi Yagi Ground Station")
	ax4.legend(loc="best")
	fig4.savefig("dipole_link_margin.png", dpi=1200, bbox_inches="tight")

	# Plot 5 — Apogee link margin vs ground station offset
	offset_plot_m = np.linspace(50.0, 600.0, 551)
	slant_plot_m = np.sqrt(apogee_alt_m**2 + offset_plot_m**2)
	elev_plot_apogee_deg = np.degrees(np.arctan(apogee_alt_m / offset_plot_m))
	theta_plot_apogee_rad = np.radians(90.0 - elev_plot_apogee_deg)
	theta_plot_apogee_rad = np.clip(theta_plot_apogee_rad, 0.001, np.pi - 0.001)
	f_apogee_plot = dipole_field_power(theta_plot_apogee_rad)
	f_apogee_plot_norm = f_apogee_plot / f_max
	g_apogee_plot_dbi = g0_dbi + 10.0 * np.log10(f_apogee_plot_norm + 1e-10)
	fspl_apogee_plot_db = 20.0 * np.log10(4.0 * np.pi * slant_plot_m / lambda_m)
	p_rx_apogee_plot_dbm = p_tx_dbm + g_apogee_plot_dbi + g_yagi_dbi - fspl_apogee_plot_db - l_cable_db
	lm_apogee_plot_sf7 = p_rx_apogee_plot_dbm - sens_dbm["SF7"]
	lm_apogee_plot_sf12 = p_rx_apogee_plot_dbm - sens_dbm["SF12"]

	fig5, ax5 = plt.subplots(figsize=(9, 5))
	ax5.set_facecolor("white")
	ax5.plot(offset_plot_m, lm_apogee_plot_sf7, label="SF7", linewidth=2)
	ax5.plot(offset_plot_m, lm_apogee_plot_sf12, label="SF12", linewidth=2)
	ax5.axhline(lm_min_db, linestyle="--", color="red", linewidth=1.5)

	for row in apogee_rows:
		x = row["offset_m"]
		ax5.axvline(x, linestyle="--", color="black", linewidth=1)
		ax5.text(x + 5, row["lm7_db"], f"SF7 {row['lm7_db']:.1f} dB", fontsize=9)
		ax5.text(x + 5, row["lm12_db"], f"SF12 {row['lm12_db']:.1f} dB", fontsize=9)

	ax5.set_xlabel("Ground station offset at apogee (m)")
	ax5.set_ylabel("Link Margin (dB)")
	ax5.set_title("Link Margin at Apogee vs Ground Station Offset")
	ax5.legend(loc="best")
	fig5.savefig("dipole_apogee_margin.png", dpi=1200, bbox_inches="tight")

	plt.show(block=False)
	input("Press Enter to close plots...")


if __name__ == "__main__":
	main()
