# Market-regime filters for trend / momentum / breakout equity strategies (global and US evidence)

Method note: about 11 searches. Most findings come from abstracts, search snippets and secondary summaries, not full-text reads. Exact figures should be checked against the published papers before they are quoted in a final report. IS = in-sample, OOS = out-of-sample.

## 1. What do the academic studies show (Faber, Daniel-Moskowitz, Barroso-Santa-Clara, Moreira-Muir, Cooper-Gutierrez-Hameed)?

### Takeaway
There is solid long-sample evidence that momentum's risk depends on the regime. Momentum crashes cluster after bear markets, in high volatility and during sharp rebounds. Momentum's average returns are also weak after a down market. The cure with the strongest support is volatility scaling, which roughly doubles momentum's Sharpe ratio in the published samples. Simple trend filters on an index, such as the 10-month SMA, reduce drawdowns, but independent tests that include costs show little or no CAGR or Sharpe advantage out of sample. Generic volatility-managed portfolios (Moreira-Muir) largely fail real-time OOS tests.

### Cited Findings
- **Barroso & Santa-Clara (JFE 2015), "Momentum Has Its Moments", US 1927-2011.** Plain winners-minus-losers momentum earned about 14.5%/yr. Scaling it by its own trailing realised volatility raised the Sharpe ratio from 0.53 to 0.97 and "practically eliminat[ed] crash risk". In the 2000s plain momentum lost 28% of wealth, mainly in the 2009 crash, while the risk-managed version gained 88%. The authors say the method is implementable in real time and that the extra turnover does not offset the gains. Long/short factor portfolio; cost treatment is not detailed in the snippets. — [CFA Institute blog](https://blogs.cfainstitute.org/blog/2018/01/17/timing-the-market-momentum-and-beyond); [RePEc abstract](https://econpapers.repec.org/RePEc:eee:jfinec:v:116:y:2015:i:1:p:111-120)
- **Daniel & Moskowitz (JFE 2016), "Momentum Crashes".** Crashes happen in "panic" states: after market declines, with high volatility, when "a bear market suddenly ends and stocks dramatically rebound". In bear markets the momentum portfolio has an up-market beta of -1.51 against a down-market beta of -0.70 (t-stat of the difference 4.5). It behaves like a short call option, and the losers leg drives this. A dynamic momentum strategy that scales exposure by forecast mean and variance "approximately doubles the alpha and Sharpe ratio" of static momentum, consistently across markets, asset classes and periods. — [NBER w20439](https://www.nber.org/papers/w20439); [Chicago Booth Review](https://www.chicagobooth.edu/review/understanding-momentum-crashes); [AQR page](https://www.aqr.com/insights/research/journal-article/momentum-crashes)
- **Cooper, Gutierrez & Hameed (JF 2004), "Market States and Momentum".** They define the market state by the lagged 3-year market return. Momentum profits come from UP states. After negative 3-year market returns the momentum premium is roughly zero. — [Typeset copy](https://typeset.io/pdf/market-states-and-momentum-2o1ubo5j2l.pdf); [QUB working paper discussing it](https://www.qub.ac.uk/schools/queens-business-school/research/working-papers/papers/Filetoupload,669376,en.pdf)
- **International and contrary evidence on market states.** Momentum is larger in up markets and in less volatile periods internationally. In China the result is reversed: momentum returns follow DOWN markets. — [Waikato IREF paper](https://researchcommons.waikato.ac.nz/bitstream/10289/11238/5/IREF_accepted.pdf); [MPRA 78989](https://mpra.ub.uni-muenchen.de/78989/1/MPRA_paper_78989.pdf)
- **Avramov, Cheng & Hameed.** Momentum was unconditionally unprofitable in the US, Japan and the Eurozone over the last decade of their sample, but substantial after liquid market states. — [TAU seminar paper](https://en-coller.tau.ac.il/sites/nihul_en.tau.ac.il/files/media_server/Recanati/management/seminars/account/avramov.pdf)
- **Moreira & Muir (volatility-managed portfolios) versus Cederburg, O'Doherty, Wang & Yan (JFE 2020).** The volatility-managed alphas are confirmed IS in spanning regressions. Across 103 equity portfolios, though, the volatility-managed version beat the original in only 53 cases and lost in 50. "Reasonable out-of-sample versions generally earn lower certainty equivalent returns and Sharpe ratios" than the unmanaged portfolios. The authors blame unstable regression parameters. Barroso & Detzel are cited as finding the strategies do not survive transaction costs. — [Cederburg et al. PDF](https://www.lehigh.edu/~xuy219/research/COWY.pdf); [RePEc](https://econpapers.repec.org/RePEc:eee:jfinec:v:138:y:2020:i:1:p:95-117); [Alpha Architect summary](https://alphaarchitect.com/does-portfolio-timing-based-on-volatility-signals-outperform-buy-and-hold/)
- **Counterpoint: DeMiguel, Martín-Utrera & Uppal (JF 2024).** A conditional multifactor volatility-managed portfolio beats the unconditional one OOS and net of costs. It is a multifactor combination, not a single-factor defence. — [LBS PDF](https://lbsresearch.london.edu/id/eprint/3716/1/The%20Journal%20of%20Finance%20-%202024%20-%20DeMIGUEL%20-%20A%20Multifactor%20Perspective%20on%20Volatility%E2%80%90Managed%20Portfolios.pdf)
- **Faber, "A Quantitative Approach to Tactical Asset Allocation".** The 10-month SMA rule was tested IS on US stocks from 1900, then OOS on four other markets. A 10-years-later revisit appeared in JPM in 2018. It is widely summarised as cutting volatility and drawdowns "while maintaining competitive returns"; I could not retrieve the exact drawdown numbers. — [CXO Advisory](https://www.cxoadvisory.com/technical-trading/long-term-outperformance-from-trends-defined-by-moving-averages); [SSRN copy on Scribd](https://www.scribd.com/doc/116881446/SSRN-id962461)
- **Alpha Architect's robustness test of simple TAA (Faber-style).** It was "not robust" OOS over 1927-1977. Over 1978-2003, outperformance was driven mainly by long-duration bonds. — [Alpha Architect](https://alphaarchitect.com/2014/09/are-uber-simple-asset-allocation-systems-robust/)
- **Concretum Group update to 2025, 200-day SMA variant.** For the 1972-2005 IS period it reports Sharpe 0.81, CAGR 11.7% and max drawdown 9.5%. The drawdown is measured on monthly data, so the true figure was likely deeper. — [Concretum](https://concretumgroup.substack.com/p/global-tactical-asset-allocation)
- **Hurst, Ooi & Pedersen (AQR), "A Century of Evidence on Trend-Following".** The study covers 67 markets from 1880/1903. Time-series momentum did well in 8 of the 10 largest 60/40 drawdowns. Fees and costs were considered. AQR is not independent here. — [AQR](https://www.aqr.com/insights/research/journal-article/a-century-of-evidence-on-trend-following-investing?aqrPDF=1); [Alpha Architect](https://alphaarchitect.com/time-series-momentum-aka-trend-following-the-historical-evidence/)
- **Bianchi et al. (2022), "Taming momentum crashes".** Later work extending crash-mitigation methods. — [Strathclyde PDF](https://strathprints.strath.ac.uk/90217/1/Bianchi-etal-SSRN-2022-Taming-momentum-crashes.pdf)

### Inferences
- Relevance to a long-only breakout/momentum book: the crash mechanism comes mainly from the short losers leg (Daniel-Moskowitz). A long-only strategy suffers less from rebound crashes. It still suffers from bear-market drawdowns and from weak momentum after down states (Cooper et al.). The case for a regime filter on long-only is therefore "avoid weak expected returns in down states", not "avoid crashes".
- Volatility scaling, which is close to the repo's ATR-based sizing, has stronger factor-level evidence than binary on/off index filters. Generic volatility timing of the market itself does not hold up OOS (Cederburg).
- Most of these results are long/short, gross or lightly costed, and US. China's reversed result is a warning that state dependence may differ in emerging markets, India included.

### Gaps
- I could not get exact Faber CAGR or drawdown figures (original or 2018 revisit) from primary text.
- I have no verified Moreira-Muir headline numbers. Only the Cederburg critique was verified.
- I found no study that tests these filters on a long-only, single-stock breakout portfolio with full costs.

## 2. Do breadth filters (% above 200 DMA, advance-decline) have out-of-sample evidence?

### Takeaway
Mostly practitioner claims. I found no peer-reviewed OOS test of a "% of stocks above 200 DMA" regime filter. The available evidence is event studies with small samples (SentimenTrader, BofA, Schwab) and self-reported TradingView backtests. Several of these treat LOW breadth as a contrarian buy signal, which is the opposite of how a breadth "risk-off" filter is used.

### Cited Findings
- SentimenTrader: when fewer than 40% of stocks were above their 200-day average, the S&P rebounded consistently over the next 2-3 months. This is described as a pattern, not a formal backtest. — [SentimenTrader](https://www.sentimentrader.com/blog/recovering-from-under-the-200-day-average)
- BofA (Michael Wilson) backtest: forward 5-day, 1-month and 3-month returns after 92% or more of S&P 500 stocks were above their 200 DMA "tend to look favorable". — [SentimenTrader blog](https://sentimentrader.com/blog/why-strong-might-be-too-strong)
- Cyclical-sector breadth thrust: the S&P rallied in every cited instance, but the sample is small. SentimenTrader itself notes that extremes "often mark exhaustion... but not always". — [SentimenTrader](https://sentimentrader.com/blog/renewed-strength-in-cyclical-sector-participation)
- Schwab: 80% is "solid bullish breadth" but "isn't a perfect determinant". — [Schwab](https://www.schwab.com/learn/story/breadth-check-strength-and-weakness-trend-tracker)
- TrendInvestorPro tests of breadth timing models, practitioner work focused on "big swings". — [TrendInvestorPro](https://trendinvestorpro.com/?p=4849)
- TradingView breadth scripts with built-in backtests have no independent validation. — [TradingView Breadth Alpha](https://www.tradingview.com/script/vYcHWuTY/)

### Inferences
- A breadth filter should be treated as an untested hypothesis and validated on the repo's own data with walk-forward splits. The thresholds (40/50/60%) are free parameters with an obvious overfitting risk.
- Breadth at extremes looks contrarian over 1-3 month horizons. A filter that goes risk-off when breadth is low may sit out the strongest rebound months, which is the same failure mode as the 200 DMA filter.

### Gaps
- I found no academic OOS study of the advance-decline line or % above 200 DMA as a timing filter.
- Breadth series also carry survivorship issues, because index constituents change; none of the sources discuss this.

## 3. How do filters behave in sideways/whipsaw regimes? Lag, missed rebounds, post-publication decay?

### Takeaway
Badly. Moving-average filters generate many false signals in choppy markets and give back gains on V-shaped rebounds. Data-mining-aware OOS tests (Zakamulin) find no significant outperformance in the second half of a 155-year sample. Their value is concentrated in prolonged bear markets. Published anomalies decay by about 26% OOS and 58% after publication on average.

### Cited Findings
- **Zakamulin, 155-year dataset, rolling and expanding windows.** "No statistically significant evidence that market timing strategies outperformed the market in the second half of our sample." The rules do tend to beat the market in bear states despite many false signals. — [SSRN 2677212](https://papers.ssrn.com/abstract=2677212)
- **Zakamulin (J. Asset Management).** Reported MA-timing performance contains "a considerable data-mining bias and ignores important market frictions". OOS tests with realistic costs show it is overstated. — [Springer](https://link.springer.com/article/10.1057/jam.2014.25)
- **Zakamulin (IRF 2018).** Glabadanidis's strong MA results came from look-ahead bias. Corrected, MA timing is "only marginally better" than buy-and-hold. — [RePEc](https://econpapers.repec.org/RePEc:bla:irvfin:v:18:y:2018:i:2:p:317-327)
- **41 markets, 6,406 technical rules, data-snooping-robust test.** Results are "very sensitive to the introduction of moderate transaction costs". — [Springer s11408-023-00433-2](https://link.springer.com/content/pdf/10.1007/s11408-023-00433-2.pdf)
- **Arthur Hill (StockCharts), S&P 500 200-day SMA crossovers, 25 years.** 20 winning trades averaged +13.69% and 70 losing trades averaged -1.32%. That is a typical trend profile, with a 22% win rate and many small whipsaws. The S&P crossed its 200 DMA 165 times since 2000. It worked on the Nasdaq 100 but "did not fare well" on the Dow and the Russell 2000. Practitioner work, costs unclear. — [StockCharts 2019](https://stockcharts.com/articles/arthurhill/2019/02/just-how-effective-is-the-200-day-moving-average.html)
- **Hill (2022), ±3% band around the 200 SMA.** Signals fell from 27 to 4. The reported CAR comparison (4.3% vs 6.73%) is ambiguously labelled, so do not rely on the direction. — [StockCharts 2022](https://d.stockcharts.com/articles/chartwatchers/2022/02/reduce-whipsaws-and-improve-pe-590.html)
- **Advisor Perspectives.** When the 200 DMA itself was still rising, a break below it was "almost always a whipsaw". — [Advisor Perspectives](https://www.advisorperspectives.com/commentaries/2026/03/23/200-dma-broke-investor-should-know)
- **Missed rebounds.** Momentum crashes occur exactly at bear-market-end rebounds (Daniel-Moskowitz, above). A trend filter is still risk-off at those points, so it misses the rebound; for a long-only book that is lost upside rather than a crash. — [NBER w20439](https://www.nber.org/papers/w20439)
- **Trend following after crises.** Average returns in the extended post-crisis period were less than half of no-crisis returns. — [UCC working paper](https://www.ucc.ie/en/media/research/centreforinvestmentresearch/wp/TrendFollowingFeb2014.pdf)
- **McLean & Pontiff (JF 2016), 97 predictors.** Returns are 26% lower OOS, an upper bound on data mining, and 58% lower after publication. Decay is larger for predictors with higher IS returns. Jacobs & Müller found a reliable post-publication decline only in the US across 39 markets. — [McLean-Pontiff PDF](https://Www.Gwern.net/doc/economics/2016-mclean.pdf); [Jacobs-Müller](https://www.wiwi.hu-berlin.de/en/Professorships/bwl/finance/seminars/papers-fin-acc-res-seminars/17s/jacobs.pdf)
- **VIX term structure as a filter.** Fassas & Hourvouliades (2019) support it as a CONTRARIAN timing indicator. Simon & Campasano's backwardation strategy earned about half its profit in 2008 and little after mid-2010. Cboe notes backwardation occurred less than 20% of the time after 2010 and questions its predictive value. — [MDPI JRFM 2019](https://mdpi.com/1911-8074/12/3/113); [CXO Advisory](https://www.cxoadvisory.com/volatility-effects/timing-and-hedging-the-roll-return-for-vix-futures/); [Cboe](https://www.cboe.com/insights/posts/inside-volatility-trading-is-vix-backwardation-necessarily-a-sign-of-a-future-down-market)

### Inferences
- In sideways markets an index MA filter costs a steady drip of small losses plus re-entry lag. The payoff depends on one or two deep bears per decade appearing in the test window. A backtest that starts in 2016, with only the 2020 crash as a deep bear, gives the filter little room to prove itself. The 2020 V-shaped rebound is exactly the case where filters miss upside.
- High VIX and backwardation appear to be contrarian buy signals at the index level. That conflicts with using them as risk-off filters, except as a sizing or volatility-scaling input.
- Expect any filter selected IS to give back roughly a quarter or more of its edge OOS.

### Gaps
- I found no rigorous study that quantifies the total whipsaw cost of 200 DMA timing in flat regimes.
- I found no India-specific evidence in this scope.

## 4. Robustness: parameter sensitivity (150 vs 200 day etc.) and costs

### Takeaway
The academic robustness evidence (Zakamulin; the 41-market study) says results are sensitive to look-ahead handling, data-mining corrections and moderate costs. Practitioner tests show large dispersion across indices (it works on the Nasdaq 100, fails on the Dow and the Russell 2000) and with bands or smoothing. I found no clean published 150 vs 200 vs 250-day sensitivity grid in this pass.

### Cited Findings
- Studies without full costs or with unclear costs: the Hill/StockCharts tests, the SentimenTrader and BofA breadth studies, the TradingView scripts and the Fassas VIX work. — sources above
- Studies with costs: Zakamulin JAM (realistic costs; the edge mostly disappears) — [Springer](https://link.springer.com/article/10.1057/jam.2014.25). The 41-market study (sensitive to moderate costs) — [Springer](https://link.springer.com/content/pdf/10.1007/s11408-023-00433-2.pdf). Barroso-Santa-Clara (turnover does not offset the gains) — [CFA blog](https://blogs.cfainstitute.org/blog/2018/01/17/timing-the-market-momentum-and-beyond). DeMiguel et al. (net of costs) — [LBS](https://lbsresearch.london.edu/id/eprint/3716/1/The%20Journal%20of%20Finance%20-%202024%20-%20DeMIGUEL%20-%20A%20Multifactor%20Perspective%20on%20Volatility%E2%80%90Managed%20Portfolios.pdf). Barroso-Detzel (volatility management fails after costs), cited in [Cederburg et al.](https://www.lehigh.edu/~xuy219/research/COWY.pdf)
- Smoothing or band variants sharply change the number of signals: 27 to 4 with a 3% band, and 34 signals in 25 years with a 5-day-smoothed price. — [StockCharts](https://d.stockcharts.com/articles/chartwatchers/2022/02/reduce-whipsaws-and-improve-pe-590.html)

### Inferences
- If the repo tests a regime filter, run a grid (for example 100-250 day MA, with and without a 2-3% band, and a 3-year lagged return state à la Cooper et al.). Use full Indian costs and walk-forward splits. Accept the filter only if a broad plateau of parameters helps, especially on max drawdown and time under water, not just one value.
- Prefer continuous scaling, either volatility-based or a reduced size (for example half) in risk-off states, over a binary off switch. That matches the strongest evidence (Barroso-Santa-Clara, Daniel-Moskowitz) and softens whipsaw costs.

### Gaps
- I found no published parameter-sensitivity surface for 150 vs 200-day equity trend filters.
- I found no replication-database (Hou-Xue-Zhang) results specific to regime-conditioned momentum. I did not search this deeply.
