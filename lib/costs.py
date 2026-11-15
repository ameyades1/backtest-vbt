"""Approximate Indian equity delivery costs as a fraction of traded value.

Per side (2024-25 rates, verify with your broker):
  STT 0.1% both sides | exchange ~0.00297% | SEBI 0.0001% | GST 18% on (brokerage+exch+SEBI)
  stamp duty 0.015% buy only | brokerage 0 for delivery on discount brokers.
vectorbt applies `fees` on both sides, so we use the average per side.
"""
STT = 0.001
EXCHANGE = 0.0000297
SEBI = 0.000001
STAMP_BUY = 0.00015
BROKERAGE = 0.0
GST = 0.18


def delivery_fee_per_side() -> float:
    buy = STT + EXCHANGE + SEBI + BROKERAGE + STAMP_BUY + GST * (EXCHANGE + SEBI + BROKERAGE)
    sell = STT + EXCHANGE + SEBI + BROKERAGE + GST * (EXCHANGE + SEBI + BROKERAGE)
    return (buy + sell) / 2


FEES = delivery_fee_per_side()   # ~0.11% per side
SLIPPAGE = 0.001                 # 0.1% per side; raise for small caps
