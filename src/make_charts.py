"""
SIG x BDAA Invitational - evidence charts
=========================================

Builds 19 evidence charts from data/clean/ (run src/clean_data.py first).

    python src/make_charts.py

Writes 16:9 slide-ready PNGs to charts/.

Colour rule: each fuel keeps one colour on every chart.
    clean = blue, gas = orange, coal = dark grey, demand = light grey.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
import textwrap

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "charts"
OUT.mkdir(exist_ok=True)

# --- palette (validated: blue/orange pass all categorical checks) -----------
CLEAN_C = "#2a78d6"      # clean energy
CLEAN_LIGHT = "#86b6ef"  # clean, secondary series
GAS_C = "#eb6834"        # natural gas
COAL_C = "#52514e"       # coal
DEMAND_C = "#c3c2b7"     # demand (bars)
DEMAND_LINE = "#898781"  # demand (lines)
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"

FONT = "Inter" if any("Inter" in f.name for f in font_manager.fontManager.ttflist) else "DejaVu Sans"
plt.rcParams.update({
    "font.family": FONT,
    "font.size": 13,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK_2,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelsize": 13,
    "ytick.labelsize": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})

FIGSIZE = (13.33, 7.5)   # 16:9 slide
DPI = 150


def frame(title: str, subtitle: str, source: str, nrows: int = 1, ncols: int = 1, **kw):
    """Figure with a finding-first title, a subtitle and a source line."""
    fig, axes = plt.subplots(nrows, ncols, figsize=FIGSIZE, **kw)
    fig.subplots_adjust(left=0.07, right=0.95, top=0.80, bottom=0.13)
    fig.text(0.07, 0.93, title, fontsize=22, fontweight="semibold", color=INK, ha="left")
    fig.text(0.07, 0.875, subtitle, fontsize=14, color=INK_2, ha="left")
    fig.text(0.07, 0.018, textwrap.fill(f"Source: {source}", 172), fontsize=10.5, color=MUTED,
             ha="left", va="bottom", linespacing=1.4)
    return fig, axes


def tidy(ax, ygrid: bool = True, xgrid: bool = False):
    ax.tick_params(length=0, pad=6)
    if ygrid:
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    if xgrid:
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(AXIS)


def save(fig, name: str):
    path = OUT / name
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    print("wrote", path.relative_to(ROOT))


# --- data -------------------------------------------------------------------
elec = pd.read_csv(CLEAN / "electricity_clean.csv")
world = pd.read_csv(CLEAN / "electricity_world_panel.csv").set_index("year")
coal_us = pd.read_csv(CLEAN / "coal_us_power.csv").set_index("year")
coal_gas = pd.read_csv(CLEAN / "coal_vs_gas_us_power.csv").set_index("year")
states = pd.read_csv(CLEAN / "coal_state_power.csv")

us = elec[elec["iso3"].eq("USA")].set_index("year")
COAL_HEAT_RATE = 10.7   # million Btu per MWh, typical coal plant (assumption)
mix = pd.DataFrame({
    "gen": us["generation_twh"],
    "demand": us["demand_twh"],
    "clean": us["clean_generation_twh"],
    "wind_solar": us["wind_solar_generation_twh"],
    "fossil": us["fossil_generation_twh"],
    "coal": coal_us["consumption_tons"] * coal_us["heat_mmbtu_per_ton"] / COAL_HEAT_RATE / 1e6,
})
mix["gas"] = mix["fossil"] - mix["coal"]          # gas + a little oil (estimate)
for k in ["clean", "gas", "coal"]:
    mix[f"{k}_share"] = mix[k] / mix["gen"] * 100
mix.round(2).to_csv(CLEAN / "us_power_mix_estimate.csv")

EMBER_US = "Ember country-year electricity (provided), U.S. rows"
GAS_NOTE = "Gas = fossil generation minus coal generation (estimated from EIA coal tons, typical plant efficiency); includes a small amount of oil."

# =============================================================================
# 1. Gas is the backbone; clean edged past it in 2025
# =============================================================================
fig, ax = frame(
    "Gas and clean each make ~40% of U.S. power; clean pulled ahead in 2025",
    "Share of U.S. electricity generation, %. Gas is the largest single fuel; clean is a group (nuclear, hydro, wind, solar)",
    f"{EMBER_US}; EIA U.S. coal consumption (provided). {GAS_NOTE}",
)
years = mix.index
series = [("clean_share", "Clean (nuclear, hydro, wind, solar)", CLEAN_C, 3.2),
          ("gas_share", "Natural gas (estimate)", GAS_C, 2.4),
          ("coal_share", "Coal (estimate)", COAL_C, 2.4)]
for col, label, color, lw in series:
    ax.plot(years, mix[col], color=color, linewidth=lw, marker="o", markersize=7,
            markeredgecolor=SURFACE, markeredgewidth=1.5, label=label, zorder=3)
    end = mix[col].iloc[-1]
    dy = {"clean_share": 1.4, "gas_share": -1.4, "coal_share": 0}[col]
    ax.annotate(f"{label.split(' (')[0]} {end:.1f}%", (years[-1], end), xytext=(14, dy * 6),
                textcoords="offset points", va="center", fontsize=13, color=INK,
                fontweight="semibold" if col == "clean_share" else "normal")
ax.set_ylim(0, 50)
ax.set_xlim(years[0] - 0.2, years[-1] + 0.9)
ax.set_yticks(range(0, 51, 10))
ax.set_yticklabels([f"{v}%" for v in range(0, 51, 10)])
ax.set_xticks(years)
ax.legend(loc="lower left", frameon=False, fontsize=12, ncol=3, bbox_to_anchor=(0, -0.01))
tidy(ax)
save(fig, "01_us_mix_gas_backbone.png")

# =============================================================================
# 2. World: clean growth beat demand growth in 2025
# =============================================================================
w = world.loc[2021:2025]
fig, ax = frame(
    "2025: the world added more clean power than new demand for the first time",
    "Yearly increase in electricity, TWh (same 91 countries every year, ~94% of world demand; 2021 = post-COVID rebound)",
    "Ember country-year electricity (provided); balanced panel of the 91 countries with 2025 data.",
)
x = np.arange(len(w))
bw = 0.36
ax.bar(x - bw / 2 - 0.01, w["demand_change_twh"], bw, color=DEMAND_C, label="Demand growth", zorder=3)
ax.bar(x + bw / 2 + 0.01, w["clean_generation_change_twh"], bw, color=CLEAN_C, label="Clean power growth", zorder=3)
for i, yr in enumerate(w.index):
    d, c = w.loc[yr, "demand_change_twh"], w.loc[yr, "clean_generation_change_twh"]
    ax.text(i - bw / 2 - 0.01, d + 20, f"+{d:,.0f}", ha="center", fontsize=12, color=INK_2)
    ax.text(i + bw / 2 + 0.01, c + 20, f"+{c:,.0f}", ha="center", fontsize=12, color=INK,
            fontweight="semibold" if yr == 2025 else "normal")
cov = w.loc[2025, "clean_covers_new_demand_pct"]
ax.annotate(f"Clean covered {cov:.0f}% of new demand.\nFossil generation fell {abs(w.loc[2025, 'fossil_generation_change_twh']):.0f} TWh.",
            (4 + bw / 2, w.loc[2025, "clean_generation_change_twh"] + 60), xytext=(2.55, 1420),
            fontsize=13, color=INK, ha="left",
            arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=1))
ax.set_xticks(x)
ax.set_xticklabels(w.index)
ax.set_ylim(0, 1600)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
ax.legend(loc="lower left", frameon=False, fontsize=12, ncol=2, bbox_to_anchor=(0, 1.0))
tidy(ax)
save(fig, "02_world_clean_beats_demand.png")

# =============================================================================
# 3. U.S.: who supplied the new demand, 2021 -> 2025
# =============================================================================
chg = (mix.loc[2025] - mix.loc[2021])
bars = [("New demand", chg["demand"], DEMAND_C),
        ("Clean", chg["clean"], CLEAN_C),
        ("Natural gas (est.)", chg["gas"], GAS_C),
        ("Coal (est.)", chg["coal"], COAL_C)]
share = chg["clean"] / chg["demand"] * 100
fig, ax = frame(
    f"Since 2021, clean energy added power equal to {share:.0f}% of America's new demand",
    "Change in U.S. electricity, 2021 to 2025, TWh",
    f"{EMBER_US}; EIA U.S. coal consumption (provided). {GAS_NOTE}",
)
ypos = np.arange(len(bars))[::-1]
for yp, (label, val, color) in zip(ypos, bars):
    ax.barh(yp, val, height=0.56, color=color, zorder=3)
    ax.text(val + (8 if val > 0 else -8), yp, f"{val:+,.0f}", va="center",
            ha="left" if val > 0 else "right", fontsize=14, color=INK,
            fontweight="semibold" if label == "Clean" else "normal")
ax.set_yticks(ypos)
ax.set_yticklabels([b[0] for b in bars], fontsize=14, color=INK)
fig.subplots_adjust(left=0.19)
ax.axvline(0, color=AXIS, linewidth=1.2)
ax.set_xlim(-260, 430)
ax.text(25, ypos[3], "Gas grew mostly by taking coal's place:\n+222 gas and −158 coal nets to only +64 TWh of fossil power",
        fontsize=12.5, color=INK_2, va="center")
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:+,.0f}" if v else "0"))
tidy(ax, ygrid=False, xgrid=True)
ax.spines["bottom"].set_visible(False)
save(fig, "03_us_who_supplied_new_demand.png")

# =============================================================================
# 4. Growth rates indexed to 2021
# =============================================================================
idx = mix.loc[2021:2025, ["wind_solar", "clean", "gas", "demand", "coal"]]
idx = idx / idx.loc[2021] * 100
lines = [("wind_solar", "Wind + solar", CLEAN_C, 3.4),
         ("clean", "All clean", CLEAN_LIGHT, 2.6),
         ("gas", "Natural gas (est.)", GAS_C, 2.4),
         ("demand", "Demand", DEMAND_LINE, 2.0),
         ("coal", "Coal (est.)", COAL_C, 2.4)]
ws_g = idx.loc[2025, "wind_solar"] - 100
fig, ax = frame(
    f"Wind and solar grew {ws_g:.0f}% since 2021; gas {idx.loc[2025, 'gas'] - 100:.0f}%, coal fell {100 - idx.loc[2025, 'coal']:.0f}%",
    "U.S. electricity generation indexed to 2021 = 100 (2020 skipped: COVID year)",
    f"{EMBER_US}; EIA U.S. coal consumption (provided). {GAS_NOTE}",
)
label_dy = {"wind_solar": 0, "clean": 3, "gas": -1, "demand": -4.5, "coal": 0}
for col, label, color, lw in lines:
    ax.plot(idx.index, idx[col], color=color, linewidth=lw, marker="o", markersize=6,
            markeredgecolor=SURFACE, markeredgewidth=1.2, label=label, zorder=3)
    end = idx[col].iloc[-1]
    ax.annotate(f"{label}  {end - 100:+.0f}%", (2025, end), xytext=(12, label_dy[col] * 3),
                textcoords="offset points", va="center", fontsize=13, color=INK,
                fontweight="semibold" if col == "wind_solar" else "normal")
ax.axhline(100, color=AXIS, linewidth=1.2, zorder=2)
ax.set_xlim(2020.85, 2026.0)
ax.set_ylim(70, 165)
ax.set_xticks(range(2021, 2026))
tidy(ax)
ax.legend(loc="upper left", frameon=False, fontsize=12, ncol=5)
save(fig, "04_us_growth_rates_indexed.png")

# =============================================================================
# 5. U.S. vs world: share of new demand covered by clean growth
# =============================================================================
us_cov = us.loc[2021:2025, "coverage_recomputed_pct"]
w_cov = world.loc[2021:2025, "clean_covers_new_demand_pct"]
fig, ax = frame(
    f"Clean covered {us_cov.loc[2025]:.0f}% of new U.S. demand in 2025, vs {w_cov.loc[2025]:.0f}% worldwide",
    "New clean power as a % of new electricity demand (100% = clean covered all of it)",
    "Ember country-year electricity (provided); world = same 91 countries every year.",
)
x = np.arange(5)
ax.bar(x - bw / 2 - 0.01, w_cov.values, bw, color=CLEAN_LIGHT, label="World", zorder=3)
ax.bar(x + bw / 2 + 0.01, np.nan_to_num(us_cov.values), bw, color=CLEAN_C, label="United States", zorder=3)
for i, yr in enumerate(range(2021, 2026)):
    ax.text(i - bw / 2 - 0.01, w_cov.loc[yr] + 3, f"{w_cov.loc[yr]:.0f}%", ha="center", fontsize=12, color=INK_2)
    if np.isnan(us_cov.loc[yr]):
        ax.text(i + bw / 2 + 0.01, 4, "U.S. demand\nfell", ha="center", fontsize=10.5, color=MUTED)
    else:
        ax.text(i + bw / 2 + 0.01, us_cov.loc[yr] + 3, f"{us_cov.loc[yr]:.0f}%", ha="center", fontsize=12,
                color=INK, fontweight="semibold" if yr == 2025 else "normal")
ax.axhline(100, color=INK_2, linewidth=1.2, linestyle=(0, (4, 3)), zorder=4)
ax.text(-0.55, 103, "100%: all new demand met by clean power", fontsize=11.5, color=INK_2, va="bottom")
ax.set_xticks(x)
ax.set_xticklabels(range(2021, 2026))
ax.set_ylim(0, 130)
ax.set_yticks(range(0, 121, 20))
ax.set_yticklabels([f"{v}%" for v in range(0, 121, 20)])
ax.legend(loc="upper left", frameon=False, fontsize=12, ncol=2, bbox_to_anchor=(0, 1.08))
tidy(ax)
save(fig, "05_us_vs_world_coverage.png")

# =============================================================================
# 6. Coal follows gas (small multiples, no dual axis)
# =============================================================================
cg = coal_gas.copy()
be = round(cg.loc[2022:2025, "breakeven_gas_usd_per_mcf"].mean() * 20) / 20   # nearest $0.05
fig, (a1, a2) = frame(
    "U.S. coal burn rises when gas gets expensive",
    f"Coal is the cheaper fuel when gas costs more than about ${be:.2f} per thousand cubic feet",
    "EIA natural gas price paid by power plants (third dataset, Oct 2026 release); EIA U.S. coal consumption, electric power sector (provided). "
    "Break-even uses 2022–25 coal prices and typical plant efficiency.",
    nrows=2, ncols=1, sharex=True,
)
fig.subplots_adjust(hspace=0.32)
x = cg.index.values
a1.bar(x, cg["gas_price_usd_per_mcf"], width=0.55, color=GAS_C, zorder=3)
for yr, v in cg["gas_price_usd_per_mcf"].items():
    a1.text(yr, v + 0.2, f"${v:.2f}", ha="center", fontsize=12, color=INK)
a1.axhline(be, color=INK_2, linewidth=1.2, linestyle=(0, (4, 3)), zorder=4)
a1.text(2025.38, be, f"Break-even\n≈${be:.2f}", fontsize=11.5, color=INK_2, va="center")
a1.set_ylim(0, 8.8)
a1.set_yticks([0, 2, 4, 6, 8])
a1.set_yticklabels(["$0", "$2", "$4", "$6", "$8"])
a1.set_title("Gas price paid by power plants, $ per thousand cubic feet", loc="left", fontsize=13, color=INK_2, pad=8)
tidy(a1)
rose = cg["coal_burn_change_mtons"] > 0
a2.bar(x, cg["consumption_mtons"], width=0.55, color=np.where(rose, COAL_C, DEMAND_C), zorder=3)
for yr, v in cg["consumption_mtons"].items():
    chg_v = cg.loc[yr, "coal_burn_change_mtons"]
    lab = f"{v:.0f}" + ("" if np.isnan(chg_v) else f"  ({chg_v:+.0f})")
    a2.text(yr, v + 12, lab, ha="center", fontsize=12, color=INK, fontweight="semibold" if rose.loc[yr] else "normal")
a2.set_ylim(0, 600)
a2.set_title("Coal burned by U.S. power plants, million short tons (dark = rose from prior year)",
             loc="left", fontsize=13, color=INK_2, pad=8)
a2.text(2022.35, 545, "2022 exception: gas peaked, but coal stockpiles were near their lowest (69 days)",
        ha="left", fontsize=11, color=INK_2)
a2.set_xticks(x)
tidy(a2)
fig.subplots_adjust(top=0.78)
save(fig, "06_coal_follows_gas.png")

# =============================================================================
# 7. Coal's lower peaks
# =============================================================================
c = coal_us["consumption_mtons"]
peak1, peak2 = c.loc[2021], c.loc[2025]
fig, ax = frame(
    f"Coal's 2025 rebound peaked {abs(peak2 / peak1 - 1) * 100:.0f}% below 2021: {peak2:.0f}M tons vs {peak1:.0f}M",
    "Coal burned by U.S. power plants, million short tons",
    "EIA U.S. coal consumption and quality (provided), U.S. total, electric power sector.",
)
ax.plot(c.index, c.values, color=COAL_C, linewidth=3, marker="o", markersize=8,
        markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=3)
for yr in c.index:
    is_peak = yr in (2021, 2025)
    ax.text(yr, c.loc[yr] + (14 if yr != 2024 else -30), f"{c.loc[yr]:.0f}", ha="center", fontsize=13,
            color=INK, fontweight="semibold" if is_peak else "normal")
ax.hlines(peak1, 2021, 2025.15, color=INK_2, linewidth=1.2, linestyle=(0, (4, 3)), zorder=2)
ax.text(2024.0, peak1 + 12, "2021 peak level", fontsize=12, color=INK_2)
ax.annotate("", xy=(2025.2, peak2), xytext=(2025.2, peak1),
            arrowprops=dict(arrowstyle="->", color=INK, linewidth=1.4))
ax.text(2025.28, (peak1 + peak2) / 2, f"{(peak2 / peak1 - 1) * 100:.0f}%\nvs 2021\npeak", fontsize=13,
        color=INK, va="center", fontweight="semibold")
ax.set_xlim(2019.7, 2025.75)
ax.set_ylim(0, 600)
ax.set_xticks(c.index)
tidy(ax)
save(fig, "07_coal_lower_peaks.png")

# =============================================================================
# 8. 2025 rebound was weak (three small panels, 2024 vs 2025)
# =============================================================================
pairs = [
    ("Coal burned", "consumption_mtons", "M tons", "{:.0f}"),
    ("Price paid for coal", "price_usd_per_ton", "$ per ton", "${:.2f}"),
    ("Stockpile", "stock_days_of_burn", "days of burn", "{:.0f}"),
]
fig, axes = frame(
    "Coal's 2025 rebound was weak: prices fell and stockpiles were drained",
    "U.S. power plants, 2024 vs 2025",
    "EIA U.S. coal consumption and quality (provided), U.S. total, electric power sector. "
    "Stockpile days = year-end stocks / daily burn.",
    nrows=1, ncols=3,
)
fig.subplots_adjust(wspace=0.35)
for ax, (title, col, unit, fmt) in zip(axes, pairs):
    v24, v25 = coal_us.loc[2024, col], coal_us.loc[2025, col]
    pct = (v25 / v24 - 1) * 100
    ax.bar([0, 1], [v24, v25], width=0.6, color=[DEMAND_C, COAL_C], zorder=3)
    for xi, v in zip([0, 1], [v24, v25]):
        ax.text(xi, v * 1.02, fmt.format(v), ha="center", fontsize=14, color=INK)
    ax.set_title(title, loc="left", fontsize=15, color=INK, fontweight="semibold", pad=26)
    ax.text(0, 1.03, f"{unit}  ·  {pct:+.0f}%", transform=ax.transAxes, fontsize=13, color=INK_2)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["2024", "2025"])
    ax.set_ylim(0, max(v24, v25) * 1.18)
    ax.set_yticks([])
    tidy(ax, ygrid=False)
gap = coal_us.loc[2025, "receipts_minus_burn_tons"] / 1e6
fig.text(0.07, 0.085, f"Plants burned {abs(gap):.0f}M tons more than they received in 2025 — they used up stockpiles instead of buying more.",
         fontsize=13, color=INK_2)
fig.subplots_adjust(bottom=0.17, top=0.74)
save(fig, "08_weak_2025_rebound.png")

# =============================================================================
# 9. States quitting coal
# =============================================================================
st = states.copy()
count = st.groupby("year")["burns_coal"].sum()
burned_2020 = set(st.loc[st["year"].eq(2020) & st["burns_coal"], "loc"])
burned_2025 = set(st.loc[st["year"].eq(2025) & st["burns_coal"], "loc"])
quit_ = st[st["loc"].isin(burned_2020 - burned_2025)][["loc", "loc_name"]].drop_duplicates()
quit_year = (st[st["loc"].isin(quit_["loc"]) & st["burns_coal"]].groupby("loc")["year"].max() + 1)
fig, ax = frame(
    f"{len(quit_)} states stopped burning coal for power since 2020",
    "Number of states (incl. DC) whose power plants burned any coal",
    "EIA U.S. coal consumption and quality (provided), state rows, electric power sector (Puerto Rico excluded).",
)
ax.bar(count.index, count.values, width=0.45, color=[COAL_C] * len(count), zorder=3)
for yr, v in count.items():
    ax.text(yr, v + 0.4, f"{v}", ha="center", fontsize=14, color=INK)
quit_ = quit_.assign(first_year=quit_["loc"].map(quit_year)).sort_values(["first_year", "loc_name"])
names = ", ".join(f"{r.loc_name} ({r.first_year})" for r in quit_.itertuples())
ax.text(2020 - 0.3, 52.5, f"Stopped (first year with no coal): {names}", fontsize=12.5, color=INK_2)
ax.set_ylim(0, 55)
ax.set_yticks([0, 10, 20, 30, 40, 50])
ax.set_xticks(count.index)
tidy(ax)
save(fig, "09_states_quitting_coal.png")

# =============================================================================
# 10. RISK: U.S. clean growth can stall and still trails demand
# =============================================================================
uc = us.loc[2021:2025, ["demand_change_twh", "clean_change_twh"]]
fig, ax = frame(
    f"Risk: U.S. clean growth can stall, as in 2023 (+{uc.loc[2023, 'clean_change_twh']:.0f} TWh)",
    "Yearly change in U.S. electricity, TWh. In every year demand grew, clean growth fell short of it",
    EMBER_US + ".",
)
x = np.arange(len(uc))
ax.bar(x - bw / 2 - 0.01, uc["demand_change_twh"], bw, color=DEMAND_C, label="Demand change", zorder=3)
ax.bar(x + bw / 2 + 0.01, uc["clean_change_twh"], bw, color=CLEAN_C, label="Clean power change", zorder=3)
for i, yr in enumerate(uc.index):
    d, cl = uc.loc[yr, "demand_change_twh"], uc.loc[yr, "clean_change_twh"]
    ax.text(i - bw / 2 - 0.01, d + (4 if d >= 0 else -12), f"{d:+.0f}", ha="center", fontsize=12, color=INK_2)
    ax.text(i + bw / 2 + 0.01, cl + 4, f"{cl:+.0f}", ha="center", fontsize=12, color=INK,
            fontweight="semibold" if yr == 2023 else "normal")
ax.annotate("2023: clean added only +10 TWh\n(cause not in the data: interest rates,\nweak wind and low hydro are candidates)",
            (2 + bw / 2 + 0.1, uc.loc[2023, "clean_change_twh"] - 2), xytext=(2.6, -40), fontsize=12, color=INK, va="center",
            arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=1))
ax.axhline(0, color=AXIS, linewidth=1.2)
ax.set_xticks(x)
ax.set_xticklabels(uc.index)
ax.set_ylim(-75, 160)
ax.legend(loc="lower left", frameon=False, fontsize=12, ncol=2, bbox_to_anchor=(0, 1.0))
tidy(ax)
save(fig, "10_risk_us_clean_can_stall.png")

# =============================================================================
# 11-13 use EIA's official generation by source (Electric Power Monthly, Table 1.1)
# =============================================================================
EIA_T11 = "EIA Electric Power Monthly, Table 1.1 (net generation by energy source, all sectors; Oct 2026 release)"
epm = pd.read_csv(CLEAN / "eia_generation_annual.csv").set_index("year")

# 11. Waterfall: where America's new power came from, 2021 -> 2025 ------------
d = epm.loc[2025] - epm.loc[2021]
clean_chg = d["clean"] + d["small_solar_pv"]            # include rooftop solar
total_chg = d["total_utility_scale"] + d["small_solar_pv"]
steps = [("Clean\n(incl. rooftop solar)", clean_chg, CLEAN_C),
         ("Natural gas", d["natural_gas"], GAS_C),
         ("Coal", d["coal"], COAL_C)]
other = total_chg - sum(v for _, v, _ in steps)
steps.append(("Oil & other", other, MUTED))
fig, ax = frame(
    f"Clean energy supplied most of America's new power: +{clean_chg:.0f} of +{total_chg:.0f} TWh",
    "Change in U.S. electricity generation by source, 2021 to 2025, TWh. Gas growth mostly replaced coal",
    EIA_T11 + ". Consistent with Ember (provided): clean +302 TWh.",
)
#     Every bar starts at zero on one scale (a waterfall's floating bars confused readers).
rows11 = [("Net new U.S. power", total_chg, DEMAND_C)] + [(lab.replace("\n", " "), v, col) for lab, v, col in steps]
ypos = np.arange(len(rows11))[::-1]
for yp, (lab, v, col) in zip(ypos, rows11):
    ax.barh(yp, v, height=0.58, color=col, zorder=3)
    ax.text(v + (6 if v >= 0 else -6), yp, f"{v:+.0f}", va="center", ha="left" if v >= 0 else "right",
            fontsize=16, color=INK, fontweight="semibold" if lab.startswith(("Net", "Clean")) else "normal")
ax.set_yticks(ypos)
ax.set_yticklabels([r[0] for r in rows11], fontsize=15, color=INK)
ax.axvline(0, color=AXIS, linewidth=1.4)
fossil_net = d["natural_gas"] + d["coal"]
ax.text(20, ypos[3], f"Gas +{d['natural_gas']:.0f} and coal {d['coal']:.0f} net to only {fossil_net:+.0f} TWh:\ngas mostly took coal's place",
        fontsize=13, color=INK_2, va="center")
ax.set_xlim(-230, 430)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:+.0f}" if v else "0"))
fig.subplots_adjust(left=0.25)
tidy(ax, ygrid=False, xgrid=True)
ax.spines["bottom"].set_visible(False)
save(fig, "11_waterfall_new_power.png")

# 12. Monthly scatter: coal share vs gas price -------------------------------
mth = pd.read_csv(CLEAN / "coal_vs_gas_monthly.csv")
mth["year"] = mth["month"].str[:4].astype(int)
r_all = np.corrcoef(mth["gas_price_usd_per_mcf"], mth["coal_share_of_coal_gas_pct"])[0, 1]
hi_ = mth[mth["gas_price_usd_per_mcf"] >= be]["coal_share_of_coal_gas_pct"].mean()
lo_ = mth[mth["gas_price_usd_per_mcf"] < be]["coal_share_of_coal_gas_pct"].mean()
fig, ax = frame(
    f"Coal only wins when gas is expensive: {hi_:.0f}% share above ${be:.2f} gas vs {lo_:.0f}% below",
    f"Each dot is one month (Jan 2024 – Jul 2026). Coal's share of coal + gas power vs gas price paid by power plants. Correlation {r_all:.2f}",
    EIA_T11 + "; EIA natural gas electric power price, monthly (third dataset).",
)
shade = {2024: 0.35, 2025: 0.65, 2026: 1.0}
for yr, grp in mth.groupby("year"):
    ax.scatter(grp["gas_price_usd_per_mcf"], grp["coal_share_of_coal_gas_pct"], s=90,
               color=COAL_C, alpha=shade[yr], edgecolor=SURFACE, linewidth=1.2, zorder=3, label=str(yr))
fit = np.polyfit(mth["gas_price_usd_per_mcf"].clip(upper=7), mth["coal_share_of_coal_gas_pct"], 1)
xs = np.linspace(2, 7, 50)
ax.plot(xs, np.polyval(fit, xs), color=INK_2, linewidth=1.2, zorder=2)
ax.axvline(be, color=GAS_C, linewidth=1.6, linestyle=(0, (4, 3)), zorder=2)
ax.text(be + 0.08, 35.6, f"Break-even ≈ ${be:.2f}:\ncoal cheaper to the right", fontsize=12, color=INK, va="top")
storm = mth[mth["month"].eq("2026-01")].iloc[0]
ax.annotate("Jan 2026 winter storm", (storm["gas_price_usd_per_mcf"], storm["coal_share_of_coal_gas_pct"]),
            xytext=(-150, 18), textcoords="offset points", fontsize=11.5, color=INK_2,
            arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=1))
ax.set_xlim(1.8, 11)
ax.set_ylim(20, 36)
ax.set_xlabel("Gas price paid by power plants, $ per thousand cubic feet", fontsize=12.5)
ax.set_ylabel("Coal share of coal + gas power, %", fontsize=12.5)
ax.legend(loc="lower right", frameon=False, fontsize=12, title="Year", title_fontsize=12)
tidy(ax, xgrid=True)
ax.spines["left"].set_visible(True)
ax.spines["left"].set_color(AXIS)
fig.subplots_adjust(bottom=0.19)
save(fig, "12_coal_follows_gas_monthly.png")

# 13. 2026 year-to-date vs 2025 ---------------------------------------------
t11 = pd.read_excel(ROOT / "data" / "raw" / "eia_epm_table_1_1_net_generation_by_source.xlsx", header=None)
ytd_lab = t11[0].fillna("").astype(str).str.strip()
ytd_i = ytd_lab[ytd_lab.str.startswith("Year to Date")].index[0]
y25, y26 = t11.loc[ytd_i + 2], t11.loc[ytd_i + 3]
check_years = (str(y25[0]).strip(), str(y26[0]).strip())
assert check_years == ("2025", "2026"), check_years
items = [("Solar (utility-scale)", 8, CLEAN_C), ("Wind & other renewables", 9, CLEAN_C),
         ("Natural gas", 4, GAS_C), ("Total generation", 12, DEMAND_C),
         ("Nuclear", 6, CLEAN_LIGHT), ("Coal", 1, COAL_C)]
vals = [(lab, (float(y26[c]) / float(y25[c]) - 1) * 100, col) for lab, c, col in items]
fig, ax = frame(
    "2026 so far: coal fell 9% while solar grew 20%",
    "Change in U.S. generation, January–August 2026 vs January–August 2025, %",
    EIA_T11 + ", year-to-date rows. 2026 data is preliminary.",
)
ypos = np.arange(len(vals))[::-1]
for yp, (lab, v, col) in zip(ypos, vals):
    ax.barh(yp, v, height=0.56, color=col, zorder=3)
    ax.text(v + (0.4 if v >= 0 else -0.4), yp, f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right",
            fontsize=14, color=INK, fontweight="semibold" if lab in ("Coal", "Solar (utility-scale)") else "normal")
ax.set_yticks(ypos)
ax.set_yticklabels([v[0] for v in vals], fontsize=14, color=INK)
ax.axvline(0, color=AXIS, linewidth=1.2)
ax.set_xlim(-13, 25)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:+.0f}%" if v else "0"))
fig.subplots_adjust(left=0.22)
tidy(ax, ygrid=False, xgrid=True)
ax.spines["bottom"].set_visible(False)
save(fig, "13_2026_ytd.png")

# =============================================================================
# 14. U.S. generation by source, stacked: history (EIA Table 1.1) + EIA AEO projection
# =============================================================================
#     Projection file (optional): data/raw/eia_aeo2026_table8_electricity.xlsx
#     from https://www.eia.gov/outlooks/aeo/excel/aeotab8.xlsx
hist = epm.loc[2016:2025].copy()
hist["solar_all"] = hist["solar_utility"] + hist["small_solar_pv"]
#     Three roles only: every clean source (nuclear, hydro, wind & other renewables, solar) is one layer.
hist["clean_all"] = hist["nuclear"] + hist["hydro"] + hist["wind_and_other_renewables"] + hist["solar_all"]
hist["oil_other"] = hist["petroleum_liquids"] + hist["petroleum_coke"] + hist["other_fossil_gas"] + hist["other"]
layers = [("coal", "Coal", COAL_C),
          ("oil_other", "Oil & other", "#a8a69f"),
          ("natural_gas", "Natural gas", GAS_C),
          ("clean_all", "Clean energy", CLEAN_C)]
fig, ax = frame(
    "Clean energy is the growth, gas the backbone, coal the backup",
    "U.S. electricity generation by source, TWh, 2016–2025 (actual). Clean = nuclear, hydro, wind and solar",
    EIA_T11 + ". Solar includes small-scale (rooftop) estimates.",
)
yrs = hist.index.values
ax.stackplot(yrs, *[hist[c].values for c, _, _ in layers], colors=[col for _, _, col in layers],
             edgecolor=SURFACE, linewidth=0.8, zorder=3)
cum = 0
for c, lab, col in layers:
    v = hist.loc[2025, c]
    if v > 120:
        ax.text(2025.12, cum + v / 2, f"{lab}  {v:,.0f}", va="center", fontsize=13.5, color=INK,
                fontweight="semibold" if c == "clean_all" else "normal")
    cum += v
coal_drop = (hist.loc[2025, "coal"] / hist.loc[2016, "coal"] - 1) * 100
clean_up = (hist.loc[2025, "clean_all"] / hist.loc[2016, "clean_all"] - 1) * 100
gas_up = (hist.loc[2025, "natural_gas"] / hist.loc[2016, "natural_gas"] - 1) * 100
solar_x = hist.loc[2025, "solar_all"] / hist.loc[2016, "solar_all"]
lab_y = lambda c: hist.loc[2016, [l[0] for l in layers][: [l[0] for l in layers].index(c)]].sum() + hist.loc[2016, c] / 2
chg16 = hist.loc[2025] - hist.loc[2016]
ax.text(2016.2, lab_y("coal"), f"Coal {chg16['coal']:+,.0f} TWh since 2016", va="center", fontsize=14, color=SURFACE, fontweight="semibold", zorder=4)
ax.text(2016.2, lab_y("natural_gas"), f"Gas {chg16['natural_gas']:+,.0f} TWh, mostly replacing coal", va="center", fontsize=14, color=INK, fontweight="semibold", zorder=4)
ax.text(2016.2, lab_y("clean_all"), f"Clean {chg16['clean_all']:+,.0f} TWh (solar grew {solar_x:.0f}×)", va="center", fontsize=14, color=SURFACE, fontweight="semibold", zorder=4)
ax.set_xlim(2016, 2027.4)
ax.set_ylim(0, 5200)
ax.set_xticks(range(2016, 2026, 1))
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
tidy(ax)
save(fig, "14_us_generation_stacked.png")
print(f"solar grew {solar_x:.1f}x since 2016")

# =============================================================================
# 15. Same three roles, actual 2016-2025 + EIA AEO2026 projection to 2050
# =============================================================================
#     Source: EIA Annual Energy Outlook 2026, Table 8, Counterfactual Baseline case (cb2026),
#     "Total Net Electricity Generation by Fuel" (all sectors, incl. end-use/rooftop).
#     https://www.eia.gov/outlooks/aeo/excel/aeotab8.xlsx
aeo_raw = pd.read_excel(RAW_AEO := ROOT / "data" / "raw" / "eia_aeo2026_table8_electricity.xlsx", header=None)
codes = aeo_raw[0].fillna("").astype(str)
hdr_i = aeo_raw.index[aeo_raw[2].astype(str).str.strip().eq("2025")][0]
year_cols = {c: int(float(v)) for c, v in aeo_raw.loc[hdr_i].items()
             if str(v).replace(".0", "").strip().isdigit() and 2025 <= float(v) <= 2050}
aeo_rows = {"coal": "ESD000:xx_CoalInSocks", "petroleum": "ESD000:xx_Petroleum",
            "natural_gas": "ESD000:xx_NaturalGas", "nuclear": "ESD000:xx_NuclearPower",
            "renewables": "ESD000:xx_RenewableSour", "hydrogen": "ESD000:xx_Hydrogen",
            "other": "ESD000:xx_OtherWithPump", "total": "ESD000:ga_TotalElectric"}
aeo = pd.DataFrame({k: aeo_raw.loc[codes.eq(code).idxmax(), list(year_cols)].astype(float).values
                    for k, code in aeo_rows.items()}, index=list(year_cols.values()))
aeo["clean_all"] = aeo["nuclear"] + aeo["renewables"]
aeo["oil_other"] = aeo["petroleum"] + aeo["hydrogen"] + aeo["other"]
assert abs(aeo[["coal", "oil_other", "natural_gas", "clean_all"]].sum(axis=1) - aeo["total"]).max() < 1, "AEO parts do not sum"
aeo.round(1).to_csv(CLEAN / "eia_aeo2026_generation_projection.csv")


cols = [col for _, _, col in layers]
AEO_SRC = ("EIA Annual Energy Outlook 2026, Table 8, Counterfactual Baseline (NEMS model; laws and regulations as of Dec 2025, "
           "incl. 2024 power-plant emission rules that EPA has proposed to repeal)")
for H in (2030, 2050):
    proj = pd.concat([hist.loc[[2025], ["coal", "oil_other", "natural_gas", "clean_all"]],
                      aeo.loc[2026:H, ["coal", "oil_other", "natural_gas", "clean_all"]]])
    end = aeo.loc[H]
    tot = end[["coal", "oil_other", "natural_gas", "clean_all"]].sum()
    share = lambda c: end[c] / tot * 100
    dH = proj.loc[H] - proj.loc[2025]
    if H == 2030:
        title = (f"Through 2030, EIA projects clean energy {dH['clean_all']:+,.0f} TWh, "
                 f"gas {dH['natural_gas']:+,.0f}, coal {dH['coal']:+,.0f}")
    else:
        title = f"By 2050, EIA projects clean energy at {share('clean_all'):.0f}% of U.S. power, gas {share('natural_gas'):.0f}%, coal under 1%"
    fig, ax = frame(
        title,
        f"U.S. electricity generation by source, TWh. Actual 2016–2025; EIA projection 2026–{H}. Clean = nuclear, hydro, wind and solar",
        "Actual: " + EIA_T11 + ". Projection: " + AEO_SRC + ".",
    )
    ax.stackplot(hist.index.values, *[hist[c].values for c, _, _ in layers], colors=cols,
                 edgecolor=SURFACE, linewidth=0.8, zorder=3)
    ax.stackplot(proj.index.values, *[proj[c].values for c, _, _ in layers], colors=cols, alpha=0.45,
                 edgecolor=SURFACE, linewidth=0.8, zorder=3)
    top = 5600 if H == 2030 else 7000
    ax.axvline(2025, color=INK_2, linewidth=1.3, linestyle=(0, (2, 3)), zorder=4)
    ax.text(2025.25, top * 0.955, "EIA projection →", fontsize=14, color=INK_2, va="center")
    ax.text(2024.75, top * 0.955, "← Actual", fontsize=14, color=INK_2, va="center", ha="right")
    cum = 0
    for c, lab, col in layers:
        v = proj.loc[H, c]
        if v > 150:
            ax.text(H + (0.25 if H == 2030 else 0.4), max(cum + v / 2, 330 if H == 2030 else 0), f"{lab}\n{v:,.0f} TWh ({share(c):.0f}%)", va="center",
                    fontsize=13, color=INK, fontweight="semibold" if c == "clean_all" else "normal", linespacing=1.3)
        cum += v
    if H == 2050:
        ax.annotate(f"Coal: {end['coal']:,.0f} TWh in 2050", (2050, end["coal"] + 10), xytext=(2043.2, 650),
                    fontsize=12.5, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=1))
    ax.text(2016.3, lab_y("coal"), "Coal", va="center", fontsize=14, color=SURFACE, fontweight="semibold", zorder=5)
    ax.text(2016.3, lab_y("natural_gas"), "Natural gas", va="center", fontsize=14, color=INK, fontweight="semibold", zorder=5)
    ax.text(2016.3, lab_y("clean_all"), "Clean energy", va="center", fontsize=14, color=SURFACE, fontweight="semibold", zorder=5)
    ax.set_xlim(2016, H + (3.6 if H == 2030 else 6.5))
    ax.set_ylim(0, top)
    ax.set_xticks(list(range(2016, 2031, 2)) if H == 2030 else [2016, 2020, 2025, 2030, 2035, 2040, 2045, 2050])
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    tidy(ax)
    fig.subplots_adjust(bottom=0.15)
    save(fig, f"15_us_generation_projection_{H}.png")
    print(H, {c: round(share(c), 1) for c in ["coal", "natural_gas", "clean_all"]}, "change vs 2025", dH.round(0).to_dict())

# =============================================================================
# 16. Coal's 2025 bump and 2026 fade, month by month (EIA Table 1.1)
# =============================================================================
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
mon = pd.read_csv(CLEAN / "eia_generation_monthly.csv")
gas_m2 = pd.read_csv(ROOT / "data" / "raw" / "eia_gas_price_power_monthly_2020_2026.csv")
mon = mon.merge(gas_m2, on="month", how="left")
piv = mon.pivot_table(index="month_num", columns="year", values="coal")
n26 = int(piv[2026].notna().sum())
below = int((piv[2026] < piv[2025]).sum())
ytd25, ytd26 = piv.loc[1:n26, 2025].sum(), piv.loc[1:n26, 2026].sum()
bump = (piv[2025].sum() / piv[2024].sum() - 1) * 100
fig, ax = frame(
    f"Coal's 2025 bump is fading: 2026 coal power is below 2025 in {below} of {n26} months",
    f"U.S. coal generation by month, TWh. 2025 ran {bump:+.0f}% above 2024; Jan–{MONTHS[n26 - 1][:3]} 2026 is {(ytd26 / ytd25 - 1) * 100:+.1f}% vs the same months of 2025",
    EIA_T11 + "; gas prices: EIA natural gas electric power price, monthly (third dataset). 2026 data is preliminary.",
)
xm = np.arange(1, 13)
styles = {2024: (DEMAND_C, 2.2, "2024"), 2025: (COAL_C, 3.2, "2025: the bump"), 2026: (CLEAN_C, 3.6, "2026: falling back")}
for yr, (col, lw, lab) in styles.items():
    s = piv[yr]
    ax.plot(xm[s.notna()], s.dropna().values, color=col, linewidth=lw, marker="o", markersize=6 if yr != 2024 else 4,
            markeredgecolor=SURFACE, markeredgewidth=1.2, zorder=3 + (yr - 2024), label=lab)
last = piv[2026].dropna()
ax.text(last.index[-1] + 0.18, last.iloc[-1] + 1.5, "2026: falling back", fontsize=13.5, color=CLEAN_C, fontweight="semibold", va="bottom")
ax.text(10.0, piv.loc[10:11, 2025].max() + 3.5, "2025: the bump", fontsize=13.5, color=COAL_C, fontweight="semibold", ha="center", va="bottom")
ax.text(12.15, piv.loc[12, 2025], "2025", fontsize=13.5, color=COAL_C, fontweight="semibold", va="center")
ax.text(12.15, piv.loc[12, 2024], "2024", fontsize=13.5, color=MUTED, va="center")
jan_g25 = mon.loc[mon["month"].eq("2025-01"), "gas_price_usd_per_mcf"].iloc[0]
jan_g26 = mon.loc[mon["month"].eq("2026-01"), "gas_price_usd_per_mcf"].iloc[0]
ax.annotate(f"Jan 2026: gas spiked to ${jan_g26:.2f} (winter storm),\nyet coal stayed below Jan 2025 (gas ${jan_g25:.2f})",
            (1, piv.loc[1, 2026]), xytext=(2.2, 87), fontsize=12, color=INK,
            arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=1))
ax.set_xticks(xm)
ax.set_xticklabels([m[:3] for m in MONTHS])
ax.set_xlim(0.6, 12.9)
ax.set_ylim(30, 95)
tidy(ax)
save(fig, "16_coal_bump_and_fade_monthly.png")
print("coal 2026 below 2025 in", below, "of", n26, "months; ytd", round((ytd26 / ytd25 - 1) * 100, 1))

# =============================================================================
# 17. Growth rates: actual 2021-2025 vs EIA projection 2025-2030 (average % per year)
# =============================================================================
cagr = lambda a, b, n: ((b / a) ** (1 / n) - 1) * 100
h = epm.copy()
h["clean_all"] = h["nuclear"] + h["hydro"] + h["wind_and_other_renewables"] + h["solar_utility"] + h["small_solar_pv"]
h["solar_all"] = h["solar_utility"] + h["small_solar_pv"]
h["total_all"] = h["total_utility_scale"] + h["small_solar_pv"]
gr = [("Solar (incl. rooftop)", cagr(h.loc[2021, "solar_all"], h.loc[2025, "solar_all"], 4), np.nan, "#5598e7"),
      ("Clean energy (all)", cagr(h.loc[2021, "clean_all"], h.loc[2025, "clean_all"], 4),
       cagr(aeo.loc[2025, "clean_all"], aeo.loc[2030, "clean_all"], 5), CLEAN_C),
      ("Total demand (generation)", cagr(h.loc[2021, "total_all"], h.loc[2025, "total_all"], 4),
       cagr(aeo.loc[2025, "total"], aeo.loc[2030, "total"], 5), DEMAND_LINE),
      ("Natural gas", cagr(h.loc[2021, "natural_gas"], h.loc[2025, "natural_gas"], 4),
       cagr(aeo.loc[2025, "natural_gas"], aeo.loc[2030, "natural_gas"], 5), GAS_C),
      ("Coal", cagr(h.loc[2021, "coal"], h.loc[2025, "coal"], 4),
       cagr(aeo.loc[2025, "coal"], aeo.loc[2030, "coal"], 5), COAL_C)]
pd.DataFrame(gr, columns=["source", "actual_2021_2025_pct_per_yr", "eia_projection_2025_2030_pct_per_yr", "color"]) \
    .drop(columns="color").round(2).to_csv(CLEAN / "growth_rates.csv", index=False)
fig, ax = frame(
    "Clean energy grows twice as fast as demand, and EIA sees the gap widening",
    "Average growth per year, %. Solid: actual 2021–2025. Faded: EIA projection 2025–2030",
    "Actual: EIA Electric Power Monthly, Table 1.1. Projection: EIA Annual Energy Outlook 2026, Table 8, Counterfactual Baseline (NEMS). "
    "Clean includes rooftop solar.",
)
ypos = np.arange(len(gr))[::-1] * 1.0
bh = 0.36
for yp, (lab, a_, p_, col) in zip(ypos, gr):
    ax.barh(yp + bh / 2 + 0.02, a_, height=bh, color=col, zorder=3)
    ax.text(a_ + (0.4 if a_ >= 0 else -0.4), yp + bh / 2 + 0.02, f"{a_:+.1f}%", va="center",
            ha="left" if a_ >= 0 else "right", fontsize=13.5, color=INK, fontweight="semibold")
    if not np.isnan(p_):
        ax.barh(yp - bh / 2 - 0.02, p_, height=bh, color=col, alpha=0.45, zorder=3)
        ax.text(p_ + (0.4 if p_ >= 0 else -0.4), yp - bh / 2 - 0.02, f"{p_:+.1f}%", va="center",
                ha="left" if p_ >= 0 else "right", fontsize=13.5, color=INK_2)
    else:
        ax.text(0.4, yp - bh / 2 - 0.02, "not split out in EIA's projection", va="center", fontsize=12, color=MUTED)
ax.set_yticks(ypos)
ax.set_yticklabels([g[0] for g in gr], fontsize=14.5, color=INK)
ax.axvline(0, color=AXIS, linewidth=1.4)
ax.set_xlim(-12, 28)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:+.0f}%" if v else "0"))
ax.legend(handles=[matplotlib.patches.Patch(color=INK_2, label="Actual 2021–2025"),
                   matplotlib.patches.Patch(color=INK_2, alpha=0.45, label="EIA projection 2025–2030")],
          loc="lower right", frameon=False, fontsize=12.5)
fig.subplots_adjust(left=0.24, bottom=0.15)
tidy(ax, ygrid=False, xgrid=True)
ax.spines["bottom"].set_visible(False)
save(fig, "17_growth_rates_actual_vs_projection.png")
print("growth", [(g[0], round(g[1], 1), None if np.isnan(g[2]) else round(g[2], 1)) for g in gr])

print("done")


# =============================================================================
# 18. Coal: short bumps when gas spikes, long-term decline (yearly bars)
# =============================================================================
gen_a = pd.read_csv(CLEAN / "eia_generation_annual.csv").set_index("year")["coal"]
gas_a = pd.read_csv(ROOT / "data" / "raw" / "eia_gas_price_power_2015_2025.csv").set_index("year")["gas_price_usd_per_mcf"]
proj = pd.read_csv(CLEAN / "eia_aeo2026_generation_projection.csv", index_col=0)["coal"].loc[2026:2030]
yrs_a = list(range(2016, 2026))
yrs_p = list(proj.index)
fall = 1 - gen_a.loc[2025] / gen_a.loc[2016]
fig, ax = frame(
    f"Coal only bumps up when gas spikes; the long-term trend is down {fall:.0%} since 2016",
    "U.S. coal power generation, TWh per year. Dark: actual. Faded: EIA projection",
    "Actual: EIA Electric Power Monthly, Table 1.1. Gas price paid by power plants: EIA (third dataset). "
    "Projection: EIA Annual Energy Outlook 2026, Table 8, Counterfactual Baseline. 2026 Jan–Aug from Table 1.1 (preliminary).",
)
bw = 0.66
ax.bar(yrs_a, gen_a.loc[yrs_a].values, bw, color=COAL_C, zorder=3, label="Actual")
ax.bar(yrs_p, proj.values, bw, color=COAL_C, alpha=0.35, zorder=3, label="EIA projection")
for y in yrs_a:
    ax.text(y, gen_a.loc[y] + 18, f"{gen_a.loc[y]:,.0f}", ha="center", fontsize=11.5, color=INK_2, zorder=5,
            bbox=dict(boxstyle="square,pad=0.15", fc=SURFACE, ec="none"))
for y in yrs_p:
    ax.text(y, proj.loc[y] + 18, f"{proj.loc[y]:,.0f}", ha="center", fontsize=11.5, color=MUTED)
# trend line through the actual years, extended to 2030
k, b0 = np.polyfit(yrs_a, gen_a.loc[yrs_a].values, 1)
xs = np.array([2015.6, 2025.4])
ax.plot(xs, k * xs + b0, color=INK, linewidth=1.8, linestyle=(0, (5, 4)), zorder=2.5)
ax.text(2022.35, 1215, f"Long-term trend (dashed):\nabout {k:,.0f} TWh a year", fontsize=12.5, color=INK, ha="left", va="center")
# the two bumps
for y in (2021, 2025):
    chg = gen_a.loc[y] / gen_a.loc[y - 1] - 1
    ax.annotate(f"Bump +{chg:.0%}\ngas \\${gas_a.loc[y-1]:.2f} → \\${gas_a.loc[y]:.2f}",
                (y, gen_a.loc[y] + 60), xytext=(y, gen_a.loc[y] + 250), ha="center", fontsize=12.5,
                color=GAS_C, fontweight="semibold",
                arrowprops=dict(arrowstyle="-|>", color=GAS_C, linewidth=1.3))
ax.text(2026.15, proj.loc[2026] + 85, "2026 so far:\n−8.7%", ha="center", fontsize=12, color=CLEAN_C, fontweight="semibold")
ax.axvline(2025.5, color=MUTED, linewidth=1, linestyle=":", zorder=2)
ax.set_xticks(yrs_a + yrs_p)
ax.set_xticklabels([str(y) for y in yrs_a + yrs_p])
ax.set_xlim(2015.4, 2030.6)
ax.set_ylim(0, 1450)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
ax.legend(loc="upper right", frameon=False, fontsize=12, ncol=2, bbox_to_anchor=(1, 1.08))
tidy(ax)
save(fig, "18_coal_bumps_not_comeback.png")
