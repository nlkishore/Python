"""Domain errors. ``code`` is stable for CLI JSON."""


class ReleaseControlError(Exception):
    def __init__(self, message: str, *, code: str = "release_control_error") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ConfigError(ReleaseControlError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="config_error")


class HttpError(ReleaseControlError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message, code="http_error")
        self.status_code = status_code


class BitbucketError(ReleaseControlError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="bitbucket_error")


class JenkinsError(ReleaseControlError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="jenkins_error")


class ArtifactoryError(ReleaseControlError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="artifactory_error")


class MappingError(ReleaseControlError):
    def __init__(self, message: str, *, paths: list[str] | None = None) -> None:
        super().__init__(message, code="mapping_error")
        self.paths = paths or []


class InventoryError(ReleaseControlError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="inventory_error")


class JenkinsNotSuccessError(JenkinsError):
    def __init__(self, job: str, build: str, result: str) -> None:
        super().__init__(f"Jenkins {job} #{build} is {result!r}, expected SUCCESS")
        self.job = job
        self.build = build
        self.result = result
