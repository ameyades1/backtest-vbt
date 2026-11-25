# Momentum-family variants for Indian equities (vol-scaled, residual, 52-week high, smooth/FIP, wider/low-turnover)

## Evidence: CAGR, max DD, Sharpe, costs, in- vs out-of-sample, decay

### Takeaway
Published Indian evidence shows momentum earns a premium, but it falls well short of the 16% / -30% target. Every long-only index-style momentum portfolio for which I found drawdown figures fell 65-75% from peak to trough in 2008. The variants that improve risk (volatility scaling, residual, 52-week high) are documented mainly as long-short factor Sharpe gains, usually gross of costs. None of them reports a long-only Indian max drawdown near -30%.

### Cited Findings
- **NSE whitepaper 2026 (backtest, then live from Aug 2020):** Nifty200 Momentum 30 returned 19.19% CAGR from Apr 2005 to 27 Feb 2026, against 15.08% for the comparison index. The snippet was truncated, so the benchmark name is unclear (probably Nifty 200 TRI). This is gross of costs, and roughly 15 of the ~21 years are backtest. — [NSE Indices whitepaper 2026](https://www.niftyindices.com/docs/default-source/indices/nifty200-momentum-30/momentum-strategy-whitepaper_2026.pdf) (the full PDF timed out; figures come from the search snippet)
- **NSE 2020 whitepaper:** 18.6% CAGR versus 12.7% for Nifty 200, with volatility of 23.4% versus 22.3%. This is entirely backtest at launch. — [NSE whitepaper Sep 2020](https://www.niftyindices.com/docs/default-source/indices/nifty200-momentum-30/nifty200_momentum_30_index_whitepaper_sep_20.pdf)
- **Index construction:** 30 stocks chosen on a normalised momentum score: 6- and 12-month returns, each divided by volatility, so the score is already risk-adjusted. Weights are capped at the lower of 5% or free-float weight x score. Rebalancing is semi-annual, in June and December. The index launched on 25 Aug 2020. — [Curious Investing Insights](https://curiousinvestinginsights.substack.com/p/momentum-or-mayhem-unpacking-the); [freefincal](https://freefincal.com/nifty200-momentum-30-index-a-new-strategy-index-from-the-nse/)
- **Drawdowns from all-time high:** 2008 GFC -67.9% (Nifty 50 -64.6%); 2020 COVID -34.2% (Nifty 50 -39.6%); 2022-23 -14.8%; 2024-25 slump about -27% against about -12% for Nifty 50. The index beat Nifty 50 in 14 of 20 calendar years. — [Curious Investing Insights](https://curiousinvestinginsights.substack.com/p/momentum-or-mayhem-unpacking-the)
- **2024-25 live drawdown:** The Kotak Nifty200 Momentum 30 index fund fell -30.13% from 27 Sep 2024 to 14 Mar 2025 and was still below that peak on 20 Aug 2026. Its worst 1-year rolling return, ending 26 Sep 2025, was about -20.7%; Motilal Oswal's fund was about -21.0%. These are fund figures, net of TER and tracking costs. — [arthgyaan Kotak](https://arthgyaan.com/fund/kotak-nifty-200-momentum-30-index-fund-direct-growth/151781); [arthgyaan Motilal](https://arthgyaan.com/fund/motilal-oswal-nifty-200-momentum-30-index-fund-direct/149800)
- **Net-of-cost practitioner backtest (Dec 2006 to Jun 2025, annual rebalance, equal weight, brokerage, slippage, 20% STCG / 12.5% LTCG):**

  | Portfolio | Net CAGR | Max DD |
  |---|---|---|
  | Nifty 200 Momentum 30 replica, 30 stocks | 14.60% | -70.61% |
  | Low scaled-turnover 15 | 19.43% | -66.41% |
  | High scaled-turnover 15 | 8.51% | -75.09% |
  | Nifty 50 | 10.41% | -55.12% |

  For the low-turnover 15, 97% of 3-year rolling windows were positive and the worst 3-year CAGR was -8.9%. The high-turnover half took more than 8 years to recover. The platform says it includes delisted stocks, but the article does not confirm this study used them. — [freefincal, "Is Indian momentum investing just a liquidity illusion?"](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/)
- **Risk-managed momentum, India (Singh, Walia, Panda, Gupta, FIIB Business Review 2022; 450 BSE stocks):** Momentum profits are negatively skewed and prone to severe losses. A simple risk-managed approach about doubles the adjusted Sharpe and significantly improves downside risk. Only the abstract was available; the period and cost treatment are not given, and it appears to be in-sample long-short. — [IDEAS/RePEc](https://ideas.repec.org/a/sae/fbbsrw/v11y2022i3p347-358.html)
- **Risk-managed time-series momentum, India (JEFAS 2022; BSE 1996-2020):** Reports a substantial absolute momentum effect with occasional severe losses. The risk-managed version gives about 2.5 times the return of plain time-series momentum. Abstract only. — [IDEAS/RePEc JEFAS](https://ideas.repec.org/a/eme/jefasp/jefas-08-2021-0159.html)
- **Volatility-managed factors with India VIX (MSE Working Paper 242, 2023):** Volatility-managed momentum extends the mean-variance frontier even after controlling for other factors. — [MSE WP 242](https://mse.ac.in/wp-content/uploads/2023/09/WORKING-PAPER-242.pdf)
- **Global evidence on volatility scaling (Barroso and Santa-Clara 2015, JFE):** Scaling by the strategy's realised volatility "virtually eliminates crashes and nearly doubles the Sharpe ratio". This is long-short, US, gross of costs. Others (Bongaerts et al. 2020; Cederburg et al. 2020) dispute that volatility management helps out-of-sample. — [EconPapers JFE 116(1)](https://econpapers.repec.org/RePEc:eee:jfinec:v:116:y:2015:i:1:p:111-120); [MSE WP 242 citing the critiques](https://mse.ac.in/wp-content/uploads/2023/09/WORKING-PAPER-242.pdf)
- **Residual momentum (Blitz, Huij and Martens 2011):** Its Sharpe is about double that of total-return momentum, mainly because it carries lower time-varying factor exposure. Ehsani and Linnainmaa report a US Sharpe of 0.59 for residual momentum and 1.23 for a beta-neutral version. — [UCP repository thesis summarising](https://repositorio.ucp.pt/bitstreams/185837aa-e37e-433f-ac1a-0d5d79027b8f/download); [Bianchi et al., Taming momentum crashes](https://strathprints.strath.ac.uk/90217/1/Bianchi-etal-SSRN-2022-Taming-momentum-crashes.pdf)
- **India and idiosyncratic risk:** Indian momentum is positively related to idiosyncratic volatility, both in 1995-2006 (Ansari and Khan 2012) and among 473 BSE 500 firms in 2008-2018 (IIMB Management Review). Maheshwari and Dhankar (2017) find profits come mostly from winners and are not explained by size, value or illiquidity. — [Emerald, Ansari and Khan](https://emerald.com/insight/content/doi/10.1108/03074351211193730/full/html); [IIMB MR](https://www.iimb.ac.in/imr/previous-issues/momentum-march-2022.php)
- **52-week high, India (Raju, SSRN 4587697; more than 4,400 stocks, Oct 2004 to Aug 2023):** The effect is distinct and robust, with "more stable alpha" than academic momentum. The same excerpt also has a line saying momentum profits are marginally higher than 52-week-high profits, which is unresolved. — [Scribd copy of SSRN 4587697](https://www.scribd.com/document/694152012/SSRN-id4587697); [5paisa summary](https://www.5paisa.com/blog/what-if-you-bought-every-stock-hitting-a-52-week-high)

### Inferences
- Plain long-only momentum in India, whether 10, 15 or 30 stocks, has a structural 2008 drawdown of -65% to -75%. Our own -60% to -69% point-in-time result matches the literature, so it is not a bug. Widening to 30 stocks did not cut the 2008 drawdown; it cut CAGR (14.6% net).
- The headline 19% NSE figure is gross of costs and mostly backtest. A net replica comes out at about 14.6%. Assume post-cost decay of 2-5 percentage points a year at semi-annual or annual rebalancing, and more at monthly.
- To get from -65% to -30%, the stock-selection variant (residual, 52-week high, FIP, volatility-adjusted score) is not enough. Exposure has to go down in bear regimes, through a market trend filter, volatility targeting with cash, or a stop/trail. The CAGR cost of doing so is the open question. A test such as "12-1 or 52-week-high ranking + NIFTY 500 above its 200 DMA gate + portfolio volatility target of about 15-18%" is the only path I can see that plausibly reaches 16% / -30%. It has not been demonstrated in any Indian source I found.

### Gaps
- I could not read the full 2026 NSE whitepaper (timeouts). It should hold the official max drawdown, Sharpe and calendar returns for Nifty200 Mom30, Midcap150 Momentum 50, Nifty500 Momentum 50 and the alpha/low-vol momentum combinations. Fetch it manually.
- I found no Indian study of frog-in-the-pan (Da, Gurun and Warachka 2014) information discreteness. Its global evidence is from memory, not verified here.
- I found no long-only Indian residual-momentum backtest with drawdowns. The Erasmus thesis by Giakoumakis has an EM/India section I could not read. — [thesis](https://thesis.eur.nl/pub/66795/Emmanouil_Giakoumakis_641404_FinalThesis_FE_Masters.pdf)
- I could not retrieve the IIMA data library's momentum factor (WML) drawdowns.

## Which settings trade CAGR against drawdown; robust or fragile

### Takeaway
Liquidity screens and lower turnover look robust: they raise net CAGR without a meaningful drawdown reduction. Holdings count and rebalance frequency mainly move costs and CAGR, not the crash drawdown. Volatility targeting and regime gating are the only levers with documented crash reduction, and the evidence for those is mostly gross long-short work.

### Cited Findings
- Within the same 30 momentum names, the low-scaled-turnover half beat the high half by about 11 percentage points a year net, with drawdowns of -66% versus -75%. This suggests crowded, high-turnover momentum names are where the decay sits. — [freefincal](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/)
- NSE's own score divides returns by volatility, and the index rebalances only twice a year, but it still fell -67.9% in 2008. — [Curious Investing Insights](https://curiousinvestinginsights.substack.com/p/momentum-or-mayhem-unpacking-the)
- About two-thirds of momentum index changes take effect within one day; a flip of index constituents moved about Rs 16k crore. Rebalance days are crowded and front-run. — [Value Research](https://www.valueresearchonline.com/stories/225617/two-thirds-momentum-index-changes-just-one-day/); [Business Standard Dec 2025](https://www.business-standard.com/markets/news/nifty200-momentum30-a-flip-of-index-switch-jolts-16k-cr-across-the-grid-125121400388_1.html)
- Volatility scaling roughly doubles Sharpe in global and Indian long-short studies (see section 1), but the out-of-sample critiques apply. — [EconPapers](https://econpapers.repec.org/RePEc:eee:jfinec:v:116:y:2015:i:1:p:111-120)

### Inferences
- **Robust:** a buffer rule (for example, hold until rank falls below 2x N), a liquidity floor, and rebalancing less often than monthly. These are cost controls.
- **Fragile:** the exact lookback (6 vs 12 vs 12-1), the exact N, and rebalance-date luck. Test multiple rebalance-day offsets.
- **Volatility target:** scale gross exposure to a target of about 15% annualised using 3-6 month realised volatility, with no leverage. In 2008 this works by moving to cash as volatility spikes. It will lag V-shaped recoveries such as Apr-Jun 2020.
- Run 20-30 stock portfolios for capacity and smoother results, not for drawdown protection.

### Gaps
- No Indian net-of-cost grid over lookback, N and rebalance frequency was found.

## Behaviour in 2008, 2013, the 2017-19 midcap bear, March 2020 and Sep 2024 to Apr 2025

### Takeaway
Momentum gives no protection in a systemic crash (2008 slightly worse than Nifty). It held up roughly in line with the market in March 2020, and it badly underperformed in the Sep 2024 to Mar 2025 momentum unwind (about -27% to -30% against about -12% to -15% for the indices).

### Cited Findings
- **2008:** -67.9% versus -64.6% for Nifty 50. — [Curious Investing Insights](https://curiousinvestinginsights.substack.com/p/momentum-or-mayhem-unpacking-the)
- **2020:** -34.2% versus -39.6%. — same source
- **2024-25:** about -27% versus Nifty 50 at about -12% and Nifty 200 at about -15%. The tracking fund fell -30.13% from 27 Sep 2024 to 14 Mar 2025 and had not recovered by Aug 2026. — same source; [arthgyaan](https://arthgyaan.com/fund/kotak-nifty-200-momentum-30-index-fund-direct-growth/151781)

### Inferences
- A trend gate (for example, NIFTY 500 below its 200 DMA, or our weekly Supertrend logic) would have cut most of 2008, which was a slow bear. It would have helped little in March 2020, which was too fast. In 2024-25 the index-level trend stayed ambiguous for weeks while momentum names collapsed. That episode needs a stock-level trailing stop, not only a market filter.

### Gaps
- I found no sourced figures for momentum in 2013 or in the 2018-19 midcap bear. Pull them from the NSE whitepaper or the Midcap150 Momentum 50 factsheet.

## Likely correlation with S44984096

### Takeaway
I found no external data on this. By construction, the overlap is likely to be high.

### Cited Findings
- I found no sourced material. S44984096 is internal to this repository.

### Inferences
- S44984096 buys pullbacks in uptrending stocks. Momentum buys the strongest uptrends. Both are long trend-followers in the same NIFTY 500 universe, so I expect a monthly return correlation of roughly 0.6-0.8 and common pain in 2024-25. Diversification benefit will be limited. Compute the correlation directly from the backtest equity curves; it is cheap with our data.
- 52-week-high ranking overlaps most with breakout-style trend following. Residual momentum is the most likely of these variants to be different, because it strips out market beta.

### Gaps
- No measured correlation yet; it needs an internal backtest.

## Indian traps: circuits, small-cap liquidity, survivorship, turnover and tax drag

### Takeaway
The liquidity and turnover drag is large and well documented (the high-turnover half lost about 11 percentage points a year in net CAGR). Circuits, ASM/GSM and survivorship matter most for small-cap momentum.

### Cited Findings
- The high-scaled-turnover momentum half returned 8.5% net against 19.4% for the low half. — [freefincal](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/)
- Index rebalance crowding (Rs 16k crore moving on a constituent flip). — [Business Standard](https://www.business-standard.com/markets/news/nifty200-momentum30-a-flip-of-index-switch-jolts-16k-cr-across-the-grid-125121400388_1.html)
- The tax model at 20% STCG / 12.5% LTCG is used in the freefincal study. — [freefincal](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/)

### Inferences
- With monthly rebalancing and annual turnover of 200-400%, costs of 0.86% round trip plus 0.2% slippage come to roughly 2-4% a year before tax. Most gains also fall under STCG at 20%. Annual or semi-annual rebalancing with a buffer keeps more holdings past 12 months for 12.5% LTCG.
- Upper-circuit momentum names cannot be bought at the modelled price, and lower-circuit names cannot be exited. Model a fill only when the bar is not locked at its circuit band. Exclude ASM/GSM stocks and anything below about Rs 5-10 crore median daily value traded.
- Survivorship: use point-in-time NIFTY 500 membership and include delisted names. NSE momentum backtests rebuild history using index rules, so they may understate drawdowns before 2020.

### Gaps
- I found no Indian quantification of circuit-lock fill bias in momentum backtests.
