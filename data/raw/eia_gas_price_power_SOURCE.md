# Source: natural gas price paid by U.S. power plants (third dataset)

- **Series:** U.S. Natural Gas Electric Power Price, annual (EIA series N3045US3)
- **Publisher:** U.S. Energy Information Administration (EIA)
- **Page:** https://www.eia.gov/dnav/ng/hist/n3045us3a.htm
- **Excel download:** https://www.eia.gov/dnav/ng/hist_xls/N3045US3a.xls
- **Units:** dollars per thousand cubic feet ($/Mcf), delivered to electric power consumers
- **Release used:** October 30, 2026 (next release November 30, 2026)
- **Retrieved:** November 4, 2026

## How it was collected

The values were read from the EIA page above and typed into
`eia_gas_price_power_2015_2025.csv`. The automated download was blocked in the
environment used, so anyone can verify the file by downloading the Excel link
above and comparing the annual values.

EIA revises recent years: the 2025 value was $4.02 in an earlier release and
$4.01 in the October 30, 2026 release. Re-check before final submission.

## Monthly version

`eia_gas_price_power_monthly_2020_2026.csv` holds the monthly values of the
same series (January 2020 to July 2026), read from
https://www.eia.gov/dnav/ng/hist/n3045us3m.htm on November 4, 2026. Note the
weather spikes: February 2021 ($18.06, Winter Storm Uri) and January 2026
($10.50). To use it for the coal-gas test, pair it with EIA's monthly coal and
gas generation from Electric Power Monthly Table 1.1:
https://www.eia.gov/electricity/monthly/xls/table_1_01.xlsx

## Why this dataset

The provided EIA coal data shows power-plant coal burn rising and falling year
to year. Power plants choose between coal and gas, so the gas price they pay
is the most direct explanation for those swings. It matches the coal data on
country (U.S.), years, buyer (power plants) and price basis (delivered).
