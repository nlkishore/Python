from pathlib import Path

from release_control.models import FileSet
from release_control.orchestrate.pipeline import run_from_sets
from release_control.reconcile.exceptions_registry import ExceptionRegistry
from release_control.reconcile.sets import compare_equal


def test_equal_sets_pass():
    pr = FileSet(name="pr_mapped", paths=["WEB-INF/classes/com/bank/Foo.class"])
    hf = FileSet(name="hotfix_list", paths=["WEB-INF/classes/com/bank/Foo.class"])
    report = run_from_sets(pr_mapped=pr, hotfix_list=hf)
    assert report.status == "PASS"
    assert compare_equal(pr, hf).ok


def test_missing_in_hotfix_fails():
    pr = FileSet(name="pr_mapped", paths=["WEB-INF/classes/com/bank/Foo.class"])
    hf = FileSet(name="hotfix_list", paths=["WEB-INF/classes/com/bank/Other.class"])
    report = run_from_sets(pr_mapped=pr, hotfix_list=hf)
    assert report.status == "FAIL"
    assert report.diffs[0].missing_in_right == ["WEB-INF/classes/com/bank/Foo.class"]


def test_config_zip_exception_drops_from_equation(tmp_path: Path):
    yaml_path = tmp_path / "exceptions.yaml"
    yaml_path.write_text(
        """
exceptions:
  - glob: "config/**"
    class: config_zip
    package: config.zip
""",
        encoding="utf-8",
    )
    registry = ExceptionRegistry.from_yaml(yaml_path)
    pr = FileSet(
        name="pr_mapped",
        paths=["WEB-INF/classes/com/bank/Foo.class", "config/app.properties"],
    )
    hf = FileSet(name="hotfix_list", paths=["WEB-INF/classes/com/bank/Foo.class"])
    zip_set = FileSet(name="hotfix_zip", paths=["WEB-INF/classes/com/bank/Foo.class"])
    report = run_from_sets(
        pr_mapped=pr, hotfix_list=hf, hotfix_zip=zip_set, registry=registry
    )
    assert report.status == "PASS"
    assert any("config/app.properties" in item for item in report.exceptions_applied)


def test_subset_binary_and_uat_delta():
    paths = ["WEB-INF/classes/com/bank/Foo.class"]
    pr = FileSet(name="pr_mapped", paths=paths)
    hf = FileSet(name="hotfix_list", paths=paths)
    binary = FileSet(
        name="full_binary",
        paths=paths + ["WEB-INF/web.xml"],
    )
    delta = FileSet(name="uat_prod", paths=paths)
    report = run_from_sets(
        pr_mapped=pr,
        hotfix_list=hf,
        full_binary=binary,
        uat_prod_delta=delta,
    )
    assert report.status == "PASS"
