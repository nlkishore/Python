import io
import zipfile
from pathlib import Path

from release_control.inventory.archives import digest_delta, inventory_archive


def _write_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def test_inventory_lists_members_and_nested_war(tmp_path: Path):
    war_buf = io.BytesIO()
    with zipfile.ZipFile(war_buf, "w") as war:
        war.writestr("WEB-INF/classes/com/bank/Foo.class", b"class-bytes")
    ear = tmp_path / "app.ear"
    _write_zip(ear, {"app.war": war_buf.getvalue(), "META-INF/application.xml": b"<xml/>"})
    inventory = inventory_archive(ear, name="full_binary")
    assert "app.war" in inventory.as_set()
    assert "app.war/WEB-INF/classes/com/bank/Foo.class" in inventory.as_set()
    assert inventory.digests["META-INF/application.xml"]


def test_digest_delta_finds_changed_member(tmp_path: Path):
    left_path = tmp_path / "uat.zip"
    right_path = tmp_path / "prod.zip"
    _write_zip(left_path, {"WEB-INF/classes/A.class": b"new"})
    _write_zip(right_path, {"WEB-INF/classes/A.class": b"old"})
    left = inventory_archive(left_path, name="uat")
    right = inventory_archive(right_path, name="prod")
    delta = digest_delta(left, right, name="uat_prod")
    assert "WEB-INF/classes/A.class" in delta.as_set()
