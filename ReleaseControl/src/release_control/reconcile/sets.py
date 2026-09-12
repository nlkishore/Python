"""FileSet equality and subset checks after path normalization."""

from __future__ import annotations

from release_control.models import FileSet, SetDiff


def diff_sets(left: FileSet, right: FileSet) -> SetDiff:
    left_paths = left.as_set()
    right_paths = right.as_set()
    return SetDiff(
        left_name=left.name,
        right_name=right.name,
        missing_in_right=sorted(left_paths - right_paths),
        extra_in_right=sorted(right_paths - left_paths),
    )


def compare_equal(left: FileSet, right: FileSet) -> SetDiff:
    return diff_sets(left, right)


def compare_subset(inner: FileSet, outer: FileSet) -> SetDiff:
    """inner ⊆ outer. Extras on the outer side are ignored."""
    missing = sorted(inner.as_set() - outer.as_set())
    return SetDiff(
        left_name=inner.name,
        right_name=outer.name,
        missing_in_right=missing,
        extra_in_right=[],
    )
