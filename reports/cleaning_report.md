# Data Cleaning Report

Run `python src/clean_data.py` from the repo root to rebuild everything in `data/clean/`.
Every check the script runs is logged in `data/clean/checks.txt` (all pass).

## What was wrong with the raw data and how we fixed it

### Coal (EIA)

| Problem | Fix |
|---|---|
| Data guide says "thousands of short tons", but the unit columns say plain short tons | Trusted the unit columns. U.S. power-plant coal = 415 million short tons in 2025 |
| Heat-content unit column is mislabeled ("sulfur percent") and uses two scales: power sectors in million Btu per ton (~18.8), industry/coke in Btu per pound (~10,000-14,000) | Converted all to Btu per pound (`heat_btu_per_lb`) and million Btu per ton |
| Missing values written as 0: 17 prices, 177 heat contents, 63 ash and 63 sulfur values | Set to missing (coal always has heat, ash and sulfur; a plant that burned coal paid for it). Consumption = 0 kept as a real zero |
| Geography mixes states, 10 regions, a "90" Pacific subtotal, Puerto Rico and the U.S. total | Added `geo_level`. Verified: states = regions = U.S. total exactly. Puerto Rico and "90" are outside it |
| Sectors overlap: Electric Power = Utility + IPP, and IPP = CHP + Non-CHP | Added `sector_role`. Verified both sums exactly. Use Electric Power for power plants; never add the parts to it |
| Power-sector prices missing for 2021 at the national level | Left missing; noted for charts |

### Electricity (Ember)

| Problem | Fix |
|---|---|
| Only 91 of 213 countries have 2025 data | Added `in_2025_panel`. All world and continent totals use the same 91 countries every year (93.5% of world demand) |
| Missing 2025 countries are fossil-heavy (Saudi Arabia, Indonesia, UAE, Iraq, Algeria) | Disclose: the 2025 fossil decline is likely overstated |
| Coverage % is blank when demand fell | Kept blank; recomputed only when demand grew |
| No nuclear or trade-intensity column | Added `nuclear_and_other_clean_twh`, `other_renewable_twh`, `abs_trade_share_pct` |

Checks that passed: no duplicates, no negatives, clean + fossil = total generation, wind+solar <= renewables <= clean, change columns match the levels, and U.S. coal (converted to TWh) is a plausible 26-35% of U.S. fossil power.

## What the clean data shows

**World (same 91 countries every year)**
- 2025 is the first year new clean power (+870 TWh) beat new demand (+792 TWh), covering 110% of it. Fossil generation fell 96 TWh.
- Clean share rose from 38.8% (2020) to 43.8% (2025); wind + solar from 9.7% to 18.3%.
- Carbon intensity fell every year since 2021, from 491 to 452 g CO2 per kWh.

**United States**
- Demand grew about 131 TWh in both 2024 and 2025. Clean power covered 75% and then 80% of it, so fossil power still rose.
- Clean share rose from 39.8% to 43.0%.

**U.S. coal**
- Power plants burn 92% of U.S. coal. Coke plants (steelmaking) 3%, other industry 5%.
- Power-plant coal: 436M tons (2020), peak 501M (2021), low 373M (2024), 415M (2025).
- The 2025 rebound (+11%) came with a slightly lower price ($46.45 to $45.56 per ton) and a stockpile drawdown (125 to 96 days of burn; plants burned 25M tons more than they received).
- States burning coal for power: 45 (2020) to 40 (2025). Connecticut, Hawaii, New Jersey, New York and Oregon stopped.
- Steelmaking coal is a separate market: $127 to $183 per ton since 2020, versus about $46 for power-plant coal.

## Third dataset: gas price paid by U.S. power plants

**Source:** EIA "U.S. Natural Gas Electric Power Price", annual, $ per thousand cubic feet, October 30, 2026 release ([page](https://www.eia.gov/dnav/ng/hist/n3045us3a.htm)). Collection notes are in `data/raw/eia_gas_price_power_SOURCE.md`.

**Why:** Power plants choose between coal and gas, so the gas price they pay explains the swings in the provided coal data. Same country, years, buyer and delivered-price basis.

**Merged result** (`coal_vs_gas_us_power.csv`):

| Year | Coal burned (M tons) | Gas price ($/Mcf) | Cheaper fuel per MWh (est.) |
|---|---|---|---|
| 2020 | 436 | 2.49 | Gas |
| 2021 | 501 | 5.43 | Unknown (2021 coal price missing) |
| 2022 | 473 | 7.51 | Coal |
| 2023 | 387 | 3.50 | Gas |
| 2024 | 373 | 2.87 | Gas |
| 2025 | 415 | 4.01 | Coal |

- Coal burn moved in the same direction as the gas price in 4 of 5 year-on-year changes (correlation 0.82). 2022 is the exception: gas peaked but coal burn fell, as stockpiles were near their lowest (69 days).
- **Break-even:** with coal at about $2.42-2.51 per million Btu, gas becomes the more expensive fuel above roughly **$3.60 per Mcf** (about $3.50 per million Btu). Gas was above that in 2025 ($4.01), which matches coal's 2025 rebound.
- Only 5 changes, so this shows direction, not proof of cause.
- Fuel cost per MWh assumes typical plant efficiency (coal 10.7, gas 7.5 million Btu per MWh) and 1.037 million Btu per Mcf of gas. These are assumptions, not data.

## Files

| File | What it is |
|---|---|
| `coal_clean.csv` | Every coal row, cleaned, with `geo_level` and `sector_role` |
| `coal_us_power.csv` | U.S. power-plant coal by year, with stockpile days and price per million Btu |
| `coal_us_sectors.csv` | U.S. coal by non-overlapping sector |
| `coal_state_power.csv` | Power-plant coal by state and year |
| `electricity_clean.csv` | Every country-year row, cleaned and flagged |
| `electricity_world_panel.csv` | World totals, same 91 countries every year |
| `electricity_continent_panel.csv` | Continent totals, same 91 countries |
| `coal_vs_gas_us_power.csv` | Coal burn merged with gas price, fuel cost per MWh and break-even gas price |
| `checks.txt` | Every validation check and its result |
