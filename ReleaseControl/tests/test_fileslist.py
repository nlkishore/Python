from release_control.inventory.fileslist import parse_files_list


SAMPLE = """
version: 1
baseline:
  release_commit: abcdef1234567
source:
  pr_id: 1842
  market: SG
entries:
  - path: WEB-INF/classes/com/bank/Foo.class
    reason: PR-1842
  - path: WEB-INF/classes/com/bank/Bar.class
    reason: CR-99
"""


def test_parse_files_list_extracts_pr_and_paths():
    file_set = parse_files_list(SAMPLE)
    assert file_set.paths[0].endswith("Foo.class")
    assert 1842 in file_set.extras["pr_ids"]
    assert file_set.extras["source"]["market"] == "SG"
