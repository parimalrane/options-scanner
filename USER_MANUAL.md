# Options Flow Scanner: User Manual

## 1. Overview
The Options Flow Scanner is a highly-specialized, institutional-grade quantitative tool designed to track anomalies in the options market. By aggressively targeting massive shifts in Open Interest (OI) relative to historical snapshots, the scanner uncovers hidden institutional positioning, smart-money sweeps, and "dark" accumulation that retail traders normally miss. 

---

## 2. Prerequisites & Setup
The scanner operates entirely locally and algorithmically processes data exports gathered directly from Barchart. To run a daily scan, you must place the appropriately dated `.csv` files into the `inputs/` folder.

**Required Stock Input Files:**
- `most-active-stock-options-MM-DD-YYYY.csv`
- `stocks-decrease-change-in-open-interest-MM-DD-YYYY.csv`
- `stocks-increase-change-in-open-interest-MM-DD-YYYY.csv`
- `unusual-stock-options-activity-MM-DD-YYYY.csv`

**Optional ETF Input Files (If running ETFs):**
- `most-active-etf-options-MM-DD-YYYY.csv`
- `etfs-decrease-change-in-open-interest-MM-DD-YYYY.csv`
- `etfs-increase-change-in-open-interest-MM-DD-YYYY.csv`
- `unusual-etf-options-activity-MM-DD-YYYY.csv`

**Optional Advanced Volatility & Fundamental Input Files (For Extreme Conviction Flags):**
- `earnings-in-the-next-trading-day-MM-DD-YYYY.csv`
- `implied-volatility-iv-rank-and-iv-percentile-high-MM-DD-YYYY.csv`
- `implied-volatility-iv-rank-and-iv-percentile-low-MM-DD-YYYY.csv`
- `stocks-high-implied-volatility-vs-realized-volatility-us-MM-DD-YYYY.csv`
- `stocks-low-implied-volatility-vs-realized-volatility-us-MM-DD-YYYY.csv`
- `etfs-high-implied-volatility-vs-realized-volatility-us-MM-DD-YYYY.csv`

*(Note: If it's the very first time you are scanning a new asset class, ETF, or stock, the algorithm will quietly "skip" generating signals for it on Day 1 while it builds the baseline snapshot. Signals will print perfectly on Day 2).*

---

## 3. How to Execute
Once the daily data is physically placed in the `inputs/` directory, open your terminal and run the batch orchestrator. The `MM-DD-YYYY` parameter is completely optional.

**Daily Run (Defaults to Today's Date):**
```cmd
C:\options-scanner> run_scan.bat
```

**Historical Run (Specify an Exact Date):**
```cmd
C:\options-scanner> run_scan.bat 08-12-2026
```

The system will crunch the arrays, print the visual block directly to your console (including a unified **TRADINGVIEW WATCHLIST** output at the very bottom for instant copy-pasting), and simultaneously save a clean `.txt` snapshot of the run into the `outputs/` folder.

---

## 4. How to Read & Interpret the Data
The output is dynamically split into **BULLISH**, **BEARISH**, and **SIDEWAYS** blocks. The rows are aggressively sorted from top-to-bottom by **NOTIONAL** capital, ensuring you look at the heaviest institutional bets first.

### Key Data Columns
*   **STOCK**: The underlying ticker.
*   **SIG**: The mathematical profile of the signal triggered. 
    *   **TMG (Short Covering)**: Massive block of Open Interest strictly *decreased*. Often implies large funds closing short positions, potentially triggering a squeeze or a floor. 
    *   **TMJ (Short Build-Up)**: Massive block of Open Interest strictly *increased*. Often implies new, heavy institutional positioning.
    *   **J+G (Combo/Confirmed)**: Both TMG and TMJ triggered simultaneously across different strikes. Highly potent combination.
*   **DTE (Days to Expiry)**: Exactly how many days until the contract expires. *(Note: 0-DTE contracts are auto-filtered out by default to reduce intra-day retail noise).*
*   **CONF (Price Confirmation)**: Compares the direction of the options flow to the movement of the underlying stock on that exact same day. (See section below for interpretation).
*   **NOTIONAL**: The actual dollar value committed to the trade (`Abs(OI_Chg) * Option_Price * 100`). This is your primary metric. Large notional equates to whale sizing.
*   **OI CHG**: The raw contract amount generated.
*   **PRICE Δ**: How much the option premium fluctuated over the day.

### Advanced Context Flags (Appended to Line End)
If you provide the optional advanced CSV inputs, the scanner will aggressively cross-reference them and permanently brand extreme conviction setups with the following tags:
*   **`[ER]` (Earnings Hedge):** Do not trust the organic momentum. The stock has earnings in the next 24 hours. This massive volume is largely binary gambling/hedging.
*   **`[IVR+]` (High IV Rank):** The implied volatility is incredibly expensive (historically maxed out). Extremely potent if the smart money is *Selling* (TMJ/Short Build-Up) because they are executing a textbook Volatility Crush against overpriced fear.
*   **`[OVRP]` (Overpriced Premium):** Implied Volatility is outstripping actual Realized Volatility. Extremely potent if the smart money is *Buying* (TMG/Short Covering) because it proves they are willingly overpaying for options in anticipation of a massive underlying technical earthquake.

---

## 5. Trading Strategies (The "Cheat Sheet")

### 1. Following the `CONF` (Confirmation)
Knowing *how/why* the stock moved changes entirely how you should approach the trade.

*   **TRUE (The Momentum Setup):** The smart-money placed a Bullish bet, AND the stock price went up. The money and the trend are moving synchronously. These are excellent setups for immediate momentum continuations and standard breakouts.
*   **FALS (The Accumulation Setup):** The smart-money placed a Bullish bet, BUT the stock price dumped heavily. Institutions are aggressively "buying the dip" while retail panics. These trades carry higher risk of catching a falling knife—it is generally best safely waiting 1-2 days for the price to visibly curve back upwards before following the money. 
*   **NEUT (The Coiled Spring):** Millions in notional options volume flooded the stock, but the stock price barely budged (within ±0.2%). Institutions are silently loading up inside a tight consolidation box. Put these on a strict watchlist to trade the explosive breakout of the trading range.

### 2. Navigating the `SIDEWAYS` Block
When a ticker has both bullish and bearish option flow simultaneously (meaning an institution is hedging or executing a Strangle framework), look at the **`net_signal:`** row at the bottom of its block.

If the internal math resolves to a heavily lopsided skew (e.g. `net_signal: -4,500`), you instantly know that their dominant bias is Bearish (the Ceiling), and the smaller positive flow is strictly a protective hedge (the Floor) against their core position.

### 3. NOTIONAL > Everything
Do not get easily tricked by massive raw OI changes (+45,000 contracts). If the options are cheap, the actual capital commitment is tiny. *Always* rely on the `NOTIONAL` ranking to tell you where the most serious, heavy-hitting institutional money is parked.
