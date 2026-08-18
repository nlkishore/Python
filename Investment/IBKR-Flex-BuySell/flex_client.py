"""IBKR Flex Web Service v3: SendRequest + GetStatement with polling."""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import httpx

FLEX_BASE_DEFAULT = (
    "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService"
)


class FlexServiceError(RuntimeError):
    pass


@dataclass
class FlexDownloadResult:
    reference_code: str
    raw_path: Path
    content_type: str  # csv | xml | unknown


def _text(elem: ET.Element | None) -> str | None:
    if elem is None or elem.text is None:
        return None
    return elem.text.strip()


def _parse_status_xml(text: str) -> dict[str, str]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise FlexServiceError(f"Invalid XML from Flex service: {exc}") from exc

    out: dict[str, str] = {}
    for child in root:
        if child.tag and child.text:
            out[child.tag] = child.text.strip()
    if not out:
        for node in root.iter():
            if node.text and node.text.strip() and node.tag:
                out[node.tag] = node.text.strip()
    return out


def send_request(
    *,
    token: str,
    query_id: str,
    base_url: str = FLEX_BASE_DEFAULT,
    from_date: str | None = None,
    to_date: str | None = None,
    user_agent: str = "Python/3.11",
    timeout: float = 60.0,
) -> str:
    params: dict[str, str] = {"t": token, "q": str(query_id), "v": "3"}
    if from_date:
        params["fd"] = from_date
    if to_date:
        params["td"] = to_date

    url = f"{base_url.rstrip('/')}/SendRequest"
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url, params=params, headers={"User-Agent": user_agent})
        resp.raise_for_status()

    meta = _parse_status_xml(resp.text)
    status = meta.get("Status", "")
    if status.lower() != "success":
        msg = meta.get("ErrorMessage") or meta.get("ErrorCode") or resp.text[:500]
        raise FlexServiceError(f"SendRequest failed ({status}): {msg}")

    ref = meta.get("ReferenceCode")
    if not ref:
        raise FlexServiceError("SendRequest succeeded but no ReferenceCode in response.")
    return ref


def get_statement(
    *,
    token: str,
    reference_code: str,
    base_url: str = FLEX_BASE_DEFAULT,
    user_agent: str = "Python/3.11",
    timeout: float = 120.0,
) -> str:
    url = f"{base_url.rstrip('/')}/GetStatement"
    params = {"t": token, "q": reference_code, "v": "3"}

    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url, params=params, headers={"User-Agent": user_agent})
        resp.raise_for_status()
        return resp.text


def download_flex_report(
    *,
    token: str,
    query_id: str,
    output_dir: Path,
    from_date: str | None = None,
    to_date: str | None = None,
    base_url: str = FLEX_BASE_DEFAULT,
    poll_seconds: float = 10.0,
    max_poll_attempts: int = 36,
    user_agent: str = "Python/3.11",
) -> FlexDownloadResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    ref = send_request(
        token=token,
        query_id=query_id,
        base_url=base_url,
        from_date=from_date,
        to_date=to_date,
        user_agent=user_agent,
    )

    last_error = ""
    body = ""
    for attempt in range(1, max_poll_attempts + 1):
        body = get_statement(
            token=token,
            reference_code=ref,
            base_url=base_url,
            user_agent=user_agent,
        )
        stripped = body.lstrip()
        if stripped.startswith("<?xml") and "<Status>" in body:
            meta = _parse_status_xml(body)
            status = meta.get("Status", "")
            code = meta.get("ErrorCode", "")
            if status.lower() == "success" and "ReferenceCode" not in meta:
                # Some successes return data directly in XML wrapper — fall through
                if "<FlexStatement" in body or "<FlexQueryResponse" in body:
                    break
            if code in ("1019", "1018") or "generation in progress" in body.lower():
                last_error = meta.get("ErrorMessage", code)
                time.sleep(poll_seconds)
                continue
            if status.lower() != "success":
                raise FlexServiceError(
                    f"GetStatement failed: {meta.get('ErrorMessage') or meta}"
                )
        break
    else:
        raise FlexServiceError(
            f"Timed out waiting for Flex report (ref={ref}). Last: {last_error}"
        )

    content_type = "unknown"
    if (
        "Transaction History,Header" in body
        or body.startswith("Statement,Header")
        or ("Buy/Sell" in body.split("\n", 1)[0] and "TradeDate" in body.split("\n", 1)[0])
    ):
        content_type = "csv"
        suffix = ".csv"
    elif body.lstrip().startswith("<?xml") or body.lstrip().startswith("<"):
        content_type = "xml"
        suffix = ".xml"
    else:
        suffix = ".txt"

    if from_date and to_date:
        out_path = output_dir / f"flex_{query_id}_{from_date}_{to_date}{suffix}"
    else:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out_path = output_dir / f"flex_{query_id}_{stamp}{suffix}"
    out_path.write_text(body, encoding="utf-8")
    return FlexDownloadResult(reference_code=ref, raw_path=out_path, content_type=content_type)
