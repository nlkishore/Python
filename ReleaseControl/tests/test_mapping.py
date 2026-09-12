from release_control.mapping.paths import map_changes
from release_control.models import MappingDefaults, PrChange


def test_java_maps_to_class():
    mapped = map_changes(
        [PrChange(path="src/main/java/com/bank/Foo.java")],
        MappingDefaults(),
        reason="PR-1",
    )
    assert mapped[0].path == "WEB-INF/classes/com/bank/Foo.class"


def test_skip_pom_and_tests():
    mapped = map_changes(
        [
            PrChange(path="pom.xml"),
            PrChange(path="src/test/java/com/bank/FooTest.java"),
            PrChange(path="src/main/java/com/bank/Bar.java"),
        ]
    )
    assert [m.path for m in mapped] == ["WEB-INF/classes/com/bank/Bar.class"]


def test_unmapped_raises():
    from release_control.exceptions import MappingError

    try:
        map_changes([PrChange(path="docs/secret.bin")])
        raise AssertionError("expected MappingError")
    except MappingError as exc:
        assert "secret.bin" in exc.message
