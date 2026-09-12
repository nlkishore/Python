from release_control.clients.jenkins import JenkinsClient
from release_control.exceptions import JenkinsNotSuccessError
from tests.fakes import FakeHttp


def test_require_success_and_extract_uri():
    http = FakeHttp(
        {
            "job/geb-sg-release/lastSuccessfulBuild/api/json": {
                "result": "SUCCESS",
                "number": 88,
                "url": "https://jenkins/job/geb-sg-release/88/",
                "actions": [
                    {
                        "remoteUrl": "https://artifactory.example.com/artifactory/libs/app-88.ear"
                    }
                ],
                "artifacts": [],
            }
        }
    )
    client = JenkinsClient("https://jenkins", "u", "t", http=http)
    data = client.require_success("geb-sg-release")
    uris = client.artifactory_uris(data)
    assert data["result"] == "SUCCESS"
    assert uris[0].endswith("app-88.ear")


def test_require_success_rejects_failure():
    http = FakeHttp(
        {
            "job/geb-sg-release/99/api/json": {
                "result": "FAILURE",
                "number": 99,
                "actions": [],
                "artifacts": [],
            }
        }
    )
    client = JenkinsClient("https://jenkins", "u", "t", http=http)
    try:
        client.require_success("geb-sg-release", 99)
        raise AssertionError("expected JenkinsNotSuccessError")
    except JenkinsNotSuccessError as exc:
        assert "FAILURE" in str(exc)
