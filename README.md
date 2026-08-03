# Daily Options Flow Scanner

A powerful Python command-line utility that ingests CSV exports from **Barchart Premier** and filters daily options flow data using a proprietary, multi-signal trading rubric. 

The scanner aggregates data across multiple Barchart reports to flag two primary actionable trading signals:
* **Signal 1:** Panic Covering
* **Signal 2:** Aggressive Buy-to-Open

## Features
- Intelligently dedups Barchart's snapshot flow rows.
- Cross-references flow data with liquid names automatically extracted from the *Most Active* options list.
- Calculates and presents deep context such as underlying price movement, Volume/OI ratios, and total OI change.
- Exports matched candidates to both a cleanly formatted **CSV file** and an easy-to-read **Text Report**.

## Requirements
- Python 3.7+
- No external packages (runs exclusively on the Python standard library!)

## Usage

Place your downloaded Barchart Premier CSV exports into an `inputs/` folder, then run the tool providing the file paths as arguments. 

```cmd
python analyze_flow.py ^
    --active inputs/most-active-stock-options-YYYY-MM-DD.csv ^
    --flow inputs/options-flow-YYYY-MM-DD.csv ^
    --decoi inputs/stocks-decrease-change-in-open-interest-YYYY-MM-DD.csv ^
    --unusual inputs/unusual-stock-options-activity-YYYY-MM-DD.csv ^
    --out outputs/flagged-YYYY-MM-DD.csv
```

> **Note:** A `run_scanner.bat` file is included as a convenience wrapper for running the script effortlessly on Windows. 

### Optional Flags
You can fine-tune the thresholds for filtering by passing the following parameters:
- `--liquidity-min` (Default: `10000`): Minimum options volume for the underlying stock to be considered for screening.
- `--premium-min` (Default: `50000`): Minimum premium (in dollars) an order must cost to qualify for Signal 2.
- `--move-min` (Default: `3`): Minimum required % price move in the underlying stock for Signal 1.

## Documentation
For more details regarding the theory behind the scanner's actionable signals, please see the [Signals & Rubric](docs/SIGNALS_RUBRIC.md) guide in the `docs` folder.
