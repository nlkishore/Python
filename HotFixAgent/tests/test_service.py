from pathlib import Path

from hotfix_prep.idempotency.store import FileIdempotencyStore
from hotfix_prep.service import HotfixPrepService
from hotfix_prep.models import PrChange

from conftest import FakeBitbucket, FakeCommitter


def _service(app_config, repo_root: Path, bb: FakeBitbucket, committer: FakeCommitter, tmp_path: Path):
    store = FileIdempotencyStore(tmp_path / "idem")
    return HotfixPrepService(
        app_config,
        bb,
        committer,
        store,
        template_path=repo_root / "templates" / "buildScripts.sh.j2",
        base_dir=repo_root,
    )


def test_dry_run_generates_files_without_commit(
    app_config, repo_root, merged_event, tmp_path
) -> None:
    bb = FakeBitbucket()
    bb.changes = [PrChange(path="src/main/java/com/example/Foo.java", change_type="MODIFY")]
    committer = FakeCommitter()
    service = _service(app_config, repo_root, bb, committer, tmp_path)
    result = service.process(merged_event, dry_run=True)
    assert result.status == "dry_run"
    assert result.entry_count == 1
    assert result.market_id == "SG"
    assert "WEB-INF/classes/com/example/Foo.class" in (result.files_list_yaml or "")
    assert committer.calls == []
    assert bb.comments == []


def test_commit_pairs_both_files(app_config, repo_root, merged_event, tmp_path) -> None:
    bb = FakeBitbucket()
    bb.changes = [PrChange(path="src/main/java/com/example/Foo.java", change_type="MODIFY")]
    committer = FakeCommitter(sha="1111222233334444")
    service = _service(app_config, repo_root, bb, committer, tmp_path)
    result = service.process(merged_event, dry_run=False)
    assert result.status == "success"
    assert result.hotfix_commit == "1111222233334444"
    assert len(committer.calls) == 1
    call = committer.calls[0]
    assert call["hotfix_branch"] == "hotfix/sg"
    assert call["files_list_name"] == "filesList.txt"
    assert call["build_scripts_name"] == "buildScripts.sh"
    assert "CR-1234" in call["message"]
    assert bb.comments


def test_idempotent_second_call(app_config, repo_root, merged_event, tmp_path) -> None:
    bb = FakeBitbucket()
    bb.changes = [PrChange(path="src/main/java/com/example/Foo.java", change_type="MODIFY")]
    committer = FakeCommitter()
    service = _service(app_config, repo_root, bb, committer, tmp_path)
    first = service.process(merged_event, dry_run=False)
    second = service.process(merged_event, dry_run=False)
    assert first.status == "success"
    assert second.status == "already_processed"
    assert len(committer.calls) == 1


def test_unmapped_release_is_ignored(app_config, repo_root, merged_event, tmp_path) -> None:
    merged_event.to_branch = "develop"
    bb = FakeBitbucket()
    bb.changes = [PrChange(path="src/main/java/com/example/Foo.java", change_type="MODIFY")]
    service = _service(app_config, repo_root, bb, FakeCommitter(), tmp_path)
    result = service.process(merged_event, dry_run=False)
    assert result.status == "ignored"


def test_empty_list_fails_without_commit(app_config, repo_root, merged_event, tmp_path) -> None:
    bb = FakeBitbucket()
    bb.changes = [PrChange(path="README.md", change_type="MODIFY")]
    committer = FakeCommitter()
    service = _service(app_config, repo_root, bb, committer, tmp_path)
    result = service.process(merged_event, dry_run=False)
    assert result.status == "failed"
    assert result.error_code == "empty_file_list"
    assert committer.calls == []
