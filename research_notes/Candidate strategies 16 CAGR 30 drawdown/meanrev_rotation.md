# Short-term mean reversion in uptrends, and sector / relative-strength rotation (Indian equities)

Scope: (a) Connors RSI(2), 3-day pullbacks, 20/50-DMA pullbacks, IBS; (b) NSE sector index momentum, top sectors then top stocks, dual momentum. Target: net CAGR >16%, max DD no worse than -30%, long-only, NIFTY 500 point-in-time, 2006-2026. Baseline S44984096: 15.3% CAGR / -23.5% DD.

Overall: the published evidence is thin and mostly gross of costs. I found **no rigorous, cost-inclusive, point-in-time Indian backtest of RSI(2), IBS or DMA-pullback mean reversion**, and only weak academic Indian evidence on sector rotation. Treat everything below as something to test in this repo, not as proof.

## Evidence: performance, costs, in/out of sample, decay, Indian evidence

### Takeaway
US and futures RSI(2) results are self-published, mostly in-sample, and gross or cost-unclear. The one large Indian RSI study (PhonePe/Share.Market) used RSI 7/14/21, not RSI(2), with no costs and today's index constituents, so it has survivorship bias. On rotation, Indian academic work finds sector momentum explains part of stock momentum. Practitioner dual-momentum (NIFTY/Gold) backtests report lower drawdowns but are informal.

### Cited Findings
- Canonical RSI(2) rules: close above the 200-day SMA, RSI(2) below 10 (long), exit on a close above the 5-day SMA, no stop in the original Connors version. It was popularised by Connors and Alvarez in *Short Term Trading Strategies That Work* (2008) — [Algotr Substack](https://algotr.substack.com/p/this-simple-mean-reversion-strategy); [Backtest Substack](https://backtest.substack.com/p/the-2-period-rsi-a-simple-system)
- ES futures RSI(2) since 1997: profit factor 2.15 (base) to 2.99 (with a VIX filter), average trade about $512-572 per contract. The author claims "17+ years out of sample" but gives no split, costs, win rate or CAGR. **Author's own backtest, single instrument, costs undisclosed** — [Algotr Substack](https://algotr.substack.com/p/this-simple-mean-reversion-strategy)
- Connors Research says mean-reversion edges persisted after publication, citing an RSI 25 variant that called SPY's short-term direction correctly more than 91% of the time since 1993. **Vendor claim, in-sample** — [TradingMarkets / Connors Research](https://tradingmarkets.com/?p=1593757)
- An RSI(2) test on Nasdaq 100 CFDs from about 2016 to 2026 returned +26.9% in total against +528.3% for buy-and-hold. The strategy badly lagged a strong trend because of low exposure — [Backtrex](https://backtrex.com/en/backtests/connors-rsi-2-nasdaq-100)
- StockCharts warns that RSI(2) signals can come early: price can keep falling after RSI(2) drops below 5 — [StockCharts ChartSchool](https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2)
- India, 25-year RSI study on NIFTY 50, Next 50, Midcap 150, Smallcap 250 and NIFTY 500. It tested RSI 7/14/21 (**not RSI(2)**). Best result: the RSI-21 30/70 cross had a 79.05% win rate and 15.65% return per trade, at about 1 trade per stock per year. **No costs or slippage, current (static) constituents so survivorship bias, no CAGR or drawdown reported** — [PhonePe Invest / Share.Market](https://www.phonepeinvest.com/buzz/insights/the-rsi-myth-is-this-popular-indicator-worth-using-part-2-research-report)
- India cross-section: size, cash-flow-to-price, momentum and **short-term reversal** have strong predictive power for Indian stock returns (academic, monthly, gross) — [SSRN 3838938](https://dx.doi.org/10.2139/ssrn.3838938)
- Indian anomalies, 2000-2020: only 5 of 12 anomalies predict 1-month returns, and the coexistence of momentum and reversal is one of them — [core.ac.uk](https://core.ac.uk/works/142907511)
- ISB/NSE work: Indian stocks under-react at first (short-run momentum), while mid caps over-react in the long run — [ISB blog](https://blogs.isb.edu/blog/2012/04/17/momentum-and-overreaction-in-indian-capital-markets/)
- Sector momentum, India: Sehgal & Jain (2011) find momentum profits in sectoral returns, and find that part of stock momentum is captured by the sector factor — [Emerald, J. Advances in Mgmt Research](https://www.emerald.com/insight/content/doi/10.1108/09727981111129327/full/html)
- Sharma, Srivastava & Pinsky test ranking and clustering rotation across 15 NSE sectoral indices, rebalanced annually, half-yearly, quarterly and monthly, on 2012-2023 data. I could not extract the numeric results from the PDF — [AIRCC IJDKP v15n2](https://aircconline.com/ijdkp/V15N2/15225ijdkp05.pdf)
- Dual momentum NIFTY/Gold (200-day lookback), 2014-2024: 18.79% CAGR / -11.42% max DD, against NIFTY 50 at 12.13% / -34.00%. **Informal blog, costs unclear, short window** — [MomentumLab](https://momentumlab.substack.com/p/backtesting-dual-momentum-strategy)
- Dual momentum NIFTY/Gold from 1995: 14.0% CAGR against 12.4% buy-and-hold, with about a 21% drawdown against more than 50% in 2008 — [Samasthiti](https://samasthiti.substack.com/p/indian-edition-of-the-dual-momentum)
- NSE strategy (factor) indices: performance of most indices falls considerably after launch, i.e. out of sample (2022 study, as reported in search results; I could not fetch the full text) — [Applied Finance Letters](https://ojs.aut.ac.nz/applied-finance-letters/article/download/604/159)
- Indian momentum, Dec 2006 to Jun 2025, **net** of brokerage, slippage, 12.5% LTCG and 20% STCG, annual rebalance:

  | Portfolio | Net CAGR | Max DD |
  |---|---|---|
  | NIFTY 200 Momentum 30 | 14.60% | -70.61% |
  | NIFTY 50 | 10.41% | -55.12% |
  | Liquid half of the momentum stocks | 8.51% | -75.09% |
  | Illiquid half of the momentum stocks | 19.43% | -66.41% |

  The author reads the excess return as an illiquidity premium. Platform-vendor backtest — [Freefincal](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/)

### Inferences
- No source meets the bar of net of Indian costs, point-in-time NIFTY 500, 2006-2026. Any >16% / <30% claim has to come from our own backtest.
- Unfiltered cross-sectional momentum in India has had drawdowns of -65 to -75% (2008). Rotation can only meet a -30% drawdown limit with an absolute-momentum or market-regime cash filter, which is the dual-momentum element.

### Gaps
- No Indian RSI(2), IBS, 3-down-day or 20/50-DMA pullback backtest with costs and point-in-time constituents was found.
- Sharpe and win-rate figures for the sector-rotation paper could not be extracted (PDF text was not machine-readable here).
- No quantified decay study of RSI(2) after 2008 was found. Claims in both directions are anecdotal.

## Does mean reversion survive ~1% round-trip Indian costs?

### Takeaway
Probably not as a standalone, high-frequency NIFTY 500 stock strategy. Academic reversal profits are largely eaten by costs even in the US. They survive only in large caps, with lower turnover, or with a fundamental anchor. Indian round-trip cost here is about 1.06% (0.86% plus 0.1% slippage per side), several times US large-cap costs.

### Cited Findings
- Quantpedia: costs make the simple short-term reversal effect hard or impossible to exploit. The cost drag comes mainly from small caps, and a large-cap universe cuts it a lot — [Quantpedia](https://quantpedia.com/strategies/short-term-reversal-in-stocks)
- Groot, Huij & Zhou (100 largest US stocks, weekly, 1990-2009, net of Nomura cost estimates):

  | Measure | Reported |
  |---|---|
  | Net return | about 0.29% per week (about 16.25% a year) |
  | Sharpe | 1.09 |
  | Max DD | -52.9% (origin of this figure unclear) |
  | 500 stocks, five-day rebalance | +10.6 bp/week |
  | 1,500 stocks, five-day rebalance | -31.4 bp/week |

  This is long-short, not long-only — [Quantpedia summary of SSRN 1605049](https://quantpedia.com/strategies/short-term-reversal-in-stocks)
- Simple and industry-adjusted reversal fail after costs, while fundamentally anchored reversal is profitable after costs — [Quantpedia](https://quantpedia.com/strategies/combining-fundamental-fscore-and-equity-short-term-reversals)
- Costs still eroded more than two-thirds of the return of a composite short-term signal (Blitz et al.) — [Alpha Architect](https://alphaarchitect.com/alpha-from-short-term-signals/)
- Reversal is concentrated in low-turnover stocks, which are the most expensive to trade, while high-turnover stocks show short-term momentum instead — [CEPR DP15857](https://repec.cepr.org/repec/cpr/ceprdp/DP15857.pdf)

### Inferences
These are my arithmetic, not sourced.

- **Break-even edge:** each trade must make more than about 1.06% gross just to cover costs. Then 20% STCG applies, because every trade is held under 12 months.
- **Exposure maths:** with 5 slots and an average hold of 4-5 days, a fully active RSI(2) book makes roughly 150-250 round trips a year.
  - Cost drag is about 1.06% × (trades per year / slots) of capital per year. At 200 trades and 5 slots that is about 42% a year.
  - So the gross edge per trade needs to be around 1.5-2% just to net 16% pre-tax. Published US stock RSI(2) averages are typically below 1% per trade (no Indian source found; verify).
- **Lower-turnover variants:** pullbacks to the 50-DMA in strong uptrends, held to a multi-week exit, at about 20-40 trades a year, have a realistic chance. RSI(2) and IBS with 5-day exits on single stocks are unlikely to survive.
- **Index route:** applying the signals to NIFTY / Bank NIFTY futures or ETFs costs much less (no delivery STT on futures). But that leaves the NIFTY 500 stock universe.

### Gaps
- No measured Indian gross edge per trade for RSI(2) or IBS on NIFTY 500 stocks. Our own backtest must log the average gross % per trade and trades per year.

## Settings: CAGR vs drawdown, robust vs fragile

### Takeaway
Little sourced evidence for India. The levers that reliably change the trade-off are the trend filter, the regime/volatility filter, the exit rule and whether a stop is used. Exact RSI thresholds are the fragile part.

### Cited Findings
- Adding a VIX filter to ES RSI(2) roughly halved the largest drawdown ($19,362 to $10,100) and raised profit factor from 2.15 to 2.99 (in-sample, vendor) — [Algotr Substack](https://algotr.substack.com/p/this-simple-mean-reversion-strategy)
- Mean reversion typically has a high win rate with occasional large losers when a dip becomes a crash — [RSI 2 Strategy for Indian Markets](https://onetradejournal.com/strategies/rsi-2-strategy)
- In the Indian RSI study, the longer period (21) with extreme bands gave the highest win rate and the fewest trades (gross) — [PhonePe Invest](https://www.phonepeinvest.com/buzz/insights/the-rsi-myth-is-this-popular-indicator-worth-using-part-2-research-report)
- Sector rotation studies compare annual, semi-annual, quarterly and monthly rebalancing on NSE indices, so rebalance frequency is the key tuning variable there — [AIRCC](https://aircconline.com/ijdkp/V15N2/15225ijdkp05.pdf)

### Inferences
- **Robust choices to test:**
  - 200-DMA plus a NIFTY 50 regime filter (index above its 200-DMA, India VIX below some level).
  - Liquidity screen (top-turnover names, to avoid the illiquidity mirage the Freefincal study shows).
  - Grid over RSI(2) entry 5/10/15 and exits SMA5 / RSI>70 / N-day.
- **Fragile choices:**
  - Single-threshold optimisation.
  - No-stop rules, which create crash tail risk.
  - Monthly sector rotation, which roughly triples turnover against quarterly.

### Gaps
- No published Indian parameter-sensitivity grid.

## Behaviour in 2008, 2013, 2017-19, March 2020, 2024-25

### Takeaway
Almost no sourced India-specific episode analysis. The structural expectations:
- Mean reversion with a 200-DMA filter goes to cash in prolonged bears (2008, part of 2020) but takes losses on the first legs down.
- Sector rotation without an absolute filter suffers deep drawdowns (2008: -65 to -75% for momentum).

### Cited Findings
- NIFTY 200 Momentum-style portfolios had -66 to -75% max drawdowns over 2006-2025, with the liquid group taking more than 8 years to recover (the 2008 episode lies inside this window) — [Freefincal](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/)
- Dual momentum (NIFTY/Gold) held the drawdown to about 21%, against more than 50% for NIFTY in 2008 — [Samasthiti](https://samasthiti.substack.com/p/indian-edition-of-the-dual-momentum)

### Inferences
- **March 2020:** the crash came fast from above the 200-DMA. RSI(2) entries would have fired repeatedly on stocks still above their 200-DMA in late February and early March, producing a cluster of losers. A NIFTY regime or VIX filter is essential.
- **2017-19:** narrow mid/small-cap bear market with large caps OK. Liquid large-cap mean reversion and sector rotation into private banks/IT likely held up; small-cap-heavy versions likely did not.
- **2024-25:** SEBI F&O changes and the late-2024 to early-2025 mid/small-cap correction. Unverified, needs our backtest.

### Gaps
- No source quantifies RSI(2), IBS or sector rotation performance in these specific Indian windows.

## Correlation with a monthly trend/pullback swing strategy (diversification)

### Takeaway
No Indian source measures correlation between short-term mean reversion and a monthly trend/pullback system. In principle the holding periods (days against months) differ. But both are long-only and buy dips inside uptrends, so they share market beta and the same crash risk. The diversification benefit will be smaller than that between trend and reversal factors.

### Cited Findings
- In India, momentum and short-term reversal coexist as distinct 1-month return predictors, which suggests different return sources — [core.ac.uk](https://core.ac.uk/works/142907511); [SSRN 3838938](https://dx.doi.org/10.2139/ssrn.3838938)
- Part of stock momentum is a sector effect. A sector-rotation sleeve would therefore overlap with any momentum-like stock selection — [Sehgal & Jain 2011](https://www.emerald.com/insight/content/doi/10.1108/09727981111129327/full/html)

### Inferences
- S44984096 is itself a pullback-in-uptrend system (StochRSI). RSI(2) or DMA pullbacks on the same universe will probably pick overlapping names and be positively correlated.
- Sector rotation with an absolute-momentum cash switch is the more plausible diversifier or overlay, for example tilting S44984096 entries toward the top-RS sectors.
- To test: daily-return correlation and drawdown overlap of each sleeve against S44984096, and a combined 70/30 equity curve.

### Gaps
- No empirical correlation data found for Indian markets, so this must be measured in the repo.
