# Breakout systems (Donchian/Turtle, Darvas, VCP/52-week high) and price-only low-volatility / low-vol + momentum blends for Indian equities

Scope: can these reach CAGR > 16% with max DD no worse than -30%, net of Indian costs (about 0.86% round trip + 0.1% slippage per side, 20% STCG), long-only, NIFTY 500 point-in-time, 2006-2026, daily OHLCV only. Current strategy S44984096: 15.3% CAGR / -23.5% max DD.

Overall caveat: the published Indian evidence is thin. The NSE whitepapers are back-tested index levels (in-sample, gross of costs, price-return), and the practitioner breakout tests are mostly gross or poorly specified. I found no peer-reviewed, cost-inclusive, survivorship-free Indian test of Donchian, Darvas or VCP breakouts on stocks.

## Q1. Evidence: CAGR, max DD, Sharpe, costs, in/out of sample, decay

### Takeaway
Low-vol and Alpha+Low-vol indices show 17-20% back-tested CAGR from 2005 to 2017-18, but they are gross, partly in-sample, and still fell 43-50% in 2008. That alone breaks a -30% cap unless an exit or regime overlay is added. The breakout evidence on Indian stocks is anecdotal. The best costed Indian momentum test shows -66% to -75% drawdowns with no exit rule.

### Cited Findings
**Low volatility (price-only, needs only daily closes)**
- NIFTY100 Low Volatility 30 method: the 30 least volatile NIFTY 100 stocks by 1-year standard deviation of returns, weighted by inverse volatility, rebalanced quarterly. — [NSE whitepaper Jun 2018](https://archives.nseindia.com/content/indices/NIFTY100_Low_Vol30_White_paper_Jun2018.pdf)
- Back-tested since April 2005 (to 31 May 2018, price return): 17.66% CAGR and 18.18% volatility, against 13.66% and 22.62% for NIFTY 100. Return/risk was 0.97 against 0.60. Over 10 years: 13.71% against 9.01%. Over 5 years: 14.77% against 12.88%. — [same](https://archives.nseindia.com/content/indices/NIFTY100_Low_Vol30_White_paper_Jun2018.pdf)
- Max drawdown was -49.5% (2 Jan 2008 to 27 Oct 2008), against -61.5% for NIFTY 100. Calendar 2008: -43.3% against -53.7%. 2011: -13.3% against -25.8%. Other drawdowns: 2006 -32.1% (index -31.0%), 2013 -15.6% (index -15.4%). — [same](https://archives.nseindia.com/content/indices/NIFTY100_Low_Vol30_White_paper_Jun2018.pdf)
- On rolling returns, low-vol beat NIFTY 100 in 100% of 5-, 7- and 10-year windows but in only 66% of 1-year windows. — [same](https://archives.nseindia.com/content/indices/NIFTY100_Low_Vol30_White_paper_Jun2018.pdf)
- Nifty500 Low Volatility 50 TRI (secondary source, Axis MF): -47.3% from 8 Jan 2008 to 27 Oct 2008. 15-year CAGR 15.1% against 13.0% for Nifty 500 TRI. I could not verify the figures (the page now returns 404). — [search summary of Axis MF article](https://www.axismf.com/mutual-fund-knowledge-centre/articles/low-volatility-index-vs-nifty-500-index)
- Nifty Low Volatility 50 selects the 50 least volatile NSE stocks by 1-year trailing prices. — [NSE factsheet](https://www.niftyindices.com/Factsheet/Factsheet_nifty_Low_Volatility50.pdf)
- Academic support for the anomaly: low-volatility stocks earn higher risk-adjusted returns in India, and this survives controls for size, value and momentum. — [Joshipura & Joshipura, Applied Finance Letters 2016](https://ojs.aut.ac.nz/applied-finance-letters/article/download/32/31). A betting-against-beta factor earns significant positive returns in India, and higher-volatility stocks earn lower returns. — [Agarwalla, Jacob, Varma, Vasudevan, IIMA WP 2014](https://www.iima.ac.in/publication/betting-against-beta-indian-market)

**Alpha + Low-vol (price-only: Jensen's alpha on 1 year of prices, plus 1-year std dev)**
- NIFTY Alpha Low-Volatility 30: 50% Alpha and 50% Low-Vol factor score, 30 stocks from NIFTY 100 plus NIFTY Midcap 50, base date April 2005. Alpha and Low-Vol need only 1 year of prices. Quality (ROE, D/E, PAT growth) and Value (ROCE, dividend yield, P/E, P/B) need annual-report data, so the Quality and Value variants cannot be built from OHLCV. — [NSE Multi-Factor whitepaper 2017](https://archives.nseindia.com/content/indices/NIFTY_Multi-Factor_Indices_whitepaper.pdf)
- Back-tested CAGR from April 2005 to 31 May 2017: Alpha Low-Vol 30 20.33%, Quality Low-Vol 30 17.61%, Alpha Quality Low-Vol 30 18.69%, against 13.47% for NIFTY 50. Ten years: 15.81% against 8.40%. Almost the whole period is a pre-launch backtest, so it is in-sample. — [same](https://archives.nseindia.com/content/indices/NIFTY_Multi-Factor_Indices_whitepaper.pdf)
- Calendar returns of Alpha Low-Vol 30: 2008 -50.27%, 2011 -13.50%, 2013 +14.74%, 2015 +13.42%, 2016 +8.02%. Single-factor portfolios in 2008: Alpha -66.96%, Low-Vol -44.60%, NIFTY 50 -51.79%. — [same](https://archives.nseindia.com/content/indices/NIFTY_Multi-Factor_Indices_whitepaper.pdf)
- Decay and out-of-sample: Alpha Low-Vol 30's 1-year return was about -11.95% as of mid-September 2025 ([Kotak](https://www.kotaksecurities.com/indices/indian-indices/nifty-alpha-low-volatility-30)). The Nippon index fund was -10.06% for 1 year as of August 2025 ([Dhan](https://dhan.co/mutual-funds/nippon-india-nifty-alpha-low-volatility-30-index-fund-direct-growth)). A third-party page puts 5-year CAGR at 11.14% and since-inception CAGR at 18.55% (unverified, undated) ([Angel One](https://www.angelone.in/indices/nifty-alpha-low-volatility-30)). Value Research ran a piece titled "Low volatility index funds fell more than market" (contents were blocked to me). — [Value Research](https://www.valueresearchonline.com/stories/230032/low-volatility-index-funds-fell-more-than-market/)
- Low-vol + momentum + payout ("Conservative Formula", India): the quarterly-rebalanced 100-stock portfolio beat S&P BSE 100 by 12.6% a year compounded. Payout yield needs dividend data, and I could not read cost or drawdown details (SSRN returned 403). — [Raju & Teli, SSRN 4163613](https://papers.ssrn.com/abstract=4163613)

**Momentum / 52-week high (context for breakouts)**
- Nifty 200 Momentum 30 constituents, annual rebalance, equal weight, Dec 2006 to Jun 2025, including delisted stocks, net of brokerage, slippage and STCG/LTCG: base momentum 14.60% CAGR / -70.61% DD. Low scaled-turnover half: 19.43% / -66.41%. High-turnover half: 8.51% / -75.09%. NIFTY 50: 10.41% / -55.12%. The author sells the backtest platform. — [freefincal, Mar 2026](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/)
- Naive monthly-rebalanced Indian momentum had drawdowns above 50% every 3-4 years. — [StockViz](https://stockviz.substack.com/p/momentum-without-the-crash)
- A 52-week-high industry-rotation test on Indian stocks, out of sample 2014-17: about 17% total over 3 years, Sharpe about 0.4, costs not discussed. Quantpedia called it "not very strong". — [Quantpedia/QuantInsti](https://quantpedia.com/an-analysis-of-52-weeks-high-effect-on-indian-stocks/)
- Nifty200 Momentum 30 TRI has returned about 19% since 2005, against about 15% for Nifty 200 TRI (secondary). Buying every 52-week high is not the same strategy. — [5paisa blog](https://www.5paisa.com/blog/what-if-you-bought-every-stock-hitting-a-52-week-high)

**Breakouts (Donchian/Turtle, VCP)**
- Donchian 20 and a 5x20 SMA cross on the NIFTY index (not stocks), gross of costs: median P&L was negative in every variant, long-only Donchian stayed in drawdown for about 5 years, and the author says to "dump" both as-is. — [TradingQnA, Trend Following in India Pt 1](https://tradingqna.com/t/trend-following-in-india-part-1-testing-donchian-s-classic-rules/188234)
- Turtle-style test on Indian stocks: about 10-15% annualised before costs, max DD about -25% to -35%, labelled illustrative. Weak evidence. — [Fyers blog](https://fyers.in/blog/backtesting-turtle-trading-on-indian-stocks/)
- Minervini Trend Template, US and Canada (not India). Nasdaq-100 since 2000: 12.3%/yr, DD 35%, against 82% for QQQ, flattered by 2000-02. TSX over 25 years: best variant lost 25% in 2008. A 10% stop cut CAGR from 8.6% to 7.1% and did not reduce DD (39% against 36%). A 200-DMA market filter cut DD from 39% to 34%. The VCP entry itself was not tested. — [MarketInOut](https://www.marketinout.com/blog/minervini-trend-template-backtest-markets); [TSX](https://www.marketinout.com/blog/minervini-trend-template-backtest-tsx)
- A VCP "study" on the prior 12 months' top 100 stocks (36 trades, 6% average risk, 69% average gain) has hindsight bias. — [FinancialWisdomTV](https://www.financialwisdomtv.com/post/can-one-chart-pattern-beat-the-market-i-tested-the-top-100-stocks)

### Inferences
- Unmanaged low-vol has about 4 points of edge over cap-weight but keeps about 80% of the market's crash depth (-45% to -50% in 2008). On its own it fails the -30% cap. It needs an exit (trend or absolute-momentum filter) or a blend with a trend-following sleeve.
- Alpha Low-Vol's 20% back-tested CAGR is in-sample and gross. Live results from 2017 to 2025 look much weaker (about 11% 5-year CAGR, a -10% to -12% 1-year drop in 2025). Expect decay of about 5 points or more.
- The breakout literature for India gives no basis to expect more than 16% CAGR at less than 30% DD. Any claim has to come from this repo's own test.

### Gaps
- No primary NSE figure for max DD or Sharpe of Alpha Low-Vol 30 over the full period. The 2020 whitepaper and the 2025-26 factsheets timed out.
- No cost-inclusive Indian Donchian, Darvas or VCP stock-portfolio study. Zerodha Varsity's costed 5x50 NIFTY test numbers were not retrieved.
- Turnover figures for the low-vol indices are not published in the sources read.

## Q2. Settings that trade CAGR against drawdown; robust vs fragile

### Takeaway
Adding Alpha/momentum to low-vol raises CAGR but also raises crash depth. Tight stops on breakouts reduce CAGR without reliably reducing DD. A market-level trend filter is the one overlay with consistent drawdown benefit in the sources.

### Cited Findings
- In 2008, Alpha alone fell -66.96%, Low-Vol -44.60% and Alpha+Low-Vol -50.27%. The blend gave up crash protection for more return (20.33% against about 17.7% CAGR). — [NSE Multi-Factor whitepaper](https://archives.nseindia.com/content/indices/NIFTY_Multi-Factor_Indices_whitepaper.pdf); [NSE LowVol30 whitepaper](https://archives.nseindia.com/content/indices/NIFTY100_Low_Vol30_White_paper_Jun2018.pdf)
- Breakout-type template: a 10% stop lowered CAGR and did not lower DD. A 200-day index filter cut max DD by about 5 points. — [MarketInOut TSX](https://www.marketinout.com/blog/minervini-trend-template-backtest-tsx)
- Momentum premium in India sits mostly in low-turnover (less liquid) names: 19.4% against 8.5% CAGR. A liquidity floor can erase the edge. — [freefincal](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/)
- Practitioner advice: check whether results shift sharply under ±15-20% parameter changes (reader comment, opinion). — [TradingQnA](https://tradingqna.com/t/trend-following-in-india-part-1-testing-donchian-s-classic-rules/188234)

### Inferences
- Robust levers: 1-year vol lookback (the index standard), inverse-vol weighting, quarterly rebalance with buffers, and a slow index trend filter. Fragile levers: short Donchian lengths (20-day) on stocks, tight percentage stops, and VCP contraction counts, which are hard to code objectively.
- Suggested grid for this repo: Donchian/52-week high entry (lookbacks 100/150/250), exit on a 50/100-day low or a 3-4x ATR chandelier stop (slow, consistent with the finding that slow exits held up), market filter on NIFTY 500 above its 200 DMA, and a liquidity floor. For low-vol: top 30-50 by 252-day vol within NIFTY 500 plus a 12-1 momentum rank, with absolute-momentum exit to cash.

### Gaps
- No Indian source maps vol-lookback or rebalance frequency to drawdown.

## Q3. Behaviour in 2008, 2013, 2017-19, March 2020, 2024-25

### Takeaway
Low-vol cushions the slow bears (2008 partly, 2011 strongly) and did well in 2013 and 2015-16. It probably lagged in the 2017 and 2023-24 small/mid-cap and PSU rallies, and Alpha Low-Vol fell 10-12% over the year to mid-2025. I could not confirm March 2020 figures.

### Cited Findings
- 2008: LowVol30 -43.3% against NIFTY 100 -53.7%. Alpha LowVol30 -50.27% against NIFTY 50 -51.79%. — [NSE](https://archives.nseindia.com/content/indices/NIFTY100_Low_Vol30_White_paper_Jun2018.pdf); [NSE MF](https://archives.nseindia.com/content/indices/NIFTY_Multi-Factor_Indices_whitepaper.pdf)
- 2013: LowVol30 +4.9% against +6.5%, with intra-year DD -15.6%. Alpha LowVol30 +14.74% against NIFTY 50 +6.76%. — same sources
- 2017: LowVol30 +28.2% against +31.0%. 2018 to May: +4.3% against +0.7%. — [NSE](https://archives.nseindia.com/content/indices/NIFTY100_Low_Vol30_White_paper_Jun2018.pdf)
- 2025: Alpha LowVol30 1-year return about -12% (Sep 2025). — [Kotak](https://www.kotaksecurities.com/indices/indian-indices/nifty-alpha-low-volatility-30)
- Trend template (US/Canada) reportedly took zero trades in 2008 (forum claim, unverified). — [TradingQnA VCP study](https://tradingqna.com/t/a-25-year-empirical-study-on-minervinis-volatility-contraction-pattern-vcp-what-2-35m-data-points-reveal-about-market-crashes/198732)

### Inferences
- In a V-shaped crash such as March 2020, a 1-year vol lookback reacts too late. Low-vol stocks fall about as hard, and breakout systems with slow exits will give back open profits. Both need testing in the repo.
- Breakout systems tend to sit in cash during 2008-type bears, because no new highs form. That is where their drawdown control comes from. They whipsaw in ranges such as 2010-13 and 2018-19, when mid/small caps were weak.

### Gaps
- No sourced March 2020 or 2024-25 drawdown for any of the low-vol indices. NSE factsheets timed out.

## Q4. Correlation with a monthly pullback-in-uptrend momentum swing strategy; diversification value of low-vol

### Takeaway
Breakouts and 52-week-high systems will be highly correlated with S44984096, since both are momentum/trend long books. Low-vol is the more plausible diversifier, but it shares the same crash beta in 2008-type events.

### Cited Findings
- NSE describes the Alpha factor as pro-cyclical (strong in 2007, 2009 and 2012, weak in 2008 and 2011) and low-vol as defensive (FMCG, pharma, IT). — [NSE MF whitepaper](https://archives.nseindia.com/content/indices/NIFTY_Multi-Factor_Indices_whitepaper.pdf)
- Low-vol sector mix (May 2018): Software 18.4%, Consumer Non Durables 17.7%, Auto 14.3%, Banks 13.8%, Power 9.9%. — [NSE](https://archives.nseindia.com/content/indices/NIFTY100_Low_Vol30_White_paper_Jun2018.pdf)
- 2015-16 shows the regime split. Alpha was +16.9% and +19.7% while Low-Vol was +11.7% and +1.8%, and their 2013 returns were similar. — [NSE MF](https://archives.nseindia.com/content/indices/NIFTY_Multi-Factor_Indices_whitepaper.pdf)

### Inferences
- Expect monthly-return correlation of about 0.8 or higher between a breakout book and S44984096. This is an estimate, to be measured in the repo. Low-vol is likely about 0.5-0.7 and diverges most in high-beta rallies and slow bears.
- A 50/50 blend of S44984096 and a trend-filtered low-vol sleeve is the most plausible route to more than 16% at less than 30% DD. It is untested.

### Gaps
- No published correlation between NSE low-vol and momentum indices was found.

## Q5. Indian traps: upper circuits, result gaps, liquidity

### Takeaway
Breakout fills are the main implementation risk. Upper-circuit and gap-up days make the signal day's close untradeable, and the momentum edge sits partly in illiquid names.

### Cited Findings
- The momentum edge is concentrated in low scaled-turnover stocks, which raises doubt that it can be captured at size. — [freefincal](https://freefincal.com/is-indian-momentum-investing-just-a-liquidity-illusion/)
- In flat markets, trend systems "wither away in transaction costs". — [Zerodha Varsity/StockViz series via search](https://zerodha.com/z-connect/varsity/could-trend-following-be-a-successful-trading-strategy-part-iii)

### Inferences
- Backtest rules for this repo: enter at the next open (not the breakout close). Skip any fill when the next open is at the upper circuit or high equals low at the circuit band. Add extra slippage on gap-ups of more than 3%. Avoid entries within about 5 days before results (flag via gap history if there is no results calendar). Apply ADV and price floors and exclude ASM/GSM names, which this repo cannot see from OHLCV, so treat them as a known residual risk. Low-vol has few of these issues: quarterly rebalance, large caps, low turnover.
- Costs: at about 1.06% round trip, a Turtle-style system with 20-day exits (many trades) loses several points of CAGR. Slow exits (100-day or 52-week-low type) limit the drag.

### Gaps
- No Indian quantification of the share of breakout signals blocked by upper circuits.
