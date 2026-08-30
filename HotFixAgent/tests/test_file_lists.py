from hotfix_prep.exceptions import ValidationError
from hotfix_prep.generate.file_lists import (
    build_file_list_document,
    extract_change_reason,
    render_file_list_yaml,
)
from hotfix_prep.generate.validator import validate_file_list_yaml, validate_paired_contents
from hotfix_prep.models import MappedEntry, MergedPrEvent


def test_extract_cr_from_branch() -> None:
    event = MergedPrEvent(
        pr_id=9,
        title="fix",
        from_branch="feature/CR-1234-fix-login",
        to_branch="release/sg",
        merge_commit="aaaaaaaa",
        project="BANK",
        slug="core-app",
    )
    assert extract_change_reason(event) == "CR-1234"


def test_file_list_yaml_valid(merged_event: MergedPrEvent) -> None:
    entries = [
        MappedEntry(
            source_path="src/main/java/com/example/Foo.java",
            path="WEB-INF/classes/com/example/Foo.class",
            reason="CR-1234",
        )
    ]
    doc = build_file_list_document(merged_event, entries, market_id="SG")
    yaml_text = render_file_list_yaml(doc)
    parsed = validate_file_list_yaml(yaml_text)
    assert parsed["version"] == 1
    assert parsed["baseline"]["release_commit"].startswith("deadbeef")
    assert parsed["entries"][0]["path"].endswith("Foo.class")
    assert "full_build_id" not in parsed["baseline"]


def test_rejects_parent_path() -> None:
    bad = """
version: 1
baseline:
  release_commit: deadbeefdead
entries:
  - path: "../etc/passwd"
"""
    try:
        validate_file_list_yaml(bad)
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass


def test_paired_contents_require_both() -> None:
    try:
        validate_paired_contents("version: 1\n", "")
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass
