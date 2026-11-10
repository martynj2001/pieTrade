import argparse
import sqlite3

from api import db
from api.agent_analysis import build_report


def _table(headers: list[str], rows: list[list[object]]) -> None:
    values = [["-" if value is None else str(value) for value in row] for row in rows]
    widths = [max([len(header), *(len(row[index]) for row in values)]) for index, header in enumerate(headers)]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in values:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def _comparison_rows(comparison: dict) -> list[list[object]]:
    return [
        ["Agent", comparison["agent_eff"], comparison["agent_range_atr"]],
        ["Fixed", comparison["fixed_eff"], comparison["fixed_range_atr"]],
        ["Baseline", comparison["base_eff"], comparison["base_range_atr"]],
        ["Any pair", comparison["any_eff"], comparison["any_range_atr"]],
    ]


def _percent(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}%"


def _print_report(report: dict) -> None:
    if not report["available"]:
        print(report["message"])
        return

    filters = report["filters"]
    period = "all time" if filters["days"] is None else f"last {filters['days']} days"
    print("AI Agent Analysis Report")
    print(f"Mode: {filters['mode']} | Period: {period}")

    reliability = report["reliability"]
    print("\nReliability")
    print(f"Total decisions: {reliability['total']}")
    ok_pct = "-" if reliability["ok_pct"] is None else f"{reliability['ok_pct']:.1f}%"
    latency = "-" if reliability["avg_latency_s"] is None else f"{reliability['avg_latency_s']:.2f} s"
    print(f"Successful decisions: {ok_pct}")
    print(f"Average latency: {latency}")
    _table(["Status", "Count"], [[row["status"], row["count"]] for row in reliability["by_status"]])

    agreement = report["agreement"]
    print("\nAgreement")
    _table(
        ["Hours", "Same as fixed", "Same as baseline"],
        [[agreement["n"], agreement["pct_same_as_fixed"], agreement["pct_same_as_baseline"]]],
    )

    comparison = report["comparison"]
    print("\nAgent vs fixed vs baseline")
    print("efficiency = net move / total range in the hour (1 = clean trend, 0 = went nowhere)")
    print("range_atr = hour's range vs normal candle size")
    _table(["Pair", "Avg efficiency", "Avg range/ATR"], _comparison_rows(comparison))
    print(
        "Efficiency hours beating fixed / baseline: "
        f"{_percent(comparison['pct_beats_fixed_eff'])} / {_percent(comparison['pct_beats_base_eff'])}"
    )
    print(
        "Range/ATR hours beating fixed / baseline: "
        f"{_percent(comparison['pct_beats_fixed_range'])} / {_percent(comparison['pct_beats_base_range'])}"
    )

    disagreements = report["disagreements"]
    print("\nDisagreement hours only")
    _table(["Pair", "Avg efficiency", "Avg range/ATR"], _comparison_rows(disagreements))
    print(
        "Efficiency hours beating fixed / baseline: "
        f"{_percent(disagreements['pct_beats_fixed_eff'])} / {_percent(disagreements['pct_beats_base_eff'])}"
    )
    print(
        "Range/ATR hours beating fixed / baseline: "
        f"{_percent(disagreements['pct_beats_fixed_range'])} / {_percent(disagreements['pct_beats_base_range'])}"
    )

    print("\nBy market")
    _table(
        [
            "Market", "Hours", "Agent eff", "Fixed eff", "Base eff", "Any eff",
            "Agent range/ATR", "Fixed range/ATR", "Base range/ATR", "Any range/ATR",
            "Beat fixed eff", "Beat base eff", "Beat fixed range", "Beat base range",
        ],
        [[
            row["market"], row["n"], row["agent_eff"], row["fixed_eff"], row["base_eff"], row["any_eff"],
            row["agent_range_atr"], row["fixed_range_atr"], row["base_range_atr"], row["any_range_atr"],
            _percent(row["pct_beats_fixed_eff"]), _percent(row["pct_beats_base_eff"]),
            _percent(row["pct_beats_fixed_range"]), _percent(row["pct_beats_base_range"]),
        ] for row in report["by_market"]],
    )

    news = report["news_cost"]
    print("\nNews & cost")
    _table(
        ["News exclusions", "Input tokens", "Output tokens", "Estimated cost (USD)"],
        [[news["decisions_with_news_exclusion"], news["input_tokens"], news["output_tokens"], news["est_cost_usd"]]],
    )

    if report["live_pnl"]:
        print("\nLive P&L")
        _table(
            ["Market", "Trades", "P&L", "Win %"],
            [[row["market"], row["trades"], row["pnl"], row["win_pct"]] for row in report["live_pnl"]],
        )

    go_live = report["go_live"]
    print("\nGo-live checklist")
    _table(
        ["Result", "Check", "Value", "Target"],
        [["PASS" if row["passed"] else "FAIL", row["name"], row["value"], row["target"]]
         for row in go_live["checks"]],
    )
    print("READY" if go_live["ready"] else "NOT YET")
    print("\nThese are proxies for trendiness, not profit.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only AI-agent analysis report")
    parser.add_argument("--mode", choices=("all", "shadow", "live"), default="all")
    parser.add_argument("--days", type=int, help="limit target hours to the last N days")
    args = parser.parse_args()
    if args.days is not None and args.days < 1:
        parser.error("--days must be at least 1")

    conn = sqlite3.connect(f"file:{db.db_path()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        _print_report(build_report(conn, mode=args.mode, days=args.days))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())