"""One table of every saved run: python compare.py [--metric "Win %"]"""
import argparse
from pathlib import Path
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("--metrics", default="Win %,CAGR %,Max DD %,Trades taken")
a = p.parse_args()
rows = []
for s in sorted(Path("results").glob("*/*/*/summary.csv")):
    name = f"{s.parent.parent.parent.name}/{s.parent.parent.name}"
    t = pd.read_csv(s, index_col=0)
    for exit_, r in t.iterrows():
        rows.append({"Strategy": name, "Universe": s.parent.name, "Exit": exit_,
                     **{m: r[m] for m in a.metrics.split(",")}})
df = pd.DataFrame(rows)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
print(df.to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
df.to_csv("results/comparison.csv", index=False)
print("\nsaved -> results/comparison.csv")
