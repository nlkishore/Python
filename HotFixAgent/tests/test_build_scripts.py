from pathlib import Path

from hotfix_prep.generate.build_scripts import apply_variables, patch_or_template


def test_patches_existing_exports() -> None:
    original = "#!/bin/bash\nexport HF_NUMBER=OLD\nexport TARGET_BRANCH=old\necho hi\n"
    updated = apply_variables(
        original,
        hf_number="CR-9",
        target_branch="release/sg",
        market="SG",
        pr_id="12",
        release_commit="abc1234",
        file_list_name="filesList.txt",
    )
    assert "export HF_NUMBER=CR-9" in updated
    assert "export TARGET_BRANCH=release/sg" in updated
    assert "export MARKET=SG" in updated
    assert "echo hi" in updated


def test_template_used_when_missing(repo_root: Path) -> None:
    text = patch_or_template(
        None,
        repo_root / "templates" / "buildScripts.sh.j2",
        hf_number="CR-1",
        target_branch="release/in",
        market="IN",
        pr_id="3",
        release_commit="ffffaaaabbbbccccddddeeeeffffaaaa",
        file_list_name="filesList.txt",
    )
    assert "HF_NUMBER=CR-1" in text
    assert "{{" not in text
