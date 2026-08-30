from hotfix_prep.exceptions import UnmappedMarketError


def test_lookup_sg(app_config) -> None:
    market = app_config.lookup_market("BANK", "core-app", "release/sg")
    assert market.id == "SG"
    assert market.hotfix_branch == "hotfix/sg"


def test_unknown_branch_raises(app_config) -> None:
    try:
        app_config.lookup_market("BANK", "core-app", "develop")
        raise AssertionError("expected UnmappedMarketError")
    except UnmappedMarketError:
        pass


def test_try_lookup_none(app_config) -> None:
    assert app_config.try_lookup("BANK", "core-app", "feature/x") is None


def test_seven_markets_loaded(app_config) -> None:
    ids = {m.id for m in app_config.document.markets}
    assert ids == {"SG", "IN", "HK", "MY", "TH", "ID", "VN"}
