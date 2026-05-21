from __future__ import annotations

import argparse
from app.services.knia.knia_collector import KniaCollector

parser = argparse.ArgumentParser()
parser.add_argument("--chart-no", action="append", dest="chart_nos")
parser.add_argument("--max-charts", type=int, default=None)
args = parser.parse_args()

if __name__ == "__main__":
    print(KniaCollector().collect_fault_charts(chart_nos=args.chart_nos, max_charts=args.max_charts))
