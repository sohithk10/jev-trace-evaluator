"""CLI with machine-readable reports and conservative exit codes."""

import argparse
import hashlib
import json
import sys

from . import __version__
from .core import InputError, dump, evaluate, load_traces, policy_from


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit traces locally or evaluate with JEV. Never executes trace tools.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    ui = sub.add_parser("ui", help="Open a loopback-only offline evaluation dashboard")
    ui.add_argument("--port", type=int, default=8765)
    check = sub.add_parser("evaluate", help="Evaluate a JSON/JSONL trace export")
    check.add_argument("traces")
    check.add_argument("--policy")
    check.add_argument("--judge", choices=["offline", "jev"], default="offline")
    check.add_argument("--allow-network", action="store_true", help="Consent to sending unflagged trace content to TypeSafe")
    check.add_argument("--model", default="jev-latest")
    check.add_argument("--max-live-traces", type=int, default=10, help="Maximum live judge calls; default 10")
    args = parser.parse_args(argv)
    if args.command == "ui":
        from .web import serve
        if not 1 <= args.port <= 65535:
            parser.error("Port must be between 1 and 65535")
        serve(args.port)
        return 0
    try:
        policy = policy_from(args.policy)
        traces = load_traces(args.traces)
        if args.max_live_traces < 1:
            raise InputError("Live trace limit must be positive")
        judge = None
        if args.judge == "jev":
            if not args.allow_network:
                raise InputError("Live JEV requires --allow-network; trace content leaves this machine")
            if len(traces) > args.max_live_traces:
                raise InputError("Batch exceeds live trace limit")
            try:
                from .judge import JevJudge
                judge = JevJudge(args.model)
            except Exception:
                print(json.dumps({"error": "JEV setup failed. Install the jev extra and set TYPESAFE_API_KEY."}), file=sys.stderr)
                return 2
        results = [evaluate(trace, policy, judge) for trace in traces]
        report = {
            "schema_version": 1, "evaluator_version": __version__, "rubric_version": 1,
            "judge": args.judge, "model": args.model if judge else None,
            "threshold": policy["threshold"],
            "policy_sha256": hashlib.sha256(dump(policy).encode()).hexdigest(),
            "summary": {status: sum(r["status"] == status for r in results) for status in ("pass", "fail", "review")},
            "results": results,
        }
        print(json.dumps(report, indent=2, allow_nan=False))
        return 1 if report["summary"]["fail"] else 2 if report["summary"]["review"] else 0
    except (InputError, OSError, RecursionError):
        print(json.dumps({"error": "Invalid or unreadable input/policy. Check the documented schema and limits."}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
