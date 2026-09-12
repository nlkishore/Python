from release_control.clients.bitbucket import BitbucketServerClient
from tests.fakes import FakeHttp


def test_iter_pr_changes_paginates():
    http = FakeHttp(
        {
            "projects/BANK/repos/core-app/pull-requests/1842/changes": {
                "values": [
                    {"path": {"toString": "src/main/java/com/bank/Foo.java"}, "type": "MODIFY"}
                ],
                "isLastPage": True,
            }
        }
    )
    client = BitbucketServerClient("https://bb", "u", "t", http=http)
    changes = client.iter_pr_changes("BANK", "core-app", 1842)
    assert changes[0].path.endswith("Foo.java")
    assert changes[0].change_type == "MODIFY"


def test_get_raw_file_404_returns_none():
    from release_control.exceptions import HttpError

    http = FakeHttp(
        {
            "projects/BANK/repos/hotfix/raw/filesList.txt": HttpError("missing", status_code=404)
        }
    )
    client = BitbucketServerClient("https://bb", "u", "t", http=http)
    assert client.get_raw_file("BANK", "hotfix", "hotfix/sg", "filesList.txt") is None
