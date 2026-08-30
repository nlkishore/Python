"""CLI: ``hotfix-prep serve`` and ``hotfix-prep process --dry-run``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hotfix_prep.logging_config import configure_logging
from hotfix_prep.wiring import build_service, package_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hotfix-prep",
        description="Detect Bitbucket PR merge and commit HotFix metadata.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run the webhook API")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    process = sub.add_parser("process", help="Process one merged PR (replay / dry-run)")
    process.add_argument("--project", required=True)
    process.add_argument("--slug", required=True)
    process.add_argument("--pr-id", type=int, required=True)
    process.add_argument("--dry-run", action="store_true")
    process.add_argument("--base-dir", default=None)

    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve(args.host, args.port)
    if args.command == "process":
        base = Path(args.base_dir) if args.base_dir else package_root()
        return _process(args.project, args.slug, args.pr_id, args.dry_run, base)
    parser.error("unknown command")
    return 2


def _serve(host: str | None, port: int | None) -> int:
    from hotfix_prep.config import Settings

    settings = Settings()
    configure_logging(settings.log_level)
    import uvicorn

    uvicorn.run(
        "hotfix_prep.api.app:app",
        host=host or settings.host,
        port=port or settings.port,
        reload=False,
    )
    return 0


def _process(project: str, slug: str, pr_id: int, dry_run: bool, base_dir: Path) -> int:
    service, _config, bitbucket = build_service(base_dir=base_dir)
    try:
        event = bitbucket.get_pull_request(project, slug, pr_id)
        result = service.process(event, dry_run=dry_run)
        print(json.dumps(result.model_dump(), indent=2))
        return 0 if result.status in {"success", "dry_run", "ignored", "already_processed"} else 1
    finally:
        bitbucket.close()


if __name__ == "__main__":
    sys.exit(main())
