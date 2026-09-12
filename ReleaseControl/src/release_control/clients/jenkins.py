"""Jenkins JSON: require SUCCESS and extract Artifactory download URIs."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from release_control.exceptions import HttpError, JenkinsError, JenkinsNotSuccessError
from release_control.http import HttpPort, RestClient


_ARCHIVE_SUFFIXES = (".ear", ".war", ".zip", ".jar")


class JenkinsClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        token: str,
        *,
        verify_ssl: bool = True,
        timeout: float = 60.0,
        http: HttpPort | None = None,
    ) -> None:
        self._owns_http = http is None
        self._http = http or RestClient(
            base_url,
            username=username,
            token=token,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def get_build(self, job: str, build: str | int = "lastSuccessfulBuild") -> dict[str, Any]:
        path = f"job/{quote(job, safe='')}/{quote(str(build), safe='')}/api/json"
        try:
            data = self._http.get_json(path, params={"tree": "result,number,url,timestamp,actions[*],artifacts[*]"})
        except HttpError as exc:
            raise JenkinsError(f"Jenkins {job} #{build} fetch failed: {exc.message}") from exc
        if not isinstance(data, dict):
            raise JenkinsError("Jenkins JSON was not an object")
        return data

    def require_success(self, job: str, build: str | int = "lastSuccessfulBuild") -> dict[str, Any]:
        data = self.get_build(job, build)
        result = str(data.get("result") or "")
        if result != "SUCCESS":
            raise JenkinsNotSuccessError(job, str(data.get("number") or build), result or "UNKNOWN")
        return data

    def artifactory_uris(self, build_json: dict[str, Any]) -> list[str]:
        found: list[str] = []
        seen: set[str] = set()

        def add(uri: str) -> None:
            cleaned = uri.strip()
            if not cleaned or cleaned in seen:
                return
            seen.add(cleaned)
            found.append(cleaned)

        for action in build_json.get("actions") or []:
            if not isinstance(action, dict):
                continue
            for key in ("remoteUrl", "downloadUri", "uri", "artifactoryUrl"):
                value = action.get(key)
                if isinstance(value, str) and _looks_like_artifact(value):
                    add(value)
            for module in action.get("modules") or []:
                if not isinstance(module, dict):
                    continue
                for artifact in module.get("artifacts") or []:
                    if isinstance(artifact, dict):
                        for key in ("downloadUri", "remoteUrl", "uri"):
                            value = artifact.get(key)
                            if isinstance(value, str) and _looks_like_artifact(value):
                                add(value)
            info = action.get("buildInfoUri")
            if isinstance(info, str) and info:
                add(info)

        for artifact in build_json.get("artifacts") or []:
            if isinstance(artifact, dict):
                rel = artifact.get("relativePath") or artifact.get("fileName")
                if isinstance(rel, str) and _looks_like_artifact(rel):
                    add(rel)

        return found


def _looks_like_artifact(value: str) -> bool:
    lower = value.lower()
    return lower.endswith(_ARCHIVE_SUFFIXES) or "/artifactory/" in lower or lower.endswith("/api/build")
