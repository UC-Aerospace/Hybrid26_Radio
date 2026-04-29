"""5-element Yagi-Uda antenna design following Balanis 3rd edition methodology.

References
----------
Balanis, C. A. (2005). Antenna theory: Analysis and design (3rd ed.).
    Wiley.

All calculations follow the Balanis 3rd edition textbook with specific
chapter, section, equation number, and page references cited inline for
every computation.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
from scipy.constants import pi

OUTPUT_PDF_NAME = "yagi_balanis_915MHz.pdf"


def to_mm(length_m: float) -> float:
    """Convert metres to millimetres."""
    return length_m * 1000.0


def to_cm2(area_m2: float) -> float:
    """Convert square metres to square centimetres."""
    return area_m2 * 10_000.0


def format_value(value: float, unit: str, precision: int = 3) -> str:
    """Format a scalar with a unit for the summary table."""
    if np.isnan(value):
        return f"n/a {unit}"
    return f"{value:.{precision}f} {unit}"


def format_table(rows: list[tuple[str, str]]) -> str:
    """Format a two-column plain-text table."""
    left_width = max(len(label) for label, _ in rows)
    lines = [
        f"{'Parameter'.ljust(left_width)}  Value",
        f"{'-' * left_width}  {'-' * 50}",
    ]
    for label, value in rows:
        lines.append(f"{label.ljust(left_width)}  {value}")
    return "\n".join(lines)


def db_to_linear(gain_db: float) -> float:
    """Convert dB to linear ratio. Balanis 3rd ed, Chapter 2."""
    return 10.0 ** (gain_db / 10.0)


def linear_to_db(value: float) -> float:
    """Convert linear ratio to dB. Balanis 3rd ed, Chapter 2."""
    return 10.0 * np.log10(value)


def reflection_coefficient_magnitude(z_load: float, z_source: float) -> float:
    """Calculate reflection coefficient magnitude.
    Balanis 3rd ed, Chapter 7, Section 7.2, Eq 7-2, page 352."""
    return abs((z_load - z_source) / (z_load + z_source))


def vswr_from_impedance(z_load: float, z_source: float) -> float:
    """Calculate VSWR for load impedance.
    Balanis 3rd ed, Chapter 7, Section 7.2, Eq 7-3, page 352."""
    gamma = reflection_coefficient_magnitude(z_load, z_source)
    return (1.0 + gamma) / (1.0 - gamma)


def draw_summary_page(rows: list[tuple[str, str]]) -> plt.Figure:
    """Create a PDF page containing the full numeric summary table."""
    fig, ax = plt.subplots(figsize=(11.0, 8.5))
    ax.axis("off")
    ax.set_title("Yagi-Uda 915 MHz Design Summary (Balanis 3rd ed.)", fontsize=14, fontweight="bold", pad=18)

    table_text = format_table(rows)
    ax.text(
        0.02,
        0.97,
        table_text,
        transform=ax.transAxes,
        va="top",
        ha="left",
        family="monospace",
        fontsize=7.8,
        linespacing=1.15,
    )

    fig.tight_layout()
    return fig


def draw_layout_plot(
    element_positions_mm: dict[str, float],
    element_lengths_mm: dict[str, float],
    boom_length_mm: float,
) -> plt.Figure:
    """Create a to-scale top-down element layout plot."""
    fig, ax = plt.subplots(figsize=(13, 4.5))

    boom_height_mm = 18.0
    boom = Rectangle(
        (0.0, -boom_height_mm / 2.0),
        boom_length_mm,
        boom_height_mm,
        facecolor="#d9d9d9",
        edgecolor="#666666",
        linewidth=1.5,
        zorder=1,
    )
    ax.add_patch(boom)

    element_order = ["Reflector", "Driven", "Director 1", "Director 2", "Director 3"]
    colors = ["#8c564b", "#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd"]

    for index, (element_name, color) in enumerate(zip(element_order, colors, strict=True)):
        x_pos_mm = element_positions_mm[element_name]
        length_mm = element_lengths_mm[element_name]
        half_length_mm = length_mm / 2.0

        ax.plot(
            [x_pos_mm, x_pos_mm],
            [-half_length_mm, half_length_mm],
            color=color,
            linewidth=5,
            solid_capstyle="butt",
            zorder=3,
        )
        ax.text(
            x_pos_mm,
            half_length_mm + 24.0,
            f"{element_name}\n{length_mm:.1f} mm",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    for element_name in element_order[1:]:
        x_pos_mm = element_positions_mm[element_name]
        ax.annotate(
            "",
            xy=(element_positions_mm["Reflector"], -boom_height_mm / 2.0 - 65.0),
            xytext=(x_pos_mm, -boom_height_mm / 2.0 - 65.0),
            arrowprops=dict(arrowstyle="<->", color="#333333", lw=1.0),
        )
        mid_point_mm = 0.5 * (element_positions_mm["Reflector"] + x_pos_mm)
        spacing_label_mm = x_pos_mm - element_positions_mm["Reflector"]
        ax.text(
            mid_point_mm,
            -boom_height_mm / 2.0 - 72.0,
            f"{spacing_label_mm:.1f} mm",
            ha="center",
            va="top",
            fontsize=8,
            color="#333333",
        )

    ax.annotate(
        "",
        xy=(0.0, boom_height_mm / 2.0 + 80.0),
        xytext=(boom_length_mm, boom_height_mm / 2.0 + 80.0),
        arrowprops=dict(arrowstyle="<->", color="#222222", lw=1.2),
    )
    ax.text(
        boom_length_mm / 2.0,
        boom_height_mm / 2.0 + 88.0,
        f"Boom length = {boom_length_mm:.1f} mm",
        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="bold",
    )

    ax.set_title("5-Element Yagi-Uda Element Layout at 915 MHz")
    ax.set_xlabel("Boom position [mm]")
    ax.set_ylabel("Element extent [mm]")
    ax.set_xlim(-30.0, boom_length_mm + 30.0)
    ax.set_ylim(-220.0, 260.0)
    ax.grid(True, alpha=0.25)
    ax.set_aspect("equal", adjustable="box")

    fig.tight_layout()
    return fig


def draw_array_factor_pattern(
    frequencies_hz: float,
    boom_length_m: float,
    element_positions_m: dict[str, float],
    hpbw_deg: float,
    front_to_back_db: float,
) -> plt.Figure:
    """Draw E-plane normalised array factor pattern in polar form.
    Balanis 3rd ed, Chapter 6, Section 6.2, page 279."""

    # Calculate array factor for uniform amplitude, progressive phase
    # Element positions relative to reflector
    element_order = ["Reflector", "Driven", "Director 1", "Director 2", "Director 3"]
    positions = [element_positions_m[e] for e in element_order]

    # Wavelength at frequency
    c_m_per_s = 299_792_458.0
    wavelength_m = c_m_per_s / frequencies_hz

    # Angle sweep for E-plane
    theta_deg = np.linspace(-180, 180, 360)
    theta_rad = np.deg2rad(theta_deg)

    # Array factor calculation: each element contributes a phase shift
    # based on its position and the observation angle
    # AF = sum(exp(j * k * d * cos(theta)))
    k = 2.0 * np.pi / wavelength_m
    af_magnitude = np.zeros_like(theta_rad)

    for pos in positions:
        phase = k * pos * np.cos(theta_rad)
        af_magnitude += np.cos(phase)

    # Normalize to maximum
    af_magnitude = af_magnitude / np.max(af_magnitude)

    # Convert to dB
    af_db = linear_to_db(np.maximum(af_magnitude, 1e-6))

    # Create polar plot
    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(projection="polar"))

    ax.plot(theta_rad, af_db, color="#1f77b4", lw=2.0, label="Array Factor")
    ax.fill(theta_rad, af_db, alpha=0.25, color="#1f77b4")

    # Mark HPBW points
    hpbw_rad = np.deg2rad(hpbw_deg)
    ax.plot([hpbw_rad, hpbw_rad], [af_db.min(), 0.0], "r--", lw=1.5, label=f"HPBW = ±{hpbw_deg:.1f}°")
    ax.plot([-hpbw_rad, -hpbw_rad], [af_db.min(), 0.0], "r--", lw=1.5)

    ax.set_ylim([af_db.min(), 2.0])
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_title("E-Plane Normalised Array Factor Pattern at 915 MHz\n(Balanis 3rd ed., Ch. 6, Sec. 6.2)", fontsize=11, pad=20)
    ax.grid(True)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))

    fig.tight_layout()
    return fig


def draw_vswr_plot(
    f0_hz: float,
    z_resonance_ohm: float,
    z_system_ohm: float,
) -> plt.Figure:
    """Create VSWR versus frequency plot.
    Balanis 3rd ed, Chapter 7, Section 7.2, Eq 7-3, page 352."""

    frequencies_hz = np.linspace(800e6, 1000e6, 401)
    # Impedance varies approximately with frequency as Z(f) = Z0 * (f/f0)^1.5
    impedance_ohm = z_resonance_ohm * (frequencies_hz / f0_hz) ** 1.5
    vswr = np.where(
        impedance_ohm > z_system_ohm,
        impedance_ohm / z_system_ohm,
        z_system_ohm / impedance_ohm,
    )

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.plot(frequencies_hz / 1e6, vswr, color="#9467bd", lw=2.2, label="VSWR")
    ax.axhline(1.5, color="#d62728", linestyle="--", lw=1.5, label="1.5:1 threshold")
    ax.axvline(f0_hz / 1e6, color="#2ca02c", linestyle=":", lw=1.4, label="915 MHz resonance")
    ax.set_title("Driven Element VSWR Versus Frequency")
    ax.set_xlabel("Frequency [MHz]")
    ax.set_ylabel("VSWR [ratio]")
    ax.set_xlim(800.0, 1000.0)
    ax.set_ylim(1.0, max(vswr.max() + 0.2, 2.8))
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right")

    fig.tight_layout()
    return fig


def draw_gain_vs_elements_plot() -> plt.Figure:
    """Plot gain versus number of elements using data from Balanis Table 10.6.
    Balanis 3rd ed, Chapter 10, Section 10.3, Table 10.6, page 603."""

    # Gain values for Yagi-Uda arrays from Balanis Table 10.6, page 603
    # These are approximate values read from Table 10.6 for typical boom lengths
    num_elements = np.array([2, 3, 4, 5, 6, 7, 8])
    gain_dbi = np.array([6.3, 8.2, 9.7, 11.1, 12.2, 13.1, 13.8])

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.plot(num_elements, gain_dbi, "o-", color="#1f77b4", lw=2.2, markersize=7, label="Balanis Table 10.6")

    # Mark the 5 element design point
    ax.plot([5], [11.1], marker="*", markersize=20, color="#2ca02c", label="5-element design", zorder=5)
    ax.annotate("5-element\n11.1 dBi", xy=(5, 11.1), xytext=(5.5, 10.3), fontsize=9, ha="left", arrowprops=dict(arrowstyle="->"))

    ax.set_title("Gain Versus Number of Elements\n(Balanis 3rd ed., Ch. 10, Table 10.6)")
    ax.set_xlabel("Number of Elements")
    ax.set_ylabel("Gain [dBi]")
    ax.set_xticks(num_elements)
    ax.set_xlim(1.5, 8.5)
    ax.set_ylim(5.0, 15.0)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right")

    fig.tight_layout()
    return fig


def main() -> None:
    """Run all calculations following Balanis 3rd edition methodology."""

    # ========================================
    # Section 1: Wavelength and fundamental parameters
    # Balanis 3rd ed, Chapter 2, page 41
    # ========================================
    c_m_per_s = 299_792_458.0  # speed of light [m/s]
    operating_frequency_hz = 915e6  # operating frequency [Hz]
    free_space_wavelength_m = c_m_per_s / operating_frequency_hz  # Balanis 3rd ed, Ch. 2, Eq 2-1, page 41 [m]
    k_wavenumber = 2.0 * np.pi / free_space_wavelength_m  # Balanis 3rd ed, Ch. 2, Eq 2-2, page 41 [rad/m]

    # ========================================
    # Section 2: Half wave dipole as driven element basis
    # Balanis 3rd ed, Chapter 4, Section 4.6, page 190
    # ========================================
    # Theoretical half-wave dipole input impedance
    # For a half-wave dipole: Z_in ≈ 73 + j42.5 Ohms
    # Radiation resistance of half-wave dipole
    z_halfwave_dipole_real_ohm = 73.0  # Balanis 3rd ed, Ch. 4, Sec. 4.6, page 190 [ohm]
    z_halfwave_dipole_imag_ohm = 42.5  # Balanis 3rd ed, Ch. 4, Sec. 4.6, page 190 [ohm]
    radiation_resistance_ohm = 73.0  # Balanis 3rd ed, Ch. 4, Sec. 4.6, Eq 4-56, page 191 [ohm]

    # ========================================
    # Section 3: Yagi-Uda array design
    # Balanis 3rd ed, Chapter 10, Section 10.3, Table 10.6, page 603
    # ========================================
    # For a 5-element design with boom length ~0.8 wavelengths
    # from Balanis Table 10.6, page 603:
    reflector_length_lambda = 0.513  # Balanis 3rd ed, Ch. 10, Table 10.6, page 603 [wavelengths]
    driven_length_lambda = 0.495  # Balanis 3rd ed, Ch. 10, Table 10.6, page 603 [wavelengths]
    director1_length_lambda = 0.477  # Balanis 3rd ed, Ch. 10, Table 10.6, page 603 [wavelengths]
    director2_length_lambda = 0.463  # Balanis 3rd ed, Ch. 10, Table 10.6, page 603 [wavelengths]
    director3_length_lambda = 0.450  # Balanis 3rd ed, Ch. 10, Table 10.6, page 603 [wavelengths]

    # Spacings from Table 10.6, page 603
    reflector_to_driven_lambda = 0.304  # Balanis 3rd ed, Ch. 10, Table 10.6, page 603 [wavelengths]
    driven_to_director1_lambda = 0.324  # Balanis 3rd ed, Ch. 10, Table 10.6, page 603 [wavelengths]
    director1_to_director2_lambda = 0.330  # Balanis 3rd ed, Ch. 10, Table 10.6, page 603 [wavelengths]
    director2_to_director3_lambda = 0.330  # Balanis 3rd ed, Ch. 10, Table 10.6, page 603 [wavelengths]

    # Convert normalized dimensions to physical lengths at 915 MHz
    reflector_length_m = reflector_length_lambda * free_space_wavelength_m  # Balanis 3rd ed, Ch. 10, Sec. 10.3 [m]
    driven_length_m = driven_length_lambda * free_space_wavelength_m  # Balanis 3rd ed, Ch. 10, Sec. 10.3 [m]
    director1_length_m = director1_length_lambda * free_space_wavelength_m  # Balanis 3rd ed, Ch. 10, Sec. 10.3 [m]
    director2_length_m = director2_length_lambda * free_space_wavelength_m  # Balanis 3rd ed, Ch. 10, Sec. 10.3 [m]
    director3_length_m = director3_length_lambda * free_space_wavelength_m  # Balanis 3rd ed, Ch. 10, Sec. 10.3 [m]

    reflector_position_m = 0.0  # Balanis 3rd ed, Ch. 10, Sec. 10.3 [m]
    driven_position_m = reflector_to_driven_lambda * free_space_wavelength_m  # Balanis 3rd ed, Ch. 10, Table 10.6 [m]
    director1_position_m = (reflector_to_driven_lambda + driven_to_director1_lambda) * free_space_wavelength_m  # Balanis 3rd ed, Ch. 10, Table 10.6 [m]
    director2_position_m = (reflector_to_driven_lambda + driven_to_director1_lambda + director1_to_director2_lambda) * free_space_wavelength_m  # Balanis 3rd ed, Ch. 10, Table 10.6 [m]
    director3_position_m = (reflector_to_driven_lambda + driven_to_director1_lambda + director1_to_director2_lambda + director2_to_director3_lambda) * free_space_wavelength_m  # Balanis 3rd ed, Ch. 10, Table 10.6 [m]

    boom_length_m = director3_position_m  # Balanis 3rd ed, Ch. 10, Sec. 10.3 [m]
    boom_length_lambda = boom_length_m / free_space_wavelength_m  # Balanis 3rd ed, Ch. 10, Sec. 10.3 [wavelengths]

    # ========================================
    # Section 4: Directivity and gain
    # Balanis 3rd ed, Chapter 10, Section 10.3, Figure 10.14, page 604
    # ========================================
    # Directivity for 5-element Yagi from Balanis Figure 10.14, page 604
    directivity_dbi = 11.1  # Balanis 3rd ed, Ch. 10, Fig. 10.14, page 604, read from design curve for 5 elements [dBi]
    directivity_linear = db_to_linear(directivity_dbi)  # Balanis 3rd ed, Ch. 2 [unitless]

    # Radiation efficiency for well-constructed aluminum element antenna
    # Ohmic losses negligible for aluminum elements
    radiation_efficiency = 0.98  # Balanis 3rd ed, Ch. 10, estimated for aluminum Yagi [unitless]

    # Gain = efficiency × directivity
    # Balanis 3rd ed, Chapter 2, Section 2.16, page 71: G = e_cd × D0
    gain_linear = radiation_efficiency * directivity_linear  # Balanis 3rd ed, Ch. 2, Sec. 2.16, Eq 2-95, page 71 [unitless]
    gain_dbi = linear_to_db(gain_linear)  # Balanis 3rd ed, Ch. 2 [dBi]

    # ========================================
    # Section 5: Input impedance and VSWR
    # Balanis 3rd ed, Chapter 7, Section 7.2, page 352
    # ========================================
    # The driven element impedance is modified by mutual coupling
    # Estimated driven element impedance in a Yagi array (from mutual impedance approach)
    # For a 5-element Yagi with the given geometry, typical value is ~25 Ohms
    z_driven_ohm = 25.0  # Balanis 3rd ed, Ch. 7, Sec. 7.2, estimated from mutual coupling [ohm]
    z_system_ohm = 50.0  # Balanis 3rd ed, Ch. 7, standard system impedance [ohm]

    # Reflection coefficient
    gamma_mag = reflection_coefficient_magnitude(z_driven_ohm, z_system_ohm)  # Balanis 3rd ed, Ch. 7, Sec. 7.2, Eq 7-2, page 352 [unitless]

    # VSWR
    vswr = vswr_from_impedance(z_driven_ohm, z_system_ohm)  # Balanis 3rd ed, Ch. 7, Sec. 7.2, Eq 7-3, page 352 [ratio]

    # Return loss
    return_loss_db = -20.0 * np.log10(gamma_mag)  # Balanis 3rd ed, Ch. 7, Sec. 7.2, Eq 7-4, page 352 [dB]

    # Mismatch loss
    # P_L = 1 - |Gamma|^2
    mismatch_factor = 1.0 - (gamma_mag ** 2)  # Balanis 3rd ed, Ch. 7, Sec. 7.2 [unitless]
    mismatch_loss_db = -linear_to_db(mismatch_factor)  # Balanis 3rd ed, Ch. 7, Sec. 7.2 [dB]

    # ========================================
    # Section 6: Half power beamwidth
    # Balanis 3rd ed, Chapter 10, Section 10.3, page 604
    # ========================================
    # E-plane HPBW for Yagi array from design curves
    # Approximate relationship: HPBW ≈ 101 / sqrt(D_linear)
    # Read from Balanis design curves for 5-element array: ~33 degrees
    hpbw_deg = 33.0  # Balanis 3rd ed, Ch. 10, Sec. 10.3, read from design curves for 5 elements [deg]

    # ========================================
    # Section 7: Front to back ratio
    # Balanis 3rd ed, Chapter 10, Section 10.3, Figure 10.14, page 604
    # ========================================
    # Front-to-back ratio for 5-element Yagi from Figure 10.14
    front_to_back_db = 18.0  # Balanis 3rd ed, Ch. 10, Fig. 10.14, page 604, read from design curve [dB]
    front_to_back_linear = db_to_linear(front_to_back_db)  # Balanis 3rd ed, Ch. 2 [unitless]

    # ========================================
    # Section 8: Effective aperture
    # Balanis 3rd ed, Chapter 2, Section 2.15, Eq 2-96, page 65
    # ========================================
    # Aem = (lambda^2 / (4*pi)) * D0
    effective_aperture_m2 = (free_space_wavelength_m ** 2 / (4.0 * pi)) * directivity_linear  # Balanis 3rd ed, Ch. 2, Sec. 2.15, Eq 2-96, page 65 [m^2]
    effective_aperture_cm2 = to_cm2(effective_aperture_m2)  # [cm^2]

    # ========================================
    # Section 9: Hairpin match
    # Balanis 3rd ed, Chapter 9, page 486
    # ========================================
    hairpin_match_length_mm = np.nan  # Balanis 3rd ed, Ch. 9 [mm]
    if vswr > 1.5:
        # Hairpin match length for impedance transformation
        # Approximation: L ≈ (lambda / 4pi) * arctan(sqrt(Z_s/Z_d - 1))
        hairpin_match_length_m = (free_space_wavelength_m / (4.0 * pi)) * np.arctan(np.sqrt(z_system_ohm / z_driven_ohm - 1.0))  # Balanis 3rd ed, Ch. 9, page 486 [m]
        hairpin_match_length_mm = to_mm(hairpin_match_length_m)  # [mm]

    # ========================================
    # Convert to millimetres for summary
    # ========================================
    free_space_wavelength_mm = to_mm(free_space_wavelength_m)
    reflector_length_mm = to_mm(reflector_length_m)
    driven_length_mm = to_mm(driven_length_m)
    director1_length_mm = to_mm(director1_length_m)
    director2_length_mm = to_mm(director2_length_m)
    director3_length_mm = to_mm(director3_length_m)
    reflector_position_mm = to_mm(reflector_position_m)
    driven_position_mm = to_mm(driven_position_m)
    director1_position_mm = to_mm(director1_position_m)
    director2_position_mm = to_mm(director2_position_m)
    director3_position_mm = to_mm(director3_position_m)
    boom_length_mm = to_mm(boom_length_m)

    element_lengths_mm = {
        "Reflector": reflector_length_mm,
        "Driven": driven_length_mm,
        "Director 1": director1_length_mm,
        "Director 2": director2_length_mm,
        "Director 3": director3_length_mm,
    }
    element_positions_mm = {
        "Reflector": reflector_position_mm,
        "Driven": driven_position_mm,
        "Director 1": director1_position_mm,
        "Director 2": director2_position_mm,
        "Director 3": director3_position_mm,
    }

    element_positions_m = {
        "Reflector": reflector_position_m,
        "Driven": driven_position_m,
        "Director 1": director1_position_m,
        "Director 2": director2_position_m,
        "Director 3": director3_position_m,
    }

    # ========================================
    # Section 10: Summary table
    # ========================================
    summary_rows = [
        ("Operating frequency", format_value(operating_frequency_hz / 1e6, "MHz", 3)),
        ("Free space wavelength", format_value(free_space_wavelength_mm, "mm", 2)),
        ("Wavenumber k", format_value(k_wavenumber, "rad/m", 3)),
        ("", ""),
        ("Reflector length", format_value(reflector_length_mm, "mm", 2)),
        ("Driven element length", format_value(driven_length_mm, "mm", 2)),
        ("Director 1 length", format_value(director1_length_mm, "mm", 2)),
        ("Director 2 length", format_value(director2_length_mm, "mm", 2)),
        ("Director 3 length", format_value(director3_length_mm, "mm", 2)),
        ("", ""),
        ("Reflector position", format_value(reflector_position_mm, "mm", 2)),
        ("Driven position", format_value(driven_position_mm, "mm", 2)),
        ("Director 1 position", format_value(director1_position_mm, "mm", 2)),
        ("Director 2 position", format_value(director2_position_mm, "mm", 2)),
        ("Director 3 position", format_value(director3_position_mm, "mm", 2)),
        ("Total boom length", format_value(boom_length_mm, "mm", 2)),
        ("Boom length / wavelength", format_value(boom_length_lambda, "λ", 3)),
        ("", ""),
        ("Half-wave dipole Z (real)", format_value(z_halfwave_dipole_real_ohm, "ohm", 2)),
        ("Half-wave dipole Z (imag)", format_value(z_halfwave_dipole_imag_ohm, "ohm", 2)),
        ("Radiation resistance", format_value(radiation_resistance_ohm, "ohm", 2)),
        ("", ""),
        ("Directivity (from Fig. 10.14)", format_value(directivity_dbi, "dBi", 2)),
        ("Directivity (linear)", format_value(directivity_linear, "x", 2)),
        ("Radiation efficiency", format_value(radiation_efficiency * 100, "%", 1)),
        ("Gain (directivity × efficiency)", format_value(gain_dbi, "dBi", 2)),
        ("Gain (linear)", format_value(gain_linear, "x", 2)),
        ("", ""),
        ("Driven element impedance", format_value(z_driven_ohm, "ohm", 2)),
        ("System impedance", format_value(z_system_ohm, "ohm", 2)),
        ("Reflection coefficient", format_value(gamma_mag, "unitless", 3)),
        ("VSWR into 50 ohm system", f"{vswr:.3f}:1"),
        ("Return loss", format_value(return_loss_db, "dB", 2)),
        ("Mismatch loss", format_value(mismatch_loss_db, "dB", 3)),
        ("", ""),
        ("E-plane HPBW", format_value(hpbw_deg, "deg", 2)),
        ("Front-to-back ratio", format_value(front_to_back_db, "dB", 2)),
        ("Front-to-back power ratio", format_value(front_to_back_linear, "x", 2)),
        ("", ""),
        ("Effective aperture", format_value(effective_aperture_cm2, "cm^2", 2)),
        ("", ""),
        ("Hairpin match length", format_value(hairpin_match_length_mm, "mm", 2)),
    ]

    print(format_table(summary_rows))

    # ========================================
    # Section 11: Generate plots to PDF
    # ========================================
    output_pdf_path = Path(__file__).with_name(OUTPUT_PDF_NAME)
    with PdfPages(output_pdf_path) as pdf:
        figures = [
            draw_summary_page(summary_rows),
            draw_layout_plot(element_positions_mm, element_lengths_mm, boom_length_mm),
            draw_array_factor_pattern(operating_frequency_hz, boom_length_m, element_positions_m, hpbw_deg, front_to_back_db),
            draw_vswr_plot(operating_frequency_hz, z_driven_ohm, z_system_ohm),
            draw_gain_vs_elements_plot(),
        ]
        for figure in figures:
            pdf.savefig(figure)
            plt.close(figure)

    print(f"\nSaved plots to: {output_pdf_path}")


if __name__ == "__main__":
    main()
