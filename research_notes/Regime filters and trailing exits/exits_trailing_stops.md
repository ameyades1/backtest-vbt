# Exit methods for momentum and breakout systems: chandelier, ATR trailing, MA/EMA, time, and fixed stops

Research date: 2026-11-25. Tool budget limited (about 15 calls), so several primary PDFs were read only through abstracts or secondary summaries. Each point notes this where it applies. Tags: [IS] = in-sample only / no holdout; [GROSS] = no transaction costs; [NET] = costs included.

## Academic evidence (Kaminski & Lo, Lo & Remorov, Han/Zhou/Zhu, Clare et al, Lempérière, Hurst/Ooi/Pedersen)

### Takeaway
The theory is settled: a stop can only add expected return if returns are serially correlated (momentum or regime switching). Under a random walk it always lowers expected return. The best-known large gain, Han/Zhou/Zhu's stop on cross-sectional momentum (Sharpe about doubled, worst month cut from -49.8% to about -17%), is gross of costs and partly comes from the short side. Lo & Remorov find that once costs are included, tight stops on single US stocks lose to buy-and-hold, and only wide stops come out roughly even on a risk-adjusted basis. The trend-following papers support slow trend exits in general but say almost nothing about which kind of trailing stop is best.

### Cited Findings
- Kaminski & Lo (J. Financial Markets 2014, vol. 18, pp. 234–254): under the random-walk hypothesis, a simple 0/1 stop-loss rule always lowers expected return. Under momentum or regime switching, stops can add value. The authors suggest that in equities, stops may capture conditional momentum after losses. The analysis covers expected return, not risk directly. — [MIT DSpace](https://dspace.mit.edu/handle/1721.1/114876); [RePEc](https://ideas.repec.org/a/eee/finmar/v18y2014icp234-254.html)
- Lo & Remorov (J. Financial Markets 2017, vol. 34): closed-form results for stops under serial correlation, regime switching and transaction costs. On a large sample of individual US stocks, **tight stop-loss strategies underperform buy-and-hold because of trading costs**. Outperformance is possible only for stocks with high enough serial correlation. Some rules reduce downside risk, "but not substantially." [NET] — [MIT DSpace](https://dspace.mit.edu/handle/1721.1/107017)
- Details of Lo & Remorov, from a CXO summary: US stocks 1964–2014. Daily stops of 0% to -6% and 10-day stops of 0% to -14%. Cost of 0.2% per trade (half-spread; excludes brokerage and impact). Tight daily stops cut returns significantly. Wide 10-day stops matched buy-and-hold risk-adjusted, raised skew and cut max drawdown, but raw return was still lower. **Executing one day late beat immediate execution**, by a lot for tight stops, because prices partly reverted. Quick re-entry helped tight stops. Stock autocorrelation was positive in the first half of the sample and significantly negative in the second half. Spreads widened in crashes, which hurt stops. — [CXO Advisory](https://www.cxoadvisory.com/equity-premium/stop-losses-on-stock-positions-in-depth)
- Han, Zhou & Zhu, "Taming momentum crashes: a simple stop-loss strategy" (US 1926–2013; 6-month formation, skip a month, hold 1 month; deciles). Equal-weight momentum: 0.99%/month, SD 6.01%, Sharpe 0.17, worst months -49.8%, -39.4%, -35.2%, -34.5%. With a 15% stop: 1.93%/month, SD 4.61%, Sharpe 0.40, 3-factor alpha 2.01%, worst months -17.4%, -14.8%, -13.8%, -13.1%. With a 10% stop: Sharpe 0.50, worst month -15.4%. With a 20% stop: Sharpe 0.32, worst month -16.79%. About 10% of longs and 11% of shorts are stopped each month. Turnover rises from 39% to 49% (winners) and from 45% to 59% (losers). **Most of the gain comes from the loser (short) side.** The authors report robustness across size, liquidity, subperiods, value weighting and 12-month formation. [GROSS] — [CXO Advisory](https://www.cxoadvisory.com/technical-trading/stop-losses-to-avoid-stock-momentum-crashes/)
- Caveats on Han/Zhou/Zhu: no trading costs; costs could be very high for illiquid stocks once stopped; shorting losers may be expensive or impossible; stop-limit fills may not have been available historically; the 2016 revision uses a limit order at 1.5x the threshold; possible data snooping in the thresholds; the result may depend on a few crashes. Alpha Architect calls the results hypothetical. — [CXO Advisory](https://www.cxoadvisory.com/technical-trading/stop-losses-to-avoid-stock-momentum-crashes/); [Alpha Architect](https://alphaarchitect.com/2016/08/taming-the-momentum-roller-coaster-fact-or-fiction/)
- Clare, Seaton, Smith & Thomas, "Breaking into the Blackbox" (2013, S&P 500): **popular stop-loss rules added no value, and monthly decision rules beat more frequent trading.** Only the abstract was available because the PDF was blocked, so the exact numbers are not verified. Their related "Trend is Our Friend" paper finds that trend following improves risk-adjusted returns over buy-and-hold and risk parity in multi-asset allocation. — [City Univ. repository](https://openaccess.city.ac.uk/17842/8/BLACKBOX%20%20%20SSRN-id2126476.pdf); [York DP 12-25](https://ideas.repec.org/p/yor/yorken/12-25.html)
- Lempérière et al., "Two centuries of trend following": trend t-stat of about 10 since 1800 and about 5 since 1960, net of drift. Full-sample t-stat 10.5 (9.8 after removing the long-only component), Sharpe 0.72. By sector, Sharpe is about 0.7 for indices, 0.47 for FX, 0.4 for bonds and 0.28 for commodities. **No sign that long trends have degraded, but shorter trends have significantly withered.** This matters for exits: fast exits act like short-trend signals. — [arXiv 1404.3274](https://arxiv.org/pdf/1404.3274)
- Hurst, Ooi & Pedersen, "A Century of Evidence on Trend-Following": 1880 onward, 67 markets. Net-of-fee Sharpe about 0.76–0.77, average single-market Sharpe about 0.4, low correlation to traditional assets. [NET of assumed 2/20 fees and costs] — [Alpha Architect](https://alphaarchitect.com/time-series-momentum-aka-trend-following-the-historical-evidence/); [AQR](https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing)

### Inferences
- Stops help only where trends persist. For a long-only momentum book in a single stock, the stop's job is to cut tail losses (drawdown, worst month), not to raise CAGR. Expect lower raw return and a better Calmar ratio at best.
- Han/Zhou/Zhu is the only large academic "stop doubles Sharpe" result. It is gross of costs, long-short, and driven by the short leg. A long-only Indian book will capture only part of it.
- The papers agree that tight stops are hurt by costs and short-term reversal, while wide or slower stops survive costs. Lempérière's finding that long trends hold up while short trends have faded points the same way: wide trailing exits.

### Gaps
- Full text of Clare et al's Blackbox paper (trailing-stop thresholds and figures) could not be read.
- No academic paper found that directly compares chandelier, ATR trailing, EMA and time exits on the same entry.

## Practitioner and systematic tests comparing exits (Turtles, LeBeau chandelier, Carver, Clenow, Alpha Architect, Quantpedia, others)

### Takeaway
Reproducible head-to-head exit comparisons are rare and mostly behind paywalls or shown as images. What is visible suggests three things. Longer time or slow trend exits beat tight give-back trailing stops on average per-trade return. Profit targets raise win rate but can cap the payoff. Combining a trailing stop with a profit target can be the worst of both.

### Cited Findings
- Chandelier exit (LeBeau, popularised by Elder): the stop sits a multiple of ATR below the highest high of the lookback. The usual default is 22 periods and 3x ATR; a larger multiple or longer length makes a wider, slower stop. In its raw form the stop can **fall** during an uptrend if ATR widens without a new high, so implementations ratchet it so it never moves down. — [NexusFi](https://nexusfi.com/a/indicators/chandelier-exit); [IncredibleCharts](https://www.incrediblecharts.com/indicators/chandelier_exits.php)
- Arthur Hill, StockCharts SystemTrader (Apr 1997–May 2017; historical index constituents, so survivorship is handled; 20 equal-weight positions; $10 commission; **no slippage**). Entry on a 5/50 EMA cross, base exit on a 50/200 EMA cross. A Chandelier (22, 4ATR) trailing stop brought CAR **below 7%**. An 8x ATR(22) profit target gave about 8.99% CAR with a much higher win rate, and drawdown about the same as the chandelier. **Trailing stop plus profit target gave the worst results.** The 8-ATR target on the S&P 1500 gave 9.27% CAR and 18.69% drawdown. Benchmarks: SPY buy-and-hold 7.52% CAR with 29% drawdown; golden cross 8.46% CAR with 17.22% drawdown. Several cells are in images and were not readable. [NET of commission, no slippage, IS] — [StockCharts](https://articles.stockcharts.com/article/articles-arthurhill-2017-05-systemtrader---trailing-stops-versus-profit-targets-for-a-moving-average-crossover-system)
- setup4alpha (Substack): 56 exit rules on Russell 1000 stocks over 26 years, 105,708 trades, after commission and slippage, with t-stats clustered. Entry when a stock closes back above its 200-day MA; the 200-day exit stays as a backstop under every rule. Average return per trade: give-back-of-profit trailing stop ranked worst, at -0.02% (mid setting) and -0.14% (tightest, t=-3.6, 47% win rate). Close-only channel exit +0.17% (5-day version -0.17%, t=-2.5). Lowest-low channel exit +0.24%, beating close-only by about 0.1% at every lookback. **Time exit +0.52%, and 12 months gave +1.03%.** The top four exits are behind a paywall. [NET, per-trade not portfolio, IS] — [setup4alpha](https://setup4alpha.substack.com/p/trailing-stop-vs-fixed-stop-tested)
- Turtle System 1: 20-day breakout entry, 10-day opposite-breakout exit, 2N (2x 20-day ATR) hard stop. System 2 uses 55-day entry and 20-day exit. **I found no clean, documented replication of the original exits with costs.** The blog tests found were simplified variants: monthly/weekly EURUSD lost -2.7% with -14.6% drawdown; an unverified 43-market futures test reported about $1.15M profit. — [Rogue Quant](https://roguequant.substack.com/p/i-backtested-the-legendary-turtle); [Backtrex](https://backtrex.com/en/backtests/turtle-trading-eur-usd)
- Carver (Systematic Trading), via secondary reviews: a trailing stop set in volatility units, around **4x daily price volatility**, corresponding to a holding period of about 6.5 weeks. Stops are set from market volatility, not account size, and kept separate from position sizing. This comes from secondary sources and is not checked against the book. — [the7circles review](https://the7circles.uk/?p=24323)

### Inferences
- Across the visible tests, exits that let trades breathe (time exits, lowest-low channels, slow EMA or wide ATR) beat tight give-back trailing stops. That matches Lempérière's point about short trends fading.
- A chandelier stop at 3–4 ATR is a reasonable default, but no test isolates it against an EMA exit on the same entry with net costs.

### Gaps
- No primary source found for Van Tharp, Clenow, Andreas (Clenow's book) or Quantpedia exit comparisons with numbers; these were not searched in depth because of the tool budget.
- Win rate and payoff ratios for each exit are mostly missing, because the tables were in images or paywalled.

## Sensitivity of ATR multiples and EMA length; overfitting; walk-forward

### Takeaway
The only walk-forward-style evidence found (Nifty 500, out-of-sample) shows a non-monotonic sweet spot: a 20% stop gave the best holdout Calmar. Tighter stops cut drawdown but gave up a lot of CAGR. In Han/Zhou/Zhu, Sharpe was ranked 10% > 15% > 20%, yet worst months were similar. These sensitivities are large, so choosing a parameter from a single in-sample best result is fragile.

### Cited Findings
- Nifty 500 momentum grid (themarketshack; roughly 2006–2026; 400 combinations; selected on about 15 years in-sample, tested on a 5-year holdout). Average holdout results by trailing stop level:

  | Stop | CAGR | Max DD | Calmar |
  |---|---|---|---|
  | None | 12.63% | -52.17% | 0.262 |
  | 15% | 8.36% | -35.32% | 0.366 |
  | 20% | 10.73% | -38.49% | 0.382 |
  | 25% | 12.03% | -42.10% | 0.346 |

  Four of the top five in-sample combinations used a 20% stop. Limitations: costs of only 0.03% per side; **STT, stamp duty, brokerage and slippage not modelled**; survivorship not modelled; the results come from a spreadsheet with no script, so they cannot be rerun. The search summary also says no combination beat the benchmark. Note: a -52% max DD in a holdout from about 2021 seems inconsistent with a 5-year window and may come from different definitions. Treat as unverified. — [themarketshack](https://themarketshack.com/projects/we-ran-400-momentum-tests-on-nifty-500-stocks-across-20-years-one-parameter-matters-more-than-everything-else)
- Han/Zhou/Zhu threshold sensitivity: Sharpe 0.50 / 0.40 / 0.32 for 10% / 15% / 20% stops [GROSS]. CXO warns that the choice of thresholds and multipliers is a data-snooping risk. — [CXO Advisory](https://www.cxoadvisory.com/technical-trading/stop-losses-to-avoid-stock-momentum-crashes/)
- setup4alpha: the tightest setting of each trailing family was its worst, for example the 5-day channel at -0.17% per trade. — [setup4alpha](https://setup4alpha.substack.com/p/trailing-stop-vs-fixed-stop-tested)
- Lo & Remorov: the sign of stock autocorrelation flipped between subperiods (positive early, negative later), so a stop tuned on one era can fail in the next. — [CXO Advisory](https://www.cxoadvisory.com/equity-premium/stop-losses-on-stock-positions-in-depth)

### Inferences
- Pick a stop width from a plateau (for example, CAGR and drawdown stay acceptable across 3–5 ATR or 15–25%) rather than the single best point. Expect tight settings to degrade out of sample.
- With costs this small, tighter stops look better than they would at a realistic Indian round-trip cost (STT, stamp duty, GST, impact).

### Gaps
- No published walk-forward test of chandelier ATR multiples or EMA exit lengths was found.

## Gap risk, slippage on stops, and India / emerging-market evidence

### Takeaway
Stop fills are worst exactly when stops matter: spreads widen in crashes, and stopped stocks are illiquid. Executing at the next day's price helped rather than hurt in US data. There is no peer-reviewed India study of momentum stops. The one Indian grid test points to wide (about 20%) stops as a drawdown-control tool that costs return.

### Cited Findings
- Spreads were often very large during crashes, which hurt stop-loss profitability. One-day delayed execution beat immediate execution because prices partly reverted. — [CXO on Lo & Remorov](https://www.cxoadvisory.com/equity-premium/stop-losses-on-stock-positions-in-depth)
- Han/Zhou/Zhu: costs are likely very high for illiquid stocks once stopped; stop-limit fills are uncertain; their execution uses a limit at 1.5x the threshold (for example, 22.5% for a 15% stop), which is a gap allowance. — [CXO Advisory](https://www.cxoadvisory.com/technical-trading/stop-losses-to-avoid-stock-momentum-crashes/)
- Hill's StockCharts test excluded slippage, which he notes matters most in less liquid stocks. — [StockCharts](https://articles.stockcharts.com/article/articles-arthurhill-2017-05-systemtrader---trailing-stops-versus-profit-targets-for-a-moving-average-crossover-system)
- India: NSE's 2012 research paper confirms momentum in CNX 100 stocks from 2003 to 2011 but does not test stops. — [NSE RP 2](https://nsearchives.nseindia.com/research/content/RP_2_Feb2012.pdf). A commercial source claims the Indian momentum premium largely disappears in the most liquid names (8.51% net CAGR over 19 years for the most liquid group). This is unverified and comes from a vendor. — [freefincal](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/)

### Inferences
- In NSE cash equities, close-based stops executed at the next open (the usual EOD backtest) already include overnight gap risk, as long as the backtest fills at the actual open and not at the stop level. Intraday stop-level fills in a backtest are optimistic, especially on result-day gaps and in stocks that hit circuit limits.
- Given the Lo & Remorov finding that delayed execution helps, a close-confirmed exit (exit on the close below the stop, filled at the next open) is defensible and less prone to whipsaw than an intraday stop.

### Gaps
- No peer-reviewed India or emerging-market study of stop or trailing exits for momentum or breakout was found.
- No quantified study found on NSE gap slippage at stops or circuit-limit fill failures.
