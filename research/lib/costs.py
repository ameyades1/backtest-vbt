"""Indian equity cost model, as a fraction of traded value per side.

Statutory (equity cash, NSE; verified Nov 2026 from broker/aggregator sites — confirm vs NSE circulars):
  STT         delivery 0.1% buy & sell | intraday 0.025% sell only
  Exchange    0.00297% (NSE cash, flat since Oct 2024)
  SEBI fee    0.0001% (Rs 10/crore)
  Stamp duty  delivery 0.015% buy | intraday 0.003% buy
  GST         18% on brokerage + exchange + SEBI fee (not on STT/stamp)

Broker brokerage (per side, % of trade value):
  sharekhan   delivery 0.30% | intraday 0.02%  (min 1 paisa/share; standard plan,
              sharekhan.com/pricing — prepaid plans are cheaper)
  discount    delivery 0     | intraday 0.03% capped at Rs 20 (approximated as %)

Stock/index futures (used for shorts): STT 0.02% sell (today's rate, applied to all history: conservative),
stamp 0.002% buy, brokerage ~0.03% per side (approximate). Exchange fee taken as the cash rate.

Not modelled: DP charge on delivery sells (flat Rs per scrip per day), minimum-per-share
brokerage (only matters for sub-Rs-3 stocks), and the Rs 20 cap for discount brokers.
"""
STT = {"delivery": (0.001, 0.001), "intraday": (0.0, 0.00025), "futures": (0.0, 0.0002)}          # (buy, sell)
STAMP = {"delivery": (0.00015, 0.0), "intraday": (0.00003, 0.0), "futures": (0.00002, 0.0)}
EXCHANGE = 0.0000297
SEBI = 0.000001
GST = 0.18

BROKERS = {
    "sharekhan": {"delivery": 0.0030, "intraday": 0.0002, "futures": 0.0003},
    "discount":  {"delivery": 0.0,    "intraday": 0.0003, "futures": 0.0003},
}


def side_costs(broker: str = "sharekhan", product: str = "delivery") -> tuple[float, float]:
    """(buy, sell) total cost as a fraction of trade value."""
    b = BROKERS[broker][product]
    gst = GST * (b + EXCHANGE + SEBI)
    buy = b + STT[product][0] + STAMP[product][0] + EXCHANGE + SEBI + gst
    sell = b + STT[product][1] + STAMP[product][1] + EXCHANGE + SEBI + gst
    return buy, sell


def fee_per_side(broker: str = "sharekhan", product: str = "delivery") -> float:
    """vectorbt charges `fees` on both sides, so use the buy/sell average."""
    return sum(side_costs(broker, product)) / 2


BROKER = "sharekhan"
PRODUCT = "delivery"
FEES = fee_per_side(BROKER, PRODUCT)   # sharekhan delivery ~0.47% per side
SLIPPAGE = 0.001                       # 0.1% per side; raise for small caps

if __name__ == "__main__":
    for br in BROKERS:
        for pr in ("delivery", "intraday"):
            b, s = side_costs(br, pr)
            print(f"{br:10} {pr:9} buy {b:.4%}  sell {s:.4%}  avg/side {(b + s) / 2:.4%}  "
                  f"round trip {b + s:.3%}")
