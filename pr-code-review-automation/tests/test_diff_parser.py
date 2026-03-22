from pr_review.diff_parser import flatten_ranges, parse_unified_diff, ranges_to_json_serializable


def test_parse_simple_addition():
    diff = """diff --git a/Foo.java b/Foo.java
index 111..222 100644
--- a/Foo.java
+++ b/Foo.java
@@ -1,3 +1,4 @@
 line1
+new line
 line2
"""
    m = parse_unified_diff(diff)
    assert "Foo.java" in m
    flat = flatten_ranges(m["Foo.java"])
    assert 2 in flat


def test_ranges_json():
    m = {"A.java": [(1, 2), (5, 5)]}
    j = ranges_to_json_serializable(m)
    assert len(j) == 1
    assert j[0]["path"] == "A.java"
    assert len(j[0]["added_lines_flat"]) == 3
