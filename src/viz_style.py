"""Shared chart style so every notebook and exported figure looks like one report."""
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# Fixed colour per dwelling type (never re-ordered between charts)
DWELLING_COLORS = {"House": "#2a78d6", "Townhouse/Villa": "#eb6834", "Unit": "#1baf7a"}
DWELLING_ORDER = ["House", "Townhouse/Villa", "Unit"]

INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"
NEG = "#e34948"   # diverging: below typical
POS = "#2a78d6"   # diverging: above typical


def apply_style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "figure.dpi": 110, "savefig.dpi": 160, "savefig.bbox": "tight",
        "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
        "text.color": INK, "axes.labelcolor": INK_2, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.edgecolor": AXIS, "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.grid": True, "axes.grid.axis": "y",
        "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
        "axes.titlesize": 13, "axes.titleweight": "semibold", "axes.titlelocation": "left",
        "axes.titlepad": 26, "lines.linewidth": 2, "legend.frameon": False,
        "xtick.major.size": 0, "ytick.major.size": 0,
    })


def money_axis(ax, axis: str = "y") -> None:
    """Format an axis as $k / $M."""
    def fmt(v, _):
        return f"${v / 1e6:.1f}M" if abs(v) >= 1e6 else f"${v / 1e3:.0f}k"
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(mticker.FuncFormatter(fmt))


def pct_axis(ax, axis: str = "y", decimals: int = 0) -> None:
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v:+.{decimals}f}%" if v else "0%"))


def subtitle(ax, text: str) -> None:
    """Grey one-line subtitle under the chart title."""
    ax.text(0, 1.02, text, transform=ax.transAxes, color=INK_2, fontsize=9.5, va="bottom")

# Two-way segment used for trends over time (see notebook 01, Q3 data note)
SEGMENT_COLORS = {"House": "#2a78d6", "Unit/Townhouse": "#eb6834"}
SEGMENT_ORDER = ["House", "Unit/Townhouse"]


def fig_header(fig, title: str, sub: str, top: float = 0.80) -> None:
    """Title + subtitle for a multi-panel figure, leaving room above the panel titles."""
    fig.subplots_adjust(top=top)
    fig.text(0.06, 0.985, title, ha="left", va="top", fontsize=13, fontweight="semibold")
    fig.text(0.06, 0.925, sub, ha="left", va="top", color=INK_2, fontsize=9.5)
