"""Domain exceptions for HotFix prep."""


class HotfixPrepError(Exception):
    """Base error. ``code`` is a stable machine-readable identifier."""

    def __init__(self, message: str, *, code: str = "hotfix_prep_error") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ConfigError(HotfixPrepError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="config_error")


class UnmappedMarketError(HotfixPrepError):
    def __init__(self, branch: str) -> None:
        super().__init__(
            f"Target branch {branch!r} is not a mapped market release branch",
            code="unmapped_market",
        )
        self.branch = branch


class EmptyFileListError(HotfixPrepError):
    def __init__(self, message: str = "No HotFix entries after mapping and filtering") -> None:
        super().__init__(message, code="empty_file_list")


class UnmappedPathError(HotfixPrepError):
    def __init__(self, paths: list[str]) -> None:
        listed = ", ".join(paths[:20])
        extra = f" (+{len(paths) - 20} more)" if len(paths) > 20 else ""
        super().__init__(
            f"Source paths have no binary mapping: {listed}{extra}",
            code="unmapped_path",
        )
        self.paths = paths


class ValidationError(HotfixPrepError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="validation_error")


class BitbucketError(HotfixPrepError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="bitbucket_error")


class CommitError(HotfixPrepError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="commit_error")


class WebhookAuthError(HotfixPrepError):
    def __init__(self, message: str = "Invalid webhook signature") -> None:
        super().__init__(message, code="webhook_auth")
