from stayput import CAPABILITY_ID, CAPABILITY_VERSION, PRODUCT_FAMILY


def test_scaffold_identity() -> None:
    assert PRODUCT_FAMILY == "SaltyDiff"
    assert CAPABILITY_ID == "stayput"
    assert CAPABILITY_VERSION == "0.1.0"
