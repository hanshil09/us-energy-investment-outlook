"""
SIG x BDAA Invitational - data cleaning
=======================================

Cleans the two provided datasets and writes analysis-ready tables.

Run from the repo root:
    python src/clean_data.py

Inputs  (data/raw/):
    eia_coal_consumption_quality_2020_2025.csv
    country_year_electricity_2020_2025.csv

Outputs (data/clean/):
    coal_clean.csv              every coal row, cleaned and labelled
    coal_us_power.csv           U.S. power-plant coal by year (main analysis table)
    coal_us_sectors.csv         U.S. coal by non-overlapping sector and year
    coal_state_power.csv        power-plant coal by state and year
    electricity_clean.csv       every country-year row, cleaned and flagged
    electricity_world_panel.csv world totals by year, same countries every year
    electricity_continent_panel.csv  continent totals by year, same countries
    checks.txt                  every validation check and its result
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)

checks: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    """Record a validation check; stop if it fails."""
    line = f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else "")
    checks.append(line)
    print(line)
    if not ok:
        raise AssertionError(line)


# ---------------------------------------------------------------------------
# 1. COAL (EIA)
# ---------------------------------------------------------------------------
coal_raw = pd.read_csv(RAW / "eia_coal_consumption_quality_2020_2025.csv")

# 1a. Units: confirm what the unit columns actually say.
#     The data guide says "thousands of short tons", but the unit columns say
#     plain short tons, and the U.S. total (~415M tons of power-plant coal in
#     2025) only makes sense in short tons. We trust the unit columns.
for col in ["consumption", "receipts", "stocks"]:
    units = list(coal_raw[f"{col}-units"].unique())
    check(f"coal {col} units are short tons", units == ["short tons"], ", ".join(units))
check("coal price units are $/short ton",
      list(coal_raw["price-units"].unique()) == ["dollars per short ton"])
#     The heat-content unit column is mislabelled ("average sulfur percent by
#     weight"). Values show two scales: power sectors ~18.8 (million Btu per
#     short ton) and industrial/coke ~10,000-14,000 (Btu per pound).

coal = coal_raw.rename(columns={
    "period": "year",
    "location": "loc",
    "stateDescription": "loc_name",
    "sectorDescription": "sector_name",
    "ash-content": "ash_pct",
    "heat-content": "heat_raw",
    "sulfur-content": "sulfur_pct",
    "consumption": "consumption_tons",
    "receipts": "receipts_tons",
    "stocks": "stocks_tons",
    "price": "price_usd_per_ton",
})
coal = coal.drop(columns=[c for c in coal.columns if c.endswith("-units")])

check("coal has no duplicate year-location-sector rows",
      not coal.duplicated(["year", "loc", "sector_name"]).any())
check("coal has no negative volumes or prices",
      not (coal[["consumption_tons", "receipts_tons", "stocks_tons",
                 "price_usd_per_ton"]] < 0).any().any())

# 1b. Geography level. One level must be picked before adding anything up.
REGIONS = {"NEW", "MAT", "ENC", "WNC", "SAT", "ESC", "WSC", "MTN", "PCC", "PCN"}
coal["geo_level"] = np.select(
    [coal["loc"].eq("US"),
     coal["loc"].isin(REGIONS),
     coal["loc"].eq("90"),          # "Pacific" = PCC + PCN, another subtotal
     coal["loc"].eq("PR")],         # Puerto Rico: not inside the U.S. total
    ["national", "region", "pacific_subtotal", "territory"],
    default="state",
)

# 1c. Sector level. "Electric Power" = Electric Utility + IPP, and
#     IPP = IPP CHP + IPP Non-CHP. Flag which rows are totals.
coal["sector_role"] = np.select(
    [coal["sector_name"].eq("Electric Power"),
     coal["sector_name"].eq("Independent Power Producers"),
     coal["sector_name"].isin(["IPP CHP", "IPP Non-CHP"])],
    ["power_total", "ipp_subtotal", "ipp_component"],
    default="end_use",   # Electric Utility, Coke, Other Industrial, Commercial
)

# 1d. Zeros that really mean "missing". Blank = missing, not zero, and some
#     missing values were written as 0. Coal always has heat, ash and sulfur,
#     and a plant that burned coal paid something for it.
burned = coal["consumption_tons"] > 0
zero_fixes = {
    "price_usd_per_ton": coal["price_usd_per_ton"].eq(0),
    "heat_raw": coal["heat_raw"].eq(0),
    "ash_pct": coal["ash_pct"].eq(0),
    "sulfur_pct": coal["sulfur_pct"].eq(0),
}
for col, mask in zero_fixes.items():
    checks.append(f"[FIX ] {col}: {int(mask.sum())} zeros set to missing "
                  f"({int((mask & burned).sum())} of them on rows that burned coal)")
    coal.loc[mask, col] = np.nan
#     Consumption = 0 is kept as a real zero (the plant burned no coal).

# 1e. One heat-content unit for every sector: Btu per pound.
power_sectors = coal["sector_role"].ne("end_use") | coal["sector_name"].eq("Electric Utility")
coal["heat_btu_per_lb"] = np.where(
    power_sectors,
    coal["heat_raw"] * 1_000_000 / 2_000,   # million Btu per ton -> Btu per lb
    coal["heat_raw"],
)
coal["heat_mmbtu_per_ton"] = coal["heat_btu_per_lb"] * 2_000 / 1_000_000
check("heat content is in a sensible coal range after conversion (4,000-16,000 Btu/lb)",
      coal["heat_btu_per_lb"].dropna().between(4_000, 16_000).all(),
      f"range {coal['heat_btu_per_lb'].min():.0f}-{coal['heat_btu_per_lb'].max():.0f}")
coal["price_usd_per_mmbtu"] = coal["price_usd_per_ton"] / coal["heat_mmbtu_per_ton"]
coal = coal.drop(columns="heat_raw")

# 1f. Validate the hierarchies (so nothing gets double-counted).
pivot = (coal[coal["loc"].eq("US")]
         .pivot_table(index="year", columns="sector_name", values="consumption_tons"))
ep_sum = pivot["Electric Utility"] + pivot["Independent Power Producers"]
check("Electric Power = Electric Utility + IPP (U.S., every year)",
      np.allclose(ep_sum, pivot["Electric Power"], rtol=1e-6))
ipp_sum = pivot["IPP CHP"] + pivot["IPP Non-CHP"]
check("IPP = IPP CHP + IPP Non-CHP (U.S., every year)",
      np.allclose(ipp_sum, pivot["Independent Power Producers"], rtol=1e-6))

ep = coal[coal["sector_name"].eq("Electric Power")]
us_ep = ep[ep["geo_level"].eq("national")].set_index("year")["consumption_tons"]
reg_sum = ep[ep["geo_level"].eq("region")].groupby("year")["consumption_tons"].sum()
state_sum = ep[ep["geo_level"].eq("state")].groupby("year")["consumption_tons"].sum()
check("10 regions add up to the U.S. total", np.allclose(reg_sum, us_ep, rtol=1e-6))
check("states (excl. Puerto Rico and the '90' subtotal) add up to the U.S. total",
      np.allclose(state_sum, us_ep, rtol=1e-6))

# 1g. Analysis tables.
us_power = (ep[ep["geo_level"].eq("national")]
            .set_index("year")
            [["consumption_tons", "receipts_tons", "stocks_tons", "price_usd_per_ton",
              "price_usd_per_mmbtu", "heat_btu_per_lb", "heat_mmbtu_per_ton",
              "sulfur_pct", "ash_pct"]]
            .copy())
us_power["consumption_mtons"] = us_power["consumption_tons"] / 1e6
us_power["consumption_change_pct"] = us_power["consumption_tons"].pct_change() * 100
us_power["receipts_minus_burn_tons"] = us_power["receipts_tons"] - us_power["consumption_tons"]
us_power["stock_days_of_burn"] = us_power["stocks_tons"] / (us_power["consumption_tons"] / 365)
us_power.reset_index().to_csv(CLEAN / "coal_us_power.csv", index=False)

us_sectors = (coal[coal["loc"].eq("US") &
                   coal["sector_name"].isin(["Electric Power", "Coke Plants",
                                             "Other Industrial",
                                             "Commercial and Institutional"])]
              [["year", "sector_name", "consumption_tons", "price_usd_per_ton",
                "heat_btu_per_lb", "sulfur_pct", "stocks_tons"]])
total = us_sectors.groupby("year")["consumption_tons"].transform("sum")
us_sectors = us_sectors.assign(share_of_us_coal_pct=us_sectors["consumption_tons"] / total * 100)
us_sectors.to_csv(CLEAN / "coal_us_sectors.csv", index=False)

state_power = (ep[ep["geo_level"].eq("state")]
               [["year", "loc", "loc_name", "consumption_tons", "receipts_tons",
                 "stocks_tons", "price_usd_per_ton", "heat_btu_per_lb", "sulfur_pct"]]
               .sort_values(["loc", "year"]))
state_power["burns_coal"] = state_power["consumption_tons"].fillna(0) > 0
state_power.to_csv(CLEAN / "coal_state_power.csv", index=False)

coal.to_csv(CLEAN / "coal_clean.csv", index=False)

# ---------------------------------------------------------------------------
# 2. ELECTRICITY (Ember)
# ---------------------------------------------------------------------------
elec = pd.read_csv(RAW / "country_year_electricity_2020_2025.csv")

check("electricity has no duplicate country-year rows",
      not elec.duplicated(["country", "year"]).any())
gen_cols = ["generation_twh", "demand_twh", "clean_generation_twh",
            "fossil_generation_twh", "renewable_generation_twh", "wind_solar_generation_twh"]
check("electricity has no negative generation or demand", not (elec[gen_cols] < 0).any().any())
check("clean + fossil = total generation (within 0.01 TWh)",
      np.allclose(elec["clean_generation_twh"] + elec["fossil_generation_twh"],
                  elec["generation_twh"], atol=0.01))
check("wind+solar <= renewables <= clean",
      ((elec["wind_solar_generation_twh"] <= elec["renewable_generation_twh"] + 0.01) &
       (elec["renewable_generation_twh"] <= elec["clean_generation_twh"] + 0.01)).all())

# 2a. Derived columns the raw file doesn't have.
elec["nuclear_and_other_clean_twh"] = elec["clean_generation_twh"] - elec["renewable_generation_twh"]
elec["other_renewable_twh"] = elec["renewable_generation_twh"] - elec["wind_solar_generation_twh"]
elec["abs_trade_share_pct"] = elec["net_imports_twh"].abs() / elec["demand_twh"] * 100

# 2b. The 2025 coverage problem: only part of the countries have 2025 data.
countries_by_year = elec.groupby("year")["country"].nunique()
countries_2025 = set(elec.loc[elec["year"].eq(2025), "country"])
elec["in_2025_panel"] = elec["country"].isin(countries_2025)
full_years = elec.groupby("country")["year"].nunique()
elec["has_all_6_years"] = elec["country"].map(full_years.eq(6))
share_2025 = (elec.loc[elec["year"].eq(2024) & elec["in_2025_panel"], "demand_twh"].sum() /
              elec.loc[elec["year"].eq(2024), "demand_twh"].sum() * 100)
checks.append(f"[INFO] countries per year: {countries_by_year.to_dict()}")
checks.append(f"[INFO] the {len(countries_2025)} countries with 2025 data made "
              f"{share_2025:.1f}% of 2024 world demand")
missing_big = (elec[elec["year"].eq(2024) & ~elec["in_2025_panel"]]
               .nlargest(5, "demand_twh")[["country", "demand_twh"]])
checks.append("[INFO] largest countries missing 2025 data: " +
              ", ".join(f"{r.country} ({r.demand_twh:.0f} TWh)" for r in missing_big.itertuples()))

# 2c. Year-over-year columns: check them against the levels.
elec = elec.sort_values(["country", "year"])
prev = elec.groupby("country")[["demand_twh", "clean_generation_twh"]].shift(1)
consec = elec.groupby("country")["year"].diff().eq(1)
diff_d = (elec["demand_twh"] - prev["demand_twh"] - elec["demand_change_twh"]).abs()
check("demand_change_twh matches the year-on-year difference in demand (within 0.05 TWh)",
      (diff_d[consec] < 0.05).all(), f"max gap {diff_d[consec].max():.3f}")

#     Coverage is meaningless when demand fell (dividing by a negative or zero).
#     The raw file already leaves it blank there; we keep that and recompute it.
growing = elec["demand_change_twh"] > 0
elec["coverage_recomputed_pct"] = np.where(
    growing, elec["clean_change_twh"] / elec["demand_change_twh"] * 100, np.nan)

elec.to_csv(CLEAN / "electricity_clean.csv", index=False)

# 2d. Panels: the same countries every year, so 2025 compares fairly.
panel = elec[elec["in_2025_panel"]]
sum_cols = ["generation_twh", "demand_twh", "clean_generation_twh", "fossil_generation_twh",
            "renewable_generation_twh", "wind_solar_generation_twh", "power_emissions_mtco2e"]


def add_shares(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["clean_share_pct"] = df["clean_generation_twh"] / df["generation_twh"] * 100
    df["wind_solar_share_pct"] = df["wind_solar_generation_twh"] / df["generation_twh"] * 100
    df["carbon_intensity_g_kwh"] = df["power_emissions_mtco2e"] / df["generation_twh"] * 1000
    return df


world = add_shares(panel.groupby("year")[sum_cols].sum())
for col in ["demand_twh", "clean_generation_twh", "fossil_generation_twh",
            "wind_solar_generation_twh"]:
    world[col.replace("_twh", "_change_twh")] = world[col].diff()
world["clean_covers_new_demand_pct"] = (world["clean_generation_change_twh"] /
                                        world["demand_change_twh"] * 100)
world.reset_index().to_csv(CLEAN / "electricity_world_panel.csv", index=False)

continent = add_shares(panel.groupby(["continent", "year"])[sum_cols].sum())
continent.reset_index().to_csv(CLEAN / "electricity_continent_panel.csv", index=False)

# ---------------------------------------------------------------------------
# 3. Cross-check between the two datasets
# ---------------------------------------------------------------------------
us_e = elec[elec["iso3"].eq("USA")].set_index("year")
check("U.S. appears in the electricity data for all 6 years", len(us_e) == 6)
#     Coal tons -> TWh, assuming a typical coal plant heat rate of
#     ~10,700 Btu per kWh (an assumption, not from the data).
coal_twh_est = us_power["consumption_tons"] * us_power["heat_mmbtu_per_ton"] / 10.7 / 1e6
share = coal_twh_est / us_e["fossil_generation_twh"] * 100
check("estimated U.S. coal power is a plausible share of fossil power (20-45%)",
      share.between(20, 45).all(), f"{share.round(0).to_dict()}")

# ---------------------------------------------------------------------------
# 4. THIRD DATASET: gas price paid by U.S. power plants (EIA)
# ---------------------------------------------------------------------------
#     Source and collection notes: data/raw/eia_gas_price_power_SOURCE.md
gas = pd.read_csv(RAW / "eia_gas_price_power_2015_2025.csv")
check("gas price file covers 2020-2025 with no gaps",
      set(range(2020, 2026)) <= set(gas["year"]) and gas["gas_price_usd_per_mcf"].notna().all())
check("gas prices are positive and plausible ($1-$15 per Mcf)",
      gas["gas_price_usd_per_mcf"].between(1, 15).all())

#     Assumptions (typical values, not from the provided data):
MMBTU_PER_MCF = 1.037        # EIA average heat content of delivered natural gas
COAL_HEAT_RATE = 10.7        # million Btu of coal per MWh, typical coal plant
GAS_HEAT_RATE = 7.5          # million Btu of gas per MWh, typical combined-cycle plant
checks.append(f"[INFO] assumptions: {MMBTU_PER_MCF} MMBtu per Mcf of gas; heat rates "
              f"coal {COAL_HEAT_RATE}, gas {GAS_HEAT_RATE} MMBtu/MWh")

gas["gas_price_usd_per_mmbtu"] = gas["gas_price_usd_per_mcf"] / MMBTU_PER_MCF

coal_gas = (us_power.reset_index()
            [["year", "consumption_tons", "consumption_mtons", "stock_days_of_burn",
              "price_usd_per_ton", "price_usd_per_mmbtu"]]
            .rename(columns={"price_usd_per_ton": "coal_price_usd_per_ton",
                             "price_usd_per_mmbtu": "coal_price_usd_per_mmbtu"})
            .merge(gas, on="year", how="left"))
check("every coal year has a gas price after the merge",
      coal_gas["gas_price_usd_per_mcf"].notna().all())

coal_gas["coal_fuel_cost_usd_per_mwh"] = coal_gas["coal_price_usd_per_mmbtu"] * COAL_HEAT_RATE
coal_gas["gas_fuel_cost_usd_per_mwh"] = coal_gas["gas_price_usd_per_mmbtu"] * GAS_HEAT_RATE
coal_gas["cheaper_fuel"] = np.where(
    coal_gas["coal_fuel_cost_usd_per_mwh"].isna(), "unknown (coal price missing)",
    np.where(coal_gas["coal_fuel_cost_usd_per_mwh"] < coal_gas["gas_fuel_cost_usd_per_mwh"],
             "coal", "gas"))
#     Gas price at which a typical gas plant's fuel costs the same as coal's.
coal_gas["breakeven_gas_usd_per_mmbtu"] = coal_gas["coal_fuel_cost_usd_per_mwh"] / GAS_HEAT_RATE
coal_gas["breakeven_gas_usd_per_mcf"] = coal_gas["breakeven_gas_usd_per_mmbtu"] * MMBTU_PER_MCF
coal_gas["coal_burn_change_mtons"] = coal_gas["consumption_mtons"].diff()
coal_gas["gas_price_change_usd_per_mcf"] = coal_gas["gas_price_usd_per_mcf"].diff()
coal_gas.to_csv(CLEAN / "coal_vs_gas_us_power.csv", index=False)

chg = coal_gas.dropna(subset=["coal_burn_change_mtons", "gas_price_change_usd_per_mcf"])
r_changes = np.corrcoef(chg["gas_price_change_usd_per_mcf"], chg["coal_burn_change_mtons"])[0, 1]
same_sign = int((np.sign(chg["gas_price_change_usd_per_mcf"]) ==
                 np.sign(chg["coal_burn_change_mtons"])).sum())
checks.append(f"[INFO] coal vs gas, {len(chg)} year-on-year changes: correlation {r_changes:.2f}; "
              f"coal moved the same direction as gas in {same_sign} of {len(chg)} years "
              "(direction only: too few points to prove cause)")

# ---------------------------------------------------------------------------
# 5. EIA official U.S. generation by source (Electric Power Monthly, Table 1.1)
# ---------------------------------------------------------------------------
#     https://www.eia.gov/electricity/monthly/xls/table_1_01.xlsx
#     Thousand MWh, all sectors. Annual 2016-2025; monthly Jan 2024 onward.
epm_raw = pd.read_excel(RAW / "eia_epm_table_1_1_net_generation_by_source.xlsx", header=None)
EPM_COLS = ["period", "coal", "petroleum_liquids", "petroleum_coke", "natural_gas",
            "other_fossil_gas", "nuclear", "hydro", "solar_utility", "wind_and_other_renewables",
            "pumped_storage", "other", "total_utility_scale", "small_solar_pv",
            "total_solar_pv", "total_solar"]
check("EIA Table 1.1 has the expected 16 columns", epm_raw.shape[1] == len(EPM_COLS))
epm_raw.columns = EPM_COLS
labels = epm_raw["period"].fillna("").astype(str).str.strip()

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "Sept", "October", "November", "December"]
annual_rows, monthly_rows, section, year = [], [], None, None
for i, lab in labels.items():
    if lab == "Annual Totals":
        section = "annual"
    elif lab.startswith("Year to Date") or lab.startswith("Rolling"):
        section = None
    elif lab.startswith("Year 20"):
        section, year = "monthly", int(lab.split()[1])
    elif section == "annual" and lab.isdigit():
        annual_rows.append({**epm_raw.loc[i].to_dict(), "year": int(lab)})
    elif section == "monthly" and lab in MONTHS:
        monthly_rows.append({**epm_raw.loc[i].to_dict(), "year": year, "month_num": MONTHS.index(lab) + 1})


def to_twh(df: pd.DataFrame) -> pd.DataFrame:
    num = [c for c in EPM_COLS if c != "period"]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce") / 1000   # thousand MWh -> TWh
    df["fossil"] = df[["coal", "petroleum_liquids", "petroleum_coke", "natural_gas", "other_fossil_gas"]].sum(axis=1)
    df["clean"] = df[["nuclear", "hydro", "solar_utility", "wind_and_other_renewables"]].sum(axis=1)
    base = df["total_utility_scale"]
    for k in ["coal", "natural_gas", "clean", "nuclear", "solar_utility", "wind_and_other_renewables"]:
        df[f"{k}_share_pct"] = df[k] / base * 100
    df["coal_share_of_coal_gas_pct"] = df["coal"] / (df["coal"] + df["natural_gas"]) * 100
    return df.drop(columns="period")


epm_annual = to_twh(pd.DataFrame(annual_rows)).set_index("year")
epm_monthly = to_twh(pd.DataFrame(monthly_rows))
epm_monthly["month"] = pd.to_datetime(dict(year=epm_monthly["year"], month=epm_monthly["month_num"], day=1)).dt.strftime("%Y-%m")
check("EIA annual rows cover 2016-2025", list(epm_annual.index) == list(range(2016, 2026)))
check("EIA monthly rows start January 2024 with no gaps",
      epm_monthly["month"].iloc[0] == "2024-01" and len(epm_monthly) == len(set(epm_monthly["month"])))
check("EIA sources add up to the utility-scale total (within 0.5%)",
      np.allclose(epm_annual[["fossil", "clean", "pumped_storage", "other"]].sum(axis=1),
                  epm_annual["total_utility_scale"], rtol=0.005))
epm_annual.reset_index().to_csv(CLEAN / "eia_generation_annual.csv", index=False)
epm_monthly.to_csv(CLEAN / "eia_generation_monthly.csv", index=False)

# 5a. How good was our estimate? Compare with the official numbers.
est = pd.read_csv(CLEAN / "us_power_mix_estimate.csv", index_col=0) if (CLEAN / "us_power_mix_estimate.csv").exists() else None
if est is not None:
    cmp_ = pd.DataFrame({"coal_est_twh": est["coal"], "coal_eia_twh": epm_annual["coal"],
                         "gas_est_twh": est["gas"], "gas_eia_twh": epm_annual["natural_gas"]}).loc[2020:2025]
    cmp_.round(1).to_csv(CLEAN / "estimate_vs_eia_check.csv")
    err = (cmp_["coal_est_twh"] / cmp_["coal_eia_twh"] - 1).abs().max() * 100
    checks.append(f"[INFO] our coal-TWh estimate vs EIA official: max error {err:.1f}% (2020-2025)")

# 5b. Monthly coal vs gas price.
gas_m = pd.read_csv(RAW / "eia_gas_price_power_monthly_2020_2026.csv")
coal_gas_m = epm_monthly.merge(gas_m, on="month", how="inner")
coal_gas_m[["month", "coal", "natural_gas", "coal_share_of_coal_gas_pct", "gas_price_usd_per_mcf"]] \
    .round(3).to_csv(CLEAN / "coal_vs_gas_monthly.csv", index=False)
r_m = np.corrcoef(coal_gas_m["gas_price_usd_per_mcf"], coal_gas_m["coal_share_of_coal_gas_pct"])[0, 1]
checks.append(f"[INFO] monthly ({len(coal_gas_m)} months, {coal_gas_m['month'].iloc[0]} to {coal_gas_m['month'].iloc[-1]}): "
              f"correlation of gas price with coal's share of coal+gas power = {r_m:.2f}")

(CLEAN / "checks.txt").write_text("\n".join(checks) + "\n", encoding="utf-8")
print(f"\nDone. Clean files written to {CLEAN}")
