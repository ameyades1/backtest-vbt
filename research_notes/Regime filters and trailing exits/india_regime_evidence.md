# Indian-market evidence on regime filters for momentum/trend strategies (NSE)

Research budget: about 12 tool calls. Two key PDFs (the NSE momentum whitepapers) timed out, so the 2017-19 calendar-year figures could not be checked. Treat every number below as attributed to its source, not independently verified.

## Q1. Academic papers on Indian momentum (IIMA data library, crashes, risk- or volatility-managed momentum)

### Takeaway
Momentum is a large, well-documented premium in India: about 21-22% a year for the long-short factor in the IIMA four-factor data from 1993 to 2013. It has crash-prone, negatively skewed returns. Risk-managed (volatility-scaled) momentum improves Sharpe ratio and downside in Indian samples, but the evidence is in-sample academic work on BSE stocks, without realistic Indian costs.

### Cited Findings
- **Agarwalla, Jacob & Varma (IIMA WP 2013-09-05), "Four Factor Model in Indian Equities Market":**
  - Data: CMIE Prowess, October 1993 to December 2013, with a survivorship-bias correction and illiquid stocks excluded.
  - Result: the momentum factor (WML) averaged about 21.9% a year in the revised version (21.2% in the original).
  - Daily, monthly and yearly factor series are kept up to date in the IIMA data library.
  - Sources: [IIMA](https://www.iima.ac.in/publication/four-factor-model-indian-equities-market); [RePEc](https://ideas.repec.org/p/iim/iimawp/12130.html); [PDF](https://web.iima.ac.in/~iffm/legacy/four-factors-India-90s-onwards-IIM-WP-Version-original-Sep13.pdf)
- **Singh & Walia (2022), "Risk-Managed Momentum: An Evidence from Indian Stock Market", FIIB Business Review 11(3):347-358:**
  - Data: 450 BSE stocks.
  - Relative momentum gives large profits, but they are negatively skewed and include occasional severe losses.
  - The risk-managed version (it forecasts crash risk and scales exposure, in the style of Barroso and Santa-Clara) roughly doubles the adjusted Sharpe ratio and significantly improves downside risk.
  - The sample period is not given in the abstract. The tests are in-sample.
  - Source: [IDEAS](https://ideas.repec.org/a/sae/fbbsrw/v11y2022i3p347-358.html)
- **Absolute (time-series) momentum:** a companion Emerald study finds the same pattern. The effect is substantial but exposed to occasional severe losses, and a risk-managed time-series momentum approach is proposed. — [Emerald IJOEM](https://www.emerald.com/insight/content/doi/10.1108/IJOEM-09-2023-1518/full/html)
- **Maheshwari & Dhankar (2017), Vision 21(1):** studies how global crises affect momentum profitability in India, i.e. crash dependence on crisis regimes. — [RePEc](https://ideas.repec.org/a/sae/vision/v21y2017i1p1-12.html)
- **Subramanian & Kayal (MSE WP 242, 2023):** applies the Moreira-Muir volatility-managed-portfolio method to India, using a volatility index. I could not confirm whether momentum results are included. — [MSE](https://mse.ac.in/wp-content/uploads/2023/09/WORKING-PAPER-242.pdf)
- **StockViz (practitioner):**
  - Naive monthly-rebalanced Indian momentum portfolios suffered drawdowns of more than 50% every 3-4 years.
  - A crash-avoidance variant, "High-To-Price" (52-week-high based), can sit in cash for months.
  - Verdict: "the jury is still out on the strategy's ability to avoid crashes in Indian equities."
  - Source: [StockViz Substack](https://stockviz.substack.com/p/momentum-without-the-crash)

### Inferences
- Volatility scaling, i.e. cutting exposure when the strategy's own realised volatility is high, has the best academic support in India. It is closer to a "regime filter" than a pure index-trend rule.
- None of the Indian papers found test regime overlays out of sample, net of STT, impact and taxes.

### Gaps
- I found no Indian paper that explicitly replicates Daniel-Moskowitz "momentum crashes" (bear-market state plus rebound) with a market-state filter.
- I could not access full-text numbers (CAGR, max drawdown) for Singh & Walia.

## Q2. India VIX as a predictor or regime filter

### Takeaway
India VIX is strongly and asymmetrically linked to *contemporaneous* NIFTY returns. Its *predictive* value is weak or contrarian, and I found no rigorous Indian study of VIX as a regime filter for momentum.

### Cited Findings
- **Thenmozhi & Chandra, NSE Working Paper 9 (2013):**
  - NIFTY returns are negatively and asymmetrically related to changes in India VIX.
  - The paper tests whether VIX changes can guide switching between large-cap and mid-cap portfolios.
  - Source: [NSE WP9](https://nsearchives.nseindia.com/research/content/res_WorkingPaper9.pdf)
- **NSE research paper res_241:** India VIX has a positive, significant relationship with value-stock returns, and the authors treat it as a distinct risk factor. — [NSE](https://nsearchives.nseindia.com/content/research/res_241_completed.pdf)
- **F1000Research (monthly data, 2011 to May 2025):**
  - A composite of India VIX and NIFTY RSI is a significant *contrarian* predictor (β = -0.061, p < 0.05).
  - High-VIX, overbought regimes tend to be followed by reversals.
  - Source: [F1000Research](https://f1000research.com/articles/15-427/v1)
- **RBI commentary:** market participants note that India VIX above 20 does not necessarily mean negative near-term returns. — [RBI](https://rbi.org.in/Scripts/PublicationsView.aspx?id=21337)

### Inferences
- High VIX usually comes with or after falls, so a VIX-based exit tends to de-risk late and miss the rebound. That rebound is exactly when momentum crashes happen.
- VIX is more defensible as a position-sizing input (smaller size when VIX is high) than as an on/off switch.
- All the VIX studies above are in-sample regressions.

### Gaps
- I found no published test of India VIX gating a momentum or breakout portfolio.
- India VIX history starts around 2008 (official series), which limits sample size. Not verified here.

## Q3. NSE momentum indices in 2017-19, 2020 and 2024-25, and practitioner regime-overlay tests

### Takeaway
The momentum indices beat their parents over the long run, but drawdowns track or exceed the market's. The September 2024 to April 2025 fall was about -32%. Published Indian overlay tests are informal blog or Substack backtests, often paywalled or reporting results only in charts, and none are rigorous or out of sample.

### Cited Findings
**Long-run index record**
- NSE: Nifty200 Momentum 30 had an 18.6% CAGR against 12.7% for Nifty 200 since base date (provider whitepaper; this is marketing-grade backfill). — [NSE whitepaper 2026](https://www.niftyindices.com/docs/default-source/indices/nifty200-momentum-30/momentum-strategy-whitepaper_2026.pdf) (fetch timed out; figure via search snippet)
- The index outperformed Nifty 200 in 15 of the past 20 calendar years. — [Curious Investing Substack](https://curiousinvestinginsights.substack.com/p/momentum-or-mayhem-unpacking-the)

**Drawdowns by episode (Nifty200M30 vs Nifty 50)** — [Curious Investing Substack](https://curiousinvestinginsights.substack.com/p/momentum-or-mayhem-unpacking-the)

| Episode | Nifty200M30 | Nifty 50 |
|---|---|---|
| 2008 GFC | -67.9% | -64.6% |
| 2020 COVID | -34.2% | -39.6% |
| 2022-23 | -14.8% | -13.2% |

- The same post says the momentum index fell -27% in a recent six-month correction, against -12% for NIFTY 50 and -15% for NIFTY 200.

**2024-25 and later** — [Wright Research](https://www.wrightresearch.in/blog/momentum-strategies-underperforming-2025-data-insights/)
- Nifty200M30 peaked at 38,115 on 27 September 2024 and troughed at 25,997 on 7 April 2025, a fall of 31.8%.
- On 5 November 2026 it was still 21.6% below that peak, and its 1-year return was about -3.5%.
- Momentum has had no losing 3-year or 5-year rolling window so far.
- The stated mechanisms are trend reversals and rotations, high-beta midcap tilts, and macro shocks (March 2020, spring 2025).
- The December 2025 index-methodology switch moved about Rs 16,000 crore. — [Business Standard](https://www.business-standard.com/markets/news/nifty200-momentum30-a-flip-of-index-switch-jolts-16k-cr-across-the-grid-125121400388_1.html)

**Freefincal tactical overlay on Nifty Midcap150 Momentum 50 TRI**
- Rule: hold equity when the 6-month moving average is above the 12-month moving average, otherwise hold debt.
- It switched only about 2 times in 5 years and about 3 in 7 years.
- It did well on XIRR at a 50% equity allocation, but generally had *higher* max drawdown, volatility and time underwater than plain rebalancing.
- It struggled with sharp moves such as March 2020, and its edge shrank at 70% equity.
- Taxes and exit loads were excluded.
- Source: [Freefincal](https://freefincal.com/?p=93180)

**Other practitioner work**
- **Momo India (Substack, September 2024):** goes 100% to cash when the momentum portfolio's NAV is below its 200-DMA, checked only at monthly rebalances, January 2007 to March 2024. Results are paywalled. — [Momo India](https://momoindia.substack.com/p/backtest-reducing-momentum-drawdowns)
- **Capitalmind Adaptive Momentum PMS:** says it moves fully or partly to cash "when market conditions dictate". No rule or out-of-sample statistics are published on the page. — [Capitalmind](https://capitalmind.in/portfolio-management-service/momentum)
- **Capitalmind basics:** a 2007-2019 momentum backtest against random portfolios; I saw no filter. — [Capitalmind](https://www.capitalmind.in/insights/momentum-investing-basics-india)
- **ValuePickr forum:** a volatility-adjusted momentum backtest with a gold regime filter, 2018-2026 (forum-grade). — [ValuePickr](https://forum.valuepickr.com/t/backtesting-volatility-adjusted-momentum-with-a-gold-regime-filter-2018-2026/218153)

### Inferences
- 2024-25 is the clearest recent case where an index-trend or breadth filter would have mattered: a high-beta midcap-tilted momentum book fell more than twice as far as NIFTY 50.
- The Freefincal result is a warning. Slow MA-crossover filters on momentum indices cut participation more than they cut drawdown when the crash is fast (2020).

### Gaps
- I could not retrieve 2017, 2018 and 2019 calendar-year returns for Nifty200M30 or Midcap150 Momentum 50 (the NSE PDFs timed out).
- Narrative context, unsourced in these notes: 2018-19 was a broad midcap and smallcap bear market with narrow large-cap leadership. It needs to be checked against the NSE factsheets: [Factsheet](https://www.niftyindices.com/Factsheet/Factsheet_Nifty200_Momentum30.pdf).
- I found no published Indian study using breadth measures (% of NIFTY 500 above 200 DMA, advance-decline) as a momentum regime filter. This is a genuine gap, best filled by the repo's own tests.
- Smallcase and Quant MF regime-overlay claims were not found in a verifiable form.

## Q4. Indian costs and whipsaw-heavy filters

### Takeaway
Credible Indian momentum tests that include costs and taxes show large drops from gross returns, and liquidity dominates. Every round trip a filter forces incurs delivery STT on both sides, impact, and short-term capital gains tax (STCG), so frequent whipsaws are expensive.

### Cited Findings
- **Freefincal, December 2006 to June 2025, annual rebalance, net of brokerage, slippage, 12.5% LTCG and 20% STCG:**

  | Portfolio | Net CAGR | Max drawdown |
  |---|---|---|
  | Base Momentum 30 | 14.60% | -70.61% |
  | Low-turnover (liquidity-scaled) momentum | 19.43% | -66.41% |
  | High-turnover momentum | 8.51% | -75.09% (over 8 years to recover) |
  | Nifty 50 | 10.41% | -55.12% |

  - No STT or impact model is detailed.
  - Source: [Freefincal](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/)
- StockViz: stop-losses, hedges and tactical strategies are "expensive", through transaction costs or forgone gains. — [StockViz](https://stockviz.substack.com/p/momentum-without-the-crash)
- The Freefincal tactical test above excluded taxes and exit loads, so it overstates the overlay's benefit. — [Freefincal](https://freefincal.com/?p=93180)

### Inferences
- Delivery STT (0.1% each side) plus stamp duty, exchange and GST charges, plus impact of about 0.2-0.5% in midcaps, comes to a rough 0.5-1% round-trip cost before tax. This is my estimate, not sourced here.
- With 20% STCG (since July 2024), a filter that liquidates winners early turns long-term gains into taxed short-term gains. Overlays should be judged net of tax and with the number of flips counted.
- Scaling exposure gradually (volatility or breadth weighted), or checking only at monthly rebalances, generates fewer trades than a daily on/off switch.

### Gaps
- I found no Indian study that quantifies how much STT and impact erode a regime filter specifically.
