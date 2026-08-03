# Options Flow Scanner: Signals & Rubric

This scanner evaluates daily consolidated options flow to distill noise down to two primary directional signals based strictly on institutional or "smart money" behavior. 

## Universe Selection
Before any signal criteria are applied, the underlying stock must be vetted for **Liquidity**. The scanner parses the `Most Active Stock Options` report to ensure candidates have enough baseline options contract volume (default > 10,000 contracts). Illiquid names are automatically dropped to prevent false signals.

---

## Signal 1: Panic Covering
*Detects situations where large market participants are forced to aggressively cover risky options positions in the face of a rapidly moving underlying stock.*

### Methodology
This logic scans the `Decrease in Open Interest` report.
- **Bullish Output:** When a stock rallies significantly (default >= 3% daily move), and there is a large, sudden drop in Open Interest heavily centered on Call strikes, it implies Call sellers (shorts) are being squeezed and forced to cover (buy back). 
- **Bearish Output:** When a stock plumps significantly (default <= -3%), and Put OI suddenly drops, it implies Put sellers are capitulating.

The scanner consolidates the total OI drops across the strike chain to display the primary strike where the covering was concentrated.

---

## Signal 2: Aggressive Buy-to-Open
*Detects whales hitting the ask to initiate massive, unhedged, short-term directional bets.*

### Methodology
This logic scans the `Options Flow` report. It filters thousands of daily trades down to strict criteria:
- **Direction:** Must be explicitly labeled as 'BuyToOpen' or 'ToOpen'.
- **At Ask:** The trade must have executed at or above the Ask price (indicating urgency).
- **Size:** The transaction premium must be highly significant (default >= $50,000 for a single trade).

It then flags Call orders as Bullish, and Put orders as Bearish, while displaying the Vol/OI fraction heavily weighting situations where volume surpasses daily Open Interest. 
