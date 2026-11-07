# SIG x BDAA Invitational: Coal vs. Clean Energy

Investment thesis analysis using supplied Ember electricity and EIA U.S. coal data, plus delivered natural gas prices, monthly generation and an EIA projection scenario. [Download the presentation](presentations/Energy_Investment_coaldiggers_diya.pptx).

## Setup

Use Python 3.10 or newer (verified on Python 3.12). Run from this folder:

```sh
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python src/clean_data.py
python src/make_charts.py
```

## Layout

```
data/raw/      provided datasets and supplemental EIA CSVs/workbooks
data/clean/    analysis-ready tables built by src/clean_data.py
src/           code
reports/       cleaning_report.md: what was fixed and what the data shows
charts/        19 original charts built by src/make_charts.py
presentations/ supplied PowerPoint, unchanged
assets/presentation/ redesigned charts and risk/catalyst graphics
```

Rules every analysis in this repo follows:
- Coal: use `geo_level == "national"` for U.S. totals, `"state"` for states. Use the Electric Power sector for power plants; never add its parts to it.
- Electricity: compare years only within the 91-country panel (`in_2025_panel`).
- Coal volumes are in short tons, not thousands.

## Reproducibility and publication notes

An isolated build using only `src/` and `data/raw/` passed all 25 validation checks and produced all 19 charts on November 6, 2026. No API key or download is needed. Rebuilding overwrites derived tables and original charts; it does not recreate the deck or the image-edited graphics.

The Python pipeline reproduces the electricity analysis and original charts. Company financial model inputs, external capacity-chart data, and some forecast/policy source files shown in the deck are not included. The presentation graphics are separate image assets.

Demand-growth coverage measures annual changes, not clean power's share of total generation. The ratio can exceed 100%; it is not shown when demand falls. The comparison group is a fixed 91-country sample, not the full world. Delivered power-plant gas prices in $/Mcf are different from Henry Hub prices in $/MMBtu. EIA projections use the AEO2026 **Counterfactual Baseline**; inspect chart-specific clean-generation definitions before combining data.

Raw competition datasets and external charts may have redistribution restrictions; public sharing permission has not been established in this review. No blanket license is applied to third-party material. The PowerPoint contains its author's name in document metadata. No obvious credentials were found in the inspected text files.
