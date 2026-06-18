"""
Rocket 1/4-wave monopole flight loss simulation (915 MHz example)
-----------------------------------------------------------------
What this sim does:
1) Builds a simple rocket flight profile (altitude + downrange vs time)
2) Computes RF loss terms for each time step
3) Reports best/worst/average losses and optional link margin
4) Plots results (if matplotlib is installed)

Main RF loss terms included:
- Free-space path loss (FSPL)
- Feedline/coax loss (TX side)
- Mismatch loss (from VSWR and optional detuning)
- Polarization mismatch loss
- Monopole pattern/pointing loss vs elevation angle
- Extra user-defined implementation loss

All important variables are grouped in the CONFIG section so you can
quickly change assumptions and see how results move.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, List


# -----------------------------
# CONFIG: change these values
# -----------------------------

@dataclass
class SimConfig:
	# RF / antenna
	frequency_hz: float = 915e6
	monopole_length_m: float = 78e-3   # 78 mm (includes your correction factor)
	monopole_5_8_length_m: float = 205e-3  # 5/8-wave monopole length
	monopole_3_4_length_m: float = 246e-3  # 3/4-wave monopole length
	dipole_length_m: float = 160e-3    # total tip-to-tip length for 1/2-wave dipole
	velocity_factor: float = 1.0       # 1.0 in free-space; use <1 for insulated/loaded wire

	# Basic TX/RX parameters for optional link-margin view
	tx_power_dbm: float = 20.0         # e.g., 100 mW telemetry TX
	rx_antenna_gain_dbi: float = 5.0   # ground station antenna gain
	rx_sensitivity_dbm: float = -110.0 # receiver sensitivity threshold

	# Monopole performance assumptions
	monopole_peak_gain_dbi: float = 2.0    # realistic installed gain (adjust from test data)
	monopole_5_8_peak_gain_dbi: float = 3.0
	monopole_3_4_peak_gain_dbi: float = 3.5
	pattern_exponent: float = 2.0          # how sharp the null is; 1.5..4 are common approximations
	antenna_cant_deg: float = 10.0         # intentional tilt from rocket axis (helps zenith null)

	# Dipole performance assumptions
	dipole_peak_gain_dbi: float = 2.15      # ideal half-wave dipole broadside gain
	dipole_implementation_loss_db: float = 1.0
    
	# Conformal patch array assumptions (simplified elevation-pattern model)
	conformal_patch_array_peak_gain_dbi: float = 8.0
	conformal_patch_array_resonant_freq_hz: float = 915e6
	conformal_patch_array_implementation_loss_db: float = 2.0
	conformal_patch_array_boresight_elevation_deg: float = 20.0
	conformal_patch_array_hpbw_deg: float = 60.0
	conformal_patch_array_sidelobe_floor_db: float = 18.0

	# Loss assumptions
	coax_loss_db_per_m: float = 0.6    # depends on cable type at 915 MHz
	coax_length_m: float = 0.3
	static_vswr: float = 1.5           # measured/assumed VSWR in flight config
	use_detuning_model: bool = True
	loaded_q: float = 15.0             # higher Q => more sensitivity to detuning
	polarization_mismatch_deg: float = 10.0  # angle between TX/RX polarization vectors
	implementation_loss_db: float = 1.5      # connectors, radome, vibration, body effects, etc.

	# Ground station geometry and simple flight model
	gs_height_m: float = 1.0
	launch_site_offset_m: float = 100.0  # GS horizontal distance from pad at t=0
	wind_speed_mps: float = 8.0          # horizontal drift from wind

	# Flight profile (piecewise linear altitude model)
	t_burn_s: float = 4.0
	t_coast_s: float = 10.0
	t_descent_s: float = 140.0
	burnout_alt_m: float = 900.0
	apogee_alt_m: float = 3000.0

	# Simulation resolution
	dt_s: float = 0.5


# -----------------------------
# Core RF helper calculations
# -----------------------------

def quarter_wave_length_m(frequency_hz: float, velocity_factor: float = 1.0) -> float:
	"""Physical quarter-wave length: L = (c/f)/4 * VF"""
	c = 299_792_458.0
	return (c / frequency_hz) * 0.25 * velocity_factor


def half_wave_length_m(frequency_hz: float, velocity_factor: float = 1.0) -> float:
	"""Physical half-wave length: L = (c/f)/2 * VF"""
	c = 299_792_458.0
	return (c / frequency_hz) * 0.5 * velocity_factor


def fractional_wave_length_m(frequency_hz: float, fraction: float, velocity_factor: float = 1.0) -> float:
	"""Physical fractional-wave length: L = (c/f)*fraction*VF"""
	c = 299_792_458.0
	return (c / frequency_hz) * fraction * velocity_factor


def get_antenna_params(cfg: SimConfig, antenna_type: str) -> Dict[str, float | str]:
	"""Return per-antenna parameters for simulation and reporting."""
	if antenna_type == "conformal_patch_array":
		return {
			"physical_length_m": 0.0,
			"wave_fraction": 0.0,
			"peak_gain_dbi": cfg.conformal_patch_array_peak_gain_dbi,
			"impl_loss_db": cfg.conformal_patch_array_implementation_loss_db,
			"resonant_frequency_hz": cfg.conformal_patch_array_resonant_freq_hz,
			"title": "CONFORMAL PATCH ARRAY",
		}
	if antenna_type == "dipole":
		return {
			"physical_length_m": cfg.dipole_length_m,
			"wave_fraction": 0.5,
			"peak_gain_dbi": cfg.dipole_peak_gain_dbi,
			"impl_loss_db": cfg.dipole_implementation_loss_db,
			"title": "HALF-WAVE DIPOLE",
		}
	if antenna_type == "monopole_5_8":
		return {
			"physical_length_m": cfg.monopole_5_8_length_m,
			"wave_fraction": 0.625,
			"peak_gain_dbi": cfg.monopole_5_8_peak_gain_dbi,
			"impl_loss_db": cfg.implementation_loss_db,
			"title": "5/8-WAVE MONOPOLE",
		}
	if antenna_type == "monopole_3_4":
		return {
			"physical_length_m": cfg.monopole_3_4_length_m,
			"wave_fraction": 0.75,
			"peak_gain_dbi": cfg.monopole_3_4_peak_gain_dbi,
			"impl_loss_db": cfg.implementation_loss_db,
			"title": "3/4-WAVE MONOPOLE",
		}
	return {
		"physical_length_m": cfg.monopole_length_m,
		"wave_fraction": 0.25,
		"peak_gain_dbi": cfg.monopole_peak_gain_dbi,
		"impl_loss_db": cfg.implementation_loss_db,
		"title": "QUARTER-WAVE MONOPOLE",
	}


def mismatch_loss_db_from_vswr(vswr: float) -> float:
	"""Mismatch loss from VSWR using reflection coefficient Gamma."""
	if vswr <= 1.0:
		return 0.0
	gamma = (vswr - 1.0) / (vswr + 1.0)
	accepted_power_ratio = 1.0 - gamma**2
	return -10.0 * math.log10(max(accepted_power_ratio, 1e-12))


def detuning_extra_mismatch_db(f_oper_hz: float, f_res_hz: float, loaded_q: float) -> float:
	"""
	Approximate extra mismatch due to operating away from resonance.

	Model notes:
	- Assume tuned at resonance to near 50 ohm resistive.
	- Off resonance, normalized reactance estimate:
		x = 2Q * (f/f0 - f0/f)
	- Use Z = 50 + j(50*x), then compute reflection coefficient to 50-ohm source.
	"""
	if f_res_hz <= 0 or loaded_q <= 0:
		return 0.0

	x = 2.0 * loaded_q * ((f_oper_hz / f_res_hz) - (f_res_hz / f_oper_hz))
	z_real = 50.0
	z_imag = 50.0 * x
	# Gamma = (Z - 50) / (Z + 50)
	num = complex(z_real - 50.0, z_imag)
	den = complex(z_real + 50.0, z_imag)
	gamma = abs(num / den)
	accepted_power_ratio = max(1.0 - gamma**2, 1e-12)
	return -10.0 * math.log10(accepted_power_ratio)


def fspl_db(frequency_hz: float, range_m: float) -> float:
	"""Free-space path loss in dB: 20log10(4*pi*d/lambda)."""
	if range_m <= 0:
		return 0.0
	c = 299_792_458.0
	wavelength_m = c / frequency_hz
	return 20.0 * math.log10(4.0 * math.pi * range_m / wavelength_m)


def polarization_loss_db(angle_deg: float) -> float:
	"""Power coupling for linear polarization mismatch: cos^2(theta)."""
	theta = math.radians(angle_deg)
	coupling = max(math.cos(theta) ** 2, 1e-12)
	return -10.0 * math.log10(coupling)


def monopole_pattern_loss_db(elevation_deg: float, cant_deg: float, exponent: float) -> float:
	"""
	Monopole pattern approximation.

	A vertical monopole has a zenith null. We approximate power pattern with:
		P(theta) ∝ sin(theta)^n
	where theta = angle between antenna axis and line-of-sight.

	Geometry approximation used here:
	- Rocket axis assumed vertical.
	- LOS elevation (from ground station) is `elevation_deg`.
	- theta ~= 90 - elevation + cant
	"""
	theta_deg = 90.0 - elevation_deg + cant_deg
	theta_deg = max(0.0, min(180.0, theta_deg))
	theta = math.radians(theta_deg)

	relative_power = max(math.sin(theta) ** exponent, 1e-12)
	return -10.0 * math.log10(relative_power)


def dipole_pattern_loss_db(elevation_deg: float, cant_deg: float) -> float:
	"""
	Half-wave dipole power pattern approximation.

	Power pattern for a center-fed half-wave dipole:
		P(theta) ∝ [cos((pi/2)cos(theta)) / sin(theta)]^2
	where theta is angle between dipole axis and line-of-sight.
	"""
	theta_deg = 90.0 - elevation_deg + cant_deg
	theta_deg = max(0.0, min(180.0, theta_deg))
	theta = math.radians(theta_deg)

	sin_t = abs(math.sin(theta))
	if sin_t < 1e-6:
		relative_power = 0.0
	else:
		relative_field = math.cos((math.pi / 2.0) * math.cos(theta)) / sin_t
		relative_power = relative_field**2

	relative_power = max(relative_power, 1e-12)
	return -10.0 * math.log10(relative_power)


def conformal_patch_array_pattern_loss_db(
	elevation_deg: float,
	boresight_elevation_deg: float,
	hpbw_deg: float,
	sidelobe_floor_db: float,
) -> float:
	"""
	Simplified conformal patch-array elevation pattern.

	Model:
	- Main lobe centered at `boresight_elevation_deg`.
	- Cosine-power rolloff derived from HPBW.
	- Minimum relative power is bounded by sidelobe floor.
	"""
	half_bw = max(hpbw_deg * 0.5, 1e-6)
	cos_half = max(math.cos(math.radians(min(half_bw, 89.9))), 1e-6)
	n = math.log(0.5) / math.log(cos_half)

	delta = abs(elevation_deg - boresight_elevation_deg)
	delta = min(delta, 90.0)

	relative_power = max(math.cos(math.radians(delta)) ** n, 0.0)
	floor_power = 10.0 ** (-max(sidelobe_floor_db, 0.0) / 10.0)
	relative_power = max(relative_power, floor_power, 1e-12)
	return -10.0 * math.log10(relative_power)


# -----------------------------
# Flight profile model
# -----------------------------

def altitude_profile_m(t_s: float, cfg: SimConfig) -> float:
	"""
	Piecewise-linear altitude profile:
	- Burn: 0 -> burnout_alt
	- Coast: burnout_alt -> apogee_alt
	- Descent: apogee_alt -> 0
	"""
	if t_s <= cfg.t_burn_s:
		return cfg.burnout_alt_m * (t_s / cfg.t_burn_s)

	t2 = cfg.t_burn_s + cfg.t_coast_s
	if t_s <= t2:
		return cfg.burnout_alt_m + (cfg.apogee_alt_m - cfg.burnout_alt_m) * ((t_s - cfg.t_burn_s) / cfg.t_coast_s)

	t3 = t2 + cfg.t_descent_s
	if t_s <= t3:
		return cfg.apogee_alt_m * (1.0 - (t_s - t2) / cfg.t_descent_s)

	return 0.0


def run_simulation(cfg: SimConfig, antenna_type: str = "monopole") -> List[Dict[str, float]]:
	# Resonance check from physical length
	# f_res ~= c * fraction / L_eff
	c = 299_792_458.0
	params = get_antenna_params(cfg, antenna_type)
	physical_length_m = float(params["physical_length_m"])
	wave_fraction = float(params["wave_fraction"])
	peak_gain_dbi = float(params["peak_gain_dbi"])
	impl_loss_db = float(params["impl_loss_db"])

	if "resonant_frequency_hz" in params:
		f_res_hz = float(params["resonant_frequency_hz"])
	else:
		l_eff = physical_length_m / max(cfg.velocity_factor, 1e-9)
		f_res_hz = c * wave_fraction / l_eff

	coax_loss_db = cfg.coax_loss_db_per_m * cfg.coax_length_m
	mismatch_static_db = mismatch_loss_db_from_vswr(cfg.static_vswr)
	mismatch_detune_db = (
		detuning_extra_mismatch_db(cfg.frequency_hz, f_res_hz, cfg.loaded_q)
		if cfg.use_detuning_model
		else 0.0
	)
	pol_loss_db = polarization_loss_db(cfg.polarization_mismatch_deg)

	total_time_s = cfg.t_burn_s + cfg.t_coast_s + cfg.t_descent_s
	steps = int(total_time_s / cfg.dt_s) + 1

	rows: List[Dict[str, float]] = []
	for i in range(steps):
		t = i * cfg.dt_s
		alt = altitude_profile_m(t, cfg)

		# Horizontal range from GS to rocket: initial offset + wind drift
		downrange = cfg.launch_site_offset_m + cfg.wind_speed_mps * t

		vertical = max(alt - cfg.gs_height_m, 0.0)
		slant_range = math.hypot(downrange, vertical)
		elevation_deg = math.degrees(math.atan2(vertical, downrange if downrange > 0 else 1e-9))

		fspl = fspl_db(cfg.frequency_hz, slant_range)
		if antenna_type == "dipole":
			patt_loss = dipole_pattern_loss_db(elevation_deg, cfg.antenna_cant_deg)
		elif antenna_type == "conformal_patch_array":
			patt_loss = conformal_patch_array_pattern_loss_db(
				elevation_deg,
				cfg.conformal_patch_array_boresight_elevation_deg,
				cfg.conformal_patch_array_hpbw_deg,
				cfg.conformal_patch_array_sidelobe_floor_db,
			)
		else:
			patt_loss = monopole_pattern_loss_db(elevation_deg, cfg.antenna_cant_deg, cfg.pattern_exponent)

		tx_antenna_effective_gain = peak_gain_dbi - patt_loss
		total_losses_db = fspl + coax_loss_db + mismatch_static_db + mismatch_detune_db + pol_loss_db + impl_loss_db + patt_loss

		# Received power estimate (optional, but very useful for go/no-go margin)
		rx_power_dbm = (
			cfg.tx_power_dbm
			+ tx_antenna_effective_gain
			+ cfg.rx_antenna_gain_dbi
			- fspl
			- coax_loss_db
			- mismatch_static_db
			- mismatch_detune_db
			- pol_loss_db
			- impl_loss_db
		)
		link_margin_db = rx_power_dbm - cfg.rx_sensitivity_dbm

		rows.append(
			{
				"t_s": t,
				"alt_m": alt,
				"downrange_m": downrange,
				"range_m": slant_range,
				"elevation_deg": elevation_deg,
				"fspl_db": fspl,
				"pattern_loss_db": patt_loss,
				"coax_loss_db": coax_loss_db,
				"mismatch_vswr_db": mismatch_static_db,
				"mismatch_detune_db": mismatch_detune_db,
				"polarization_loss_db": pol_loss_db,
				"implementation_loss_db": impl_loss_db,
				"total_loss_db": total_losses_db,
				"rx_power_dbm": rx_power_dbm,
				"link_margin_db": link_margin_db,
				"peak_gain_dbi": peak_gain_dbi,
			}
		)

	return rows


def print_summary(cfg: SimConfig, rows: List[Dict[str, float]], antenna_type: str) -> None:
	losses = [r["total_loss_db"] for r in rows]
	margins = [r["link_margin_db"] for r in rows]
	rx = [r["rx_power_dbm"] for r in rows]

	min_loss = min(losses)
	max_loss = max(losses)
	avg_loss = sum(losses) / len(losses)

	min_margin = min(margins)
	max_margin = max(margins)
	avg_margin = sum(margins) / len(margins)

	# Quarter-wave and resonance breakdown
	ideal_l_q_m = quarter_wave_length_m(cfg.frequency_hz, cfg.velocity_factor)
	ideal_l_h_m = half_wave_length_m(cfg.frequency_hz, cfg.velocity_factor)
	ideal_l_5_8_m = fractional_wave_length_m(cfg.frequency_hz, 0.625, cfg.velocity_factor)
	ideal_l_3_4_m = fractional_wave_length_m(cfg.frequency_hz, 0.75, cfg.velocity_factor)
	c = 299_792_458.0
	params = get_antenna_params(cfg, antenna_type)
	length_m = float(params["physical_length_m"])
	wave_fraction = float(params["wave_fraction"])
	title = str(params["title"])
	if "resonant_frequency_hz" in params:
		f_res_hz = float(params["resonant_frequency_hz"])
	else:
		f_res_hz = c * wave_fraction / (length_m / max(cfg.velocity_factor, 1e-9))

	if antenna_type == "dipole":
		ideal_length_m = ideal_l_h_m
	elif antenna_type == "monopole_5_8":
		ideal_length_m = ideal_l_5_8_m
	elif antenna_type == "monopole_3_4":
		ideal_length_m = ideal_l_3_4_m
	else:
		ideal_length_m = ideal_l_q_m

	print("=" * 72)
	print(f"ROCKET TELEMETRY LOSS SIM SUMMARY ({title})")
	print("=" * 72)
	print(f"Operating frequency: {cfg.frequency_hz/1e6:.3f} MHz")
	print(f"Ideal 1/4-wave length (@VF={cfg.velocity_factor:.3f}): {ideal_l_q_m*1e3:.2f} mm")
	print(f"Ideal 1/2-wave length (@VF={cfg.velocity_factor:.3f}): {ideal_l_h_m*1e3:.2f} mm")
	print(f"Ideal 5/8-wave length (@VF={cfg.velocity_factor:.3f}): {ideal_l_5_8_m*1e3:.2f} mm")
	print(f"Ideal 3/4-wave length (@VF={cfg.velocity_factor:.3f}): {ideal_l_3_4_m*1e3:.2f} mm")
	if antenna_type == "conformal_patch_array":
		print("Configured antenna length: N/A (array geometry model)")
	else:
		print(f"Configured antenna length: {length_m*1e3:.2f} mm")
	print(f"Estimated resonance: {f_res_hz/1e6:.3f} MHz")
	if antenna_type == "conformal_patch_array":
		print("Length error vs ideal: N/A")
	else:
		print(f"Length error vs ideal: {(length_m-ideal_length_m)*1e3:+.2f} mm")
	print("-" * 72)
	print(f"Total loss (best / avg / worst): {min_loss:.2f} / {avg_loss:.2f} / {max_loss:.2f} dB")
	print(f"Rx power   (best / avg / worst): {max(rx):.2f} / {sum(rx)/len(rx):.2f} / {min(rx):.2f} dBm")
	print(f"Margin     (best / avg / worst): {max_margin:.2f} / {avg_margin:.2f} / {min_margin:.2f} dB")

	worst = max(rows, key=lambda r: r["total_loss_db"])
	print("-" * 72)
	print("Worst-point breakdown:")
	print(f"Time = {worst['t_s']:.1f} s | Alt = {worst['alt_m']:.1f} m | Range = {worst['range_m']:.1f} m")
	print(f"FSPL                 : {worst['fspl_db']:.2f} dB")
	print(f"Pattern loss         : {worst['pattern_loss_db']:.2f} dB")
	print(f"Coax loss            : {worst['coax_loss_db']:.2f} dB")
	print(f"Mismatch (VSWR)      : {worst['mismatch_vswr_db']:.2f} dB")
	print(f"Mismatch (detuning)  : {worst['mismatch_detune_db']:.2f} dB")
	print(f"Polarization loss    : {worst['polarization_loss_db']:.2f} dB")
	print(f"Implementation loss  : {worst['implementation_loss_db']:.2f} dB")
	print(f"TOTAL LOSS           : {worst['total_loss_db']:.2f} dB")
	print(f"Rx power             : {worst['rx_power_dbm']:.2f} dBm")
	print(f"Link margin          : {worst['link_margin_db']:.2f} dB")
	print("=" * 72)


def print_comparison(rows_by_type: Dict[str, List[Dict[str, float]]], baseline_type: str = "monopole") -> None:
	baseline_rows = rows_by_type[baseline_type]
	base_losses = [r["total_loss_db"] for r in baseline_rows]
	base_margin = [r["link_margin_db"] for r in baseline_rows]
	labels = {
		"monopole": "1/4-wave monopole",
		"monopole_5_8": "5/8-wave monopole",
		"monopole_3_4": "3/4-wave monopole",
		"dipole": "1/2-wave dipole",
		"conformal_patch_array": "conformal patch array",
	}

	print("COMPARISON (vs 1/4-wave monopole baseline)")
	print("-" * 72)
	for antenna_type, rows in rows_by_type.items():
		if antenna_type == baseline_type:
			continue
		losses = [r["total_loss_db"] for r in rows]
		margin = [r["link_margin_db"] for r in rows]
		delta_avg_loss = (sum(base_losses) / len(base_losses)) - (sum(losses) / len(losses))
		delta_worst_loss = max(base_losses) - max(losses)
		delta_avg_margin = (sum(margin) / len(margin)) - (sum(base_margin) / len(base_margin))
		delta_worst_margin = min(margin) - min(base_margin)

		print(f"{labels.get(antenna_type, antenna_type)}:")
		print(f"  Avg total-loss improvement: {delta_avg_loss:+.2f} dB")
		print(f"  Worst total-loss improvement: {delta_worst_loss:+.2f} dB")
		print(f"  Avg link-margin improvement: {delta_avg_margin:+.2f} dB")
		print(f"  Worst link-margin improvement: {delta_worst_margin:+.2f} dB")
	print("=" * 72)


def try_plot(rows_by_type: Dict[str, List[Dict[str, float]]]) -> None:
	"""Optional plotting. If matplotlib is unavailable, sim still runs."""
	try:
		import matplotlib.pyplot as plt
	except Exception:
		print("matplotlib not installed; skipping plots.")
		return

	first_key = next(iter(rows_by_type))
	t = [r["t_s"] for r in rows_by_type[first_key]]
	alt = [r["alt_m"] for r in rows_by_type[first_key]]
	labels = {
		"monopole": "1/4-wave monopole",
		"monopole_5_8": "5/8-wave monopole",
		"monopole_3_4": "3/4-wave monopole",
		"dipole": "1/2-wave dipole",
		"conformal_patch_array": "conformal patch array",
	}

	fig, ax = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
	ax[0].plot(t, alt)
	ax[0].set_ylabel("Altitude (m)")
	ax[0].grid(True, alpha=0.3)

	for antenna_type, rows in rows_by_type.items():
		total_loss = [r["total_loss_db"] for r in rows]
		ax[1].plot(t, total_loss, label=labels.get(antenna_type, antenna_type))
	ax[1].set_ylabel("Total Loss (dB)")
	ax[1].grid(True, alpha=0.3)
	ax[1].legend()

	for antenna_type, rows in rows_by_type.items():
		margin = [r["link_margin_db"] for r in rows]
		ax[2].plot(t, margin, label=labels.get(antenna_type, antenna_type))
	ax[2].axhline(0.0, linestyle="--")
	ax[2].set_ylabel("Link Margin (dB)")
	ax[2].set_xlabel("Time (s)")
	ax[2].grid(True, alpha=0.3)
	ax[2].legend()

	plt.tight_layout()
	plt.show()


def main() -> None:
	cfg = SimConfig()
	antenna_types = ["monopole", "monopole_5_8", "monopole_3_4", "dipole", "conformal_patch_array"]
	rows_by_type = {a: run_simulation(cfg, antenna_type=a) for a in antenna_types}

	for antenna_type in antenna_types:
		print_summary(cfg, rows_by_type[antenna_type], antenna_type=antenna_type)

	print_comparison(rows_by_type, baseline_type="monopole")
	try_plot(rows_by_type)


if __name__ == "__main__":
	main()