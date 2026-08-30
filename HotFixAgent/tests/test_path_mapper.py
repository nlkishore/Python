from hotfix_prep.exceptions import EmptyFileListError, UnmappedPathError
from hotfix_prep.mapping.path_mapper import map_changes, map_single
from hotfix_prep.models import MappingDefaults, PrChange


def _defaults() -> MappingDefaults:
    return MappingDefaults(
        skip_globs=["**/src/test/**", "**/*Test.java", "**/*.md", "**/pom.xml"],
        java_roots=["src/main/java"],
        resource_roots=["src/main/resources"],
        webapp_roots=["src/main/webapp"],
        class_prefix="WEB-INF/classes",
        skip_deleted=True,
    )


def test_java_maps_to_class() -> None:
    target = map_single("src/main/java/com/example/Foo.java", _defaults())
    assert target == "WEB-INF/classes/com/example/Foo.class"


def test_resource_maps_under_classes() -> None:
    target = map_single("src/main/resources/application.properties", _defaults())
    assert target == "WEB-INF/classes/application.properties"


def test_webapp_keeps_relative_path() -> None:
    target = map_single("src/main/webapp/WEB-INF/web.xml", _defaults())
    assert target == "WEB-INF/web.xml"


def test_skips_tests_and_docs() -> None:
    d = _defaults()
    assert map_single("src/test/java/com/example/FooTest.java", d) is None
    assert map_single("README.md", d) is None
    assert map_single("pom.xml", d) is None


def test_map_changes_skips_deletes() -> None:
    changes = [
        PrChange(path="src/main/java/com/example/Foo.java", change_type="MODIFY"),
        PrChange(path="src/main/java/com/example/Old.java", change_type="DELETE"),
        PrChange(path="src/test/java/com/example/FooTest.java", change_type="ADD"),
    ]
    entries = map_changes(changes, _defaults(), reason="CR-1")
    assert [e.path for e in entries] == ["WEB-INF/classes/com/example/Foo.class"]
    assert entries[0].reason == "CR-1"


def test_unmapped_path_fails() -> None:
    changes = [PrChange(path="scripts/build.xml", change_type="MODIFY")]
    try:
        map_changes(changes, _defaults())
        raise AssertionError("expected UnmappedPathError")
    except UnmappedPathError as exc:
        assert "scripts/build.xml" in exc.paths


def test_empty_after_filter_fails() -> None:
    changes = [PrChange(path="README.md", change_type="MODIFY")]
    try:
        map_changes(changes, _defaults())
        raise AssertionError("expected EmptyFileListError")
    except EmptyFileListError:
        pass
