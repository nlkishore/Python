"""JSON and HTML report writers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from pr_review.config.schema import Settings


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_html_summary(path: Path, settings: Settings, summary: dict[str, Any]) -> None:
    env = Environment(
        loader=PackageLoader("pr_review", "reports/templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("summary.html.j2")
    html = tpl.render(settings=settings, summary=summary)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
