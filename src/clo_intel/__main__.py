from __future__ import annotations

import argparse
import json
import sys

from clo_intel.pipeline import run_all
from clo_intel.telemetry import configure_logging


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(prog="clo-intel")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run", help="Extract and contextualize every PDF in data/pdfs")
    serve = sub.add_parser("serve", help="Open the human-review UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    if args.cmd == "run":
        results = run_all()
        if not results:
            print("No PDFs in data/pdfs/", file=sys.stderr)
            return 1
        print(json.dumps([r.model_dump(mode="json") for r in results], indent=2))
        return 0

    import uvicorn

    uvicorn.run("clo_intel.api:app", host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
