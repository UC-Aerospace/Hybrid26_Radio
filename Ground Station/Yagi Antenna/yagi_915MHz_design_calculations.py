"""5-element Yagi-Uda antenna design calculations for 915 MHz.

References
----------
Balanis, C. A. (2016). Antenna theory: Analysis and design (4th ed.).
    Wiley.
Kraus, J. D. (1988). Antennas (2nd ed.). McGraw-Hill.
Stutzman, W. L., & Thiele, G. A. (2012). Antenna theory and design
    (3rd ed.). Wiley.
Viezbicke, P. P. (1976). Yagi antenna design (NBS Technical Note 688).
    National Bureau of Standards.

All equations used in the script are annotated inline with the relevant
source and equation reference where available.
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


OUTPUT_PDF_NAME = "yagi_915MHz_design_calculations.pdf"


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
    lines = [f"{'Parameter'.ljust(left_width)}  Value", f"{'-' * left_width}  {'-' * 48}"]
    for label, value in rows:
        lines.append(f"{label.ljust(left_width)}  {value}")
    return "\n".join(lines)


def draw_summary_page(rows: list[tuple[str, str]]) -> plt.Figure:
    """Create a PDF page containing the full numeric summary table."""

    fig, ax = plt.subplots(figsize=(11.0, 8.5))
    ax.axis("off")
    ax.set_title("Yagi-Uda 915 MHz Design Summary", fontsize=16, fontweight="bold", pad=18)

    table_text = format_table(rows)
    ax.text(
        0.02,
        0.97,
        table_text,
        transform=ax.transAxes,
        va="top",
        ha="left",
        family="monospace",
        fontsize=8.3,
        linespacing=1.18,
    )

    fig.tight_layout()
    return fig


def vswr_from_impedance(z_load: float, z_system: float) -> float:
    """Calculate VSWR for a real load impedance."""

    return z_load / z_system if z_load > z_system else z_system / z_load


def reflection_coefficient(z_load: float, z_system: float) -> float:
    """Calculate the real-valued reflection coefficient magnitude."""

    return abs((z_load - z_system) / (z_load + z_system))


def gain_db_to_linear(gain_db: float) -> float:
    """Convert gain in dBi to linear gain."""

    return 10.0 ** (gain_db / 10.0)


def linear_to_db(value: float) -> float:
    """Convert a linear ratio to decibels."""

    return 10.0 * np.log10(value)


def draw_layout_plot(
    element_positions_mm: dict[str, float],
    element_lengths_mm: dict[str, float],
    boom_length_mm: float,
) -> plt.Figure:
    """Create a to-scale top-down element layout plot."""

    fig, ax = plt.subplots(figsize=(13, 4.5))

    boom_height_mm = 18.0  # boom thickness [mm]
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
        ax.annotate(
            "",
            xy=(x_pos_mm, -half_length_mm - 10.0),
            xytext=(x_pos_mm, -half_length_mm - 45.0),
            arrowprops=dict(arrowstyle="<->", color=color, lw=1.1),
        )
        ax.text(
            x_pos_mm,
            -half_length_mm - 52.0,
            f"L{index + 1}",
            ha="center",
            va="top",
            fontsize=8,
            color=color,
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


def draw_gain_plot(boom_length_lambda: float, design_gain_db: float) -> plt.Figure:
    """Create a gain versus boom-length plot using the Kraus formula."""

    boom_lengths_lambda = np.linspace(0.5, 4.0, 300)
    gain_kraus_db = 10.0 * np.log10(0.8 * (2.0 * boom_lengths_lambda))  # Kraus, Antennas, Ch. 8
    design_gain_kraus_db = 10.0 * np.log10(0.8 * (2.0 * boom_length_lambda))  # Kraus, Antennas, Ch. 8

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.plot(boom_lengths_lambda, gain_kraus_db, color="#1f77b4", lw=2.2, label="Kraus gain estimate")
    ax.axhline(10.0, color="#d62728", linestyle="--", lw=1.5, label="10 dBi target")
    ax.plot(
        [boom_length_lambda],
        [design_gain_kraus_db],
        marker="o",
        markersize=8,
        color="#2ca02c",
        label=f"Design point at {boom_length_lambda:.2f} λ",
    )
    ax.annotate(
        f"{design_gain_kraus_db:.2f} dBi",
        xy=(boom_length_lambda, design_gain_kraus_db),
        xytext=(boom_length_lambda + 0.15, design_gain_kraus_db + 0.6),
        arrowprops=dict(arrowstyle="->", lw=1.0),
    )
    ax.set_title(f"Gain Versus Boom Length\nDesign average gain = {design_gain_db:.2f} dBi")
    ax.set_xlabel("Boom length [wavelengths]")
    ax.set_ylabel("Gain [dBi]")
    ax.set_xlim(0.5, 4.0)
    ax.set_ylim(min(gain_kraus_db.min(), 0.0) - 0.5, max(gain_kraus_db.max(), 10.5) + 0.5)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right")

    fig.tight_layout()
    return fig


def draw_vswr_plot(f0_hz: float, z_resonance_ohm: float, z_system_ohm: float) -> plt.Figure:
    """Create the VSWR versus frequency plot."""

    frequencies_hz = np.linspace(800e6, 1000e6, 401)
    impedance_ohm = z_resonance_ohm * (frequencies_hz / f0_hz) ** 1.5  # user-specified frequency dependence
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


def draw_pointing_plot(
    design_gain_db: float,
    hpbw_deg: float,
    max_expected_rocket_angle_deg: float,
) -> plt.Figure:
    """Create the pointing error impact plot."""

    theta_deg = np.linspace(0.0, 90.0, 361)
    design_gain_linear = gain_db_to_linear(design_gain_db)
    received_gain_linear = design_gain_linear * np.exp(-2.77 * (theta_deg / hpbw_deg) ** 2)
    received_gain_db = linear_to_db(received_gain_linear)

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.plot(theta_deg, received_gain_db, color="#1f77b4", lw=2.2, label="Received gain")
    ax.axvline(hpbw_deg / 2.0, color="#d62728", linestyle="--", lw=1.5, label="HPBW / 2")
    ax.axvline(
        max_expected_rocket_angle_deg,
        color="#2ca02c",
        linestyle=":",
        lw=1.6,
        label=f"Max expected rocket angle = {max_expected_rocket_angle_deg:.0f}°",
    )
    ax.set_title("Pointing Error Impact on Received Gain")
    ax.set_xlabel("Pointing error [degrees]")
    ax.set_ylabel("Received gain [dBi]")
    ax.set_xlim(0.0, 90.0)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right")

    fig.tight_layout()
    return fig


def main() -> None:
    """Run all calculations, print the summary table, and export plots."""

    # Section 1: Fundamental parameters.
    c_m_per_s = 299_792_458.0  # speed of light [m/s]
    operating_frequency_hz = 915e6  # operating frequency [Hz]
    free_space_wavelength_m = c_m_per_s / operating_frequency_hz  # Balanis, Antenna Theory, Eq. 2-1 [m]

    # Section 2: Normalized 5-element Viezbicke-style design ratios.
    reflector_length_lambda = 0.520  # reflector length / lambda [unitless]
    driven_length_lambda = 0.500  # driven element length / lambda [unitless]
    director1_length_lambda = 0.480  # director 1 length / lambda [unitless]
    director2_length_lambda = 0.460  # director 2 length / lambda [unitless]
    director3_length_lambda = 0.440  # director 3 length / lambda [unitless]

    reflector_to_driven_lambda = 0.350  # spacing / lambda [unitless]
    driven_to_director1_lambda = 0.400  # spacing / lambda [unitless]
    director1_to_director2_lambda = 0.450  # spacing / lambda [unitless]
    director2_to_director3_lambda = 0.500  # spacing / lambda [unitless]

    reflector_length_m = reflector_length_lambda * free_space_wavelength_m  # reflector length [m]
    driven_length_m = driven_length_lambda * free_space_wavelength_m  # driven element length [m]
    director1_length_m = director1_length_lambda * free_space_wavelength_m  # director 1 length [m]
    director2_length_m = director2_length_lambda * free_space_wavelength_m  # director 2 length [m]
    director3_length_m = director3_length_lambda * free_space_wavelength_m  # director 3 length [m]

    reflector_position_m = 0.0  # reflector position from boom origin [m]
    driven_position_m = reflector_to_driven_lambda * free_space_wavelength_m  # driven position [m]
    director1_position_m = (reflector_to_driven_lambda + driven_to_director1_lambda) * free_space_wavelength_m  # director 1 position [m]
    director2_position_m = (reflector_to_driven_lambda + driven_to_director1_lambda + director1_to_director2_lambda) * free_space_wavelength_m  # director 2 position [m]
    director3_position_m = (reflector_to_driven_lambda + driven_to_director1_lambda + director1_to_director2_lambda + director2_to_director3_lambda) * free_space_wavelength_m  # director 3 position [m]

    boom_length_m = director3_position_m  # total boom length [m]

    # Section 3: Driven element feed impedance and mismatch metrics.
    z_system_ohm = 50.0  # system impedance [ohm]
    z_driven_ohm = 25.0  # estimated driven element impedance [ohm]
    vswr = vswr_from_impedance(z_driven_ohm, z_system_ohm)  # Balanis, Eq. 2-64 [ratio]
    gamma_mag = reflection_coefficient(z_driven_ohm, z_system_ohm)  # Balanis, Eq. 2-66 [unitless]
    return_loss_db = -20.0 * np.log10(gamma_mag)  # Balanis, Eq. 2-66 [dB]
    mismatch_loss_db = -10.0 * np.log10(1.0 - gamma_mag**2)  # Balanis, Eq. 2-66 [dB]

    # Section 4: Gain estimates.
    boom_length_lambda = boom_length_m / free_space_wavelength_m  # boom length / lambda [unitless]
    gain_viezbicke_db = 10.0 * np.log10(7.5 * boom_length_lambda)  # Viezbicke empirical gain relationship [dBi]
    gain_kraus_db = 10.0 * np.log10(0.8 * (2.0 * boom_length_lambda + 1.0))  # Kraus, Antennas, Ch. 8 [dBi]
    design_gain_db = gain_viezbicke_db  # design gain from Viezbicke [dBi]
    design_gain_linear = gain_db_to_linear(design_gain_db)  # design gain in linear units [unitless]

    # Section 5: Beamwidth and pointing tolerance.
    hpbw_deg = 101.0 / np.sqrt(design_gain_linear)  # Stutzman & Thiele, Ch. 3 [deg]
    max_pointing_error_deg = hpbw_deg / 2.0  # maximum pointing error [deg]

    # Section 6: Front-to-back ratio.
    front_to_back_db = 20.0  # estimated front-to-back ratio [dB]
    front_to_back_linear = 10.0 ** (front_to_back_db / 10.0)  # power ratio [unitless]

    # Section 7: Effective aperture.
    effective_aperture_m2 = (free_space_wavelength_m**2 / (4.0 * pi)) * design_gain_linear  # Balanis, Eq. 2-96 [m^2]
    effective_aperture_cm2 = to_cm2(effective_aperture_m2)  # effective aperture [cm^2]

    # Section 8: Link budget contribution.
    g_rx_db_i = design_gain_db  # ground station receive gain [dBi]
    delta_link_margin_iso_db = g_rx_db_i - 0.0  # improvement versus isotropic [dB]
    delta_link_margin_whip_db = g_rx_db_i - 3.0  # improvement versus 3 dBi whip [dB]
    minimum_link_margin_db = 32.29  # reference dynamic link budget minimum [dB]

    # Section 9: Hairpin match.
    hairpin_match_length_m = np.nan  # hairpin wire length [m]
    if vswr > 1.5:
        hairpin_match_length_m = (free_space_wavelength_m / (4.0 * pi)) * np.arctan(np.sqrt(z_system_ohm / z_driven_ohm - 1.0))  # Balanis, Ch. 9 matching networks [m]
    hairpin_match_length_mm = to_mm(hairpin_match_length_m) if not np.isnan(hairpin_match_length_m) else np.nan  # hairpin wire length [mm]

    # Additional plotting parameter.
    max_expected_rocket_angle_deg = 30.0  # assumed maximum rocket angular position during flight [deg]

    # Summary values in millimetres.
    free_space_wavelength_mm = to_mm(free_space_wavelength_m)  # free-space wavelength [mm]
    reflector_length_mm = to_mm(reflector_length_m)  # reflector length [mm]
    driven_length_mm = to_mm(driven_length_m)  # driven element length [mm]
    director1_length_mm = to_mm(director1_length_m)  # director 1 length [mm]
    director2_length_mm = to_mm(director2_length_m)  # director 2 length [mm]
    director3_length_mm = to_mm(director3_length_m)  # director 3 length [mm]
    reflector_position_mm = to_mm(reflector_position_m)  # reflector position [mm]
    driven_position_mm = to_mm(driven_position_m)  # driven position [mm]
    director1_position_mm = to_mm(director1_position_m)  # director 1 position [mm]
    director2_position_mm = to_mm(director2_position_m)  # director 2 position [mm]
    director3_position_mm = to_mm(director3_position_m)  # director 3 position [mm]
    boom_length_mm = to_mm(boom_length_m)  # boom length [mm]

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

    # Console summary table.
    summary_rows = [
        ("Operating frequency", format_value(operating_frequency_hz / 1e6, "MHz", 3)),
        ("Free space wavelength", format_value(free_space_wavelength_mm, "mm", 2)),
        ("Reflector length", format_value(reflector_length_mm, "mm", 2)),
        ("Driven element length", format_value(driven_length_mm, "mm", 2)),
        ("Director 1 length", format_value(director1_length_mm, "mm", 2)),
        ("Director 2 length", format_value(director2_length_mm, "mm", 2)),
        ("Director 3 length", format_value(director3_length_mm, "mm", 2)),
        ("Reflector position", format_value(reflector_position_mm, "mm", 2)),
        ("Driven position", format_value(driven_position_mm, "mm", 2)),
        ("Director 1 position", format_value(director1_position_mm, "mm", 2)),
        ("Director 2 position", format_value(director2_position_mm, "mm", 2)),
        ("Director 3 position", format_value(director3_position_mm, "mm", 2)),
        ("Total boom length", format_value(boom_length_mm, "mm", 2)),
        ("Driven feed impedance", format_value(z_driven_ohm, "ohm", 2)),
        ("VSWR into 50 ohms", f"{vswr:.3f}:1"),
        ("Return loss", format_value(return_loss_db, "dB", 3)),
        ("Mismatch loss", format_value(mismatch_loss_db, "dB", 3)),
        ("Gain, Viezbicke (design)", format_value(gain_viezbicke_db, "dBi", 3)),
        ("Gain, Kraus", format_value(gain_kraus_db, "dBi", 3)),
        ("Half power beamwidth", format_value(hpbw_deg, "deg", 3)),
        ("Maximum pointing error", format_value(max_pointing_error_deg, "deg", 3)),
        ("Front to back ratio", format_value(front_to_back_db, "dB", 2)),
        ("Front to back power ratio", format_value(front_to_back_linear, "x", 2)),
        ("Effective aperture", format_value(effective_aperture_cm2, "cm^2", 2)),
        ("Link margin improvement vs isotropic", format_value(delta_link_margin_iso_db, "dB", 3)),
        ("Link margin improvement vs 3 dBi whip", format_value(delta_link_margin_whip_db, "dB", 3)),
        ("Reference minimum link margin", format_value(minimum_link_margin_db, "dB", 2)),
        ("Hairpin match length", format_value(hairpin_match_length_mm, "mm", 3)),
    ]

    print(format_table(summary_rows))

    # Generate plots into a single PDF file.
    output_pdf_path = Path(__file__).with_name(OUTPUT_PDF_NAME)
    with PdfPages(output_pdf_path) as pdf:
        figures = [
            draw_summary_page(summary_rows),
            draw_layout_plot(element_positions_mm, element_lengths_mm, boom_length_mm),
            draw_gain_plot(boom_length_lambda, design_gain_db),
            draw_vswr_plot(operating_frequency_hz, z_driven_ohm, z_system_ohm),
            draw_pointing_plot(design_gain_db, hpbw_deg, max_expected_rocket_angle_deg),
        ]
        for figure in figures:
            pdf.savefig(figure)
            plt.close(figure)

    print(f"\nSaved plots to: {output_pdf_path}")


if __name__ == "__main__":
    main()