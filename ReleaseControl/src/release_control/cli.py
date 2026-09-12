"""One CLI, many subcommands. No local git clone."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from release_control.config import Settings
from release_control.connections import bitbucket_client, jenkins_client, load_settings
from release_control.exceptions import ReleaseControlError
from release_control.logging_config import configure_logging
from release_control.models import FileSet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release-control",
        description="Reconcile PR files, HotFix lists, and binaries (Bitbucket REST only).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    pr_files = sub.add_parser("pr-files", help="List mapped files for a Pull Request")
    pr_files.add_argument("--project", required=True)
    pr_files.add_argument("--slug", required=True)
    pr_files.add_argument("--pr-id", type=int, required=True)

    hf = sub.add_parser("hotfix-scan", help="Read filesList.txt from HotFix branch via REST")
    hf.add_argument("--project", required=True)
    hf.add_argument("--slug", required=True)
    hf.add_argument("--branch", required=True)
    hf.add_argument("--files-list-name", default="filesList.txt")

    jenkins = sub.add_parser("jenkins-artifact", help="Require SUCCESS and print Artifactory URIs")
    jenkins.add_argument("--job", required=True)
    jenkins.add_argument("--build", default="lastSuccessfulBuild")

    inventory = sub.add_parser("inventory", help="List members + SHA-256 of a local zip/ear/war")
    inventory.add_argument("--archive", required=True)
    inventory.add_argument("--name", default="archive")

    recon = sub.add_parser("reconcile", help="Compare FileSet JSON dumps")
    recon.add_argument("--pr-json", required=True)
    recon.add_argument("--hotfix-json", required=True)
    recon.add_argument("--zip-json", default=None)
    recon.add_argument("--binary-json", default=None)
    recon.add_argument("--patched-json", default=None)
    recon.add_argument("--delta-json", default=None)
    recon.add_argument("--exceptions", default=None)

    args = parser.parse_args(argv)
    settings = load_settings()
    configure_logging(settings.log_level)
    try:
        if args.command == "pr-files":
            return _pr_files(settings, args.project, args.slug, args.pr_id)
        if args.command == "hotfix-scan":
            return _hotfix_scan(
                settings, args.project, args.slug, args.branch, args.files_list_name
            )
        if args.command == "jenkins-artifact":
            return _jenkins(settings, args.job, args.build)
        if args.command == "inventory":
            return _inventory(args.archive, args.name)
        if args.command == "reconcile":
            return _reconcile(args)
    except ReleaseControlError as exc:
        print(json.dumps({"status": "FAIL", "code": exc.code, "error": exc.message}, indent=2))
        return 1
    parser.error("unknown command")
    return 2


def _pr_files(settings, project: str, slug: str, pr_id: int) -> int:
    from release_control.orchestrate.pipeline import collect_pr_set

    client = bitbucket_client(settings)
    try:
        file_set = collect_pr_set(client, project=project, slug=slug, pr_id=pr_id)
        print(json.dumps(file_set.model_dump(), indent=2))
        return 0
    finally:
        client.close()


def _hotfix_scan(
    settings: Settings, project: str, slug: str, branch: str, files_list_name: str
) -> int:
    from release_control.orchestrate.pipeline import collect_hotfix_set

    client = bitbucket_client(settings)
    try:
        file_set = collect_hotfix_set(
            client,
            project=project,
            slug=slug,
            branch=branch,
            files_list_name=files_list_name,
        )
        print(json.dumps(file_set.model_dump(), indent=2))
        return 0
    finally:
        client.close()


def _jenkins(settings, job: str, build: str) -> int:
    client = jenkins_client(settings)
    try:
        data = client.require_success(job, build)
        uris = client.artifactory_uris(data)
        print(
            json.dumps(
                {
                    "job": job,
                    "build": data.get("number"),
                    "result": data.get("result"),
                    "url": data.get("url"),
                    "artifactory_uris": uris,
                },
                indent=2,
            )
        )
        return 0 if uris else 1
    finally:
        client.close()


def _inventory(archive: str, name: str) -> int:
    from release_control.inventory.archives import inventory_archive

    file_set = inventory_archive(Path(archive), name=name)
    print(json.dumps(file_set.model_dump(), indent=2))
    return 0


def _load_set(path: str) -> FileSet:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return FileSet.model_validate(payload)


def _reconcile(args: argparse.Namespace) -> int:
    from release_control.orchestrate.pipeline import run_from_sets
    from release_control.reconcile.exceptions_registry import ExceptionRegistry

    registry = (
        ExceptionRegistry.from_yaml(Path(args.exceptions))
        if args.exceptions
        else ExceptionRegistry([])
    )
    report = run_from_sets(
        pr_mapped=_load_set(args.pr_json),
        hotfix_list=_load_set(args.hotfix_json),
        hotfix_zip=_load_set(args.zip_json) if args.zip_json else None,
        full_binary=_load_set(args.binary_json) if args.binary_json else None,
        patched=_load_set(args.patched_json) if args.patched_json else None,
        uat_prod_delta=_load_set(args.delta_json) if args.delta_json else None,
        registry=registry,
    )
    print(json.dumps(report.to_cli_dict(), indent=2))
    return 0 if report.status in {"PASS", "REVIEW"} else 1


if __name__ == "__main__":
    sys.exit(main())
