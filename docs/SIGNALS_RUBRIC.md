# Options Flow Scanner: Signals & Rubric

This scanner evaluates daily consolidated options flow to distill noise down to four primary directional signals based strictly on institutional or "smart money" behavior. 

## Universe Selection
Before any signal criteria are applied, the underlying stock must be vetted for **Liquidity**. The scanner parses the `Most Active Stock Options` report to ensure candidates have enough baseline options contract volume (default > 10,000 contracts). Illiquid names are automatically dropped to prevent false signals.

---

## Signal 4: Trend Conviction
*Detects whales opening massive new positions to aggressively ride an emerging trend or momentum surge.*

### Methodology
This logic scans the `Increase in Open Interest` report.
- **Bullish Output:** When a stock rallies significantly (default >= 3% daily move), and there is a massive surge in Open Interest heavily centered on Call strikes, it implies institutions are driving the trend higher by initiating new long positions.
- **Bearish Output:** When a stock plunges significantly (default <= -3%), and Put OI suddenly blasts upwards, it implies institutions are confidently riding the downtrend.

The scanner consolidates the total OI builds across the strike chain to display the primary strike where the highest conviction was placed.

---

## Signal 3: Institutional Risk Reversals
*Detects structured, financed plays where a fund completely exposes themselves to directional risk by buying one out-of-the-money leg and financing it by selling the opposite leg.*

### Methodology
This logic scans the `Options Flow` report by grouping trades on the identical Expiry date.
- **Bullish Risk Reversal:** A fund buys an Out-Of-The-Money Call at the Ask, AND simultaneously sells a Put at the Bid. 
- **Bearish Risk Reversal:** A fund buys an Out-Of-The-Money Put at the Ask, AND simultaneously sells a Call at the Bid.

---

## Signal 2: Naked Whale Sweeps
*Detects whales hitting the ask to initiate massive, unhedged, short-term directional bets.*

### Methodology
This logic scans the remaining `Options Flow` tape after Risk Reversals have been extracted.
- **Direction:** Must be explicitly labeled as 'BuyToOpen' or 'ToOpen'.
- **At Ask:** The trade must have executed at or above the Ask price (indicating extreme urgency).
- **Size:** The transaction premium must be highly significant (default >= $50,000 for a single trade).

It flags Call orders as Bullish, and Put orders as Bearish, while displaying the Vol/OI fraction.

---

## Signal 1: Panic Covering
*Detects situations where large market participants are forced to aggressively cover risky options positions in the face of a rapidly moving underlying stock.*

### Methodology
This logic scans the `Decrease in Open Interest` report.
- **Bullish Output:** When a stock rallies significantly (default >= 3% daily move), and there is a large, sudden drop in Open Interest heavily centered on Call strikes, it implies Call sellers (shorts) are being squeezed and forced to cover (buy back). 
- **Bearish Output:** When a stock plumps significantly (default <= -3%), and Put OI suddenly drops, it implies Put sellers are capitulating.
