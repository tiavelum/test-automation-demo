"""R3, the rule that decides whether a confirmation is accepted, tested with decision table
testing (DT): one case per column of the table in docs/business-rules.md."""

import pytest


@pytest.mark.parametrize(
    ("account_type", "amount", "second_confirmation", "expected"),
    [
        pytest.param("private", "5000.00", False, "confirmed", id="R3-DT-D1-private-low-single"),
        pytest.param("private", "5000.00", True, "confirmed", id="R3-DT-D2-private-low-second"),
        pytest.param("private", "5000.01", False, "rejected", id="R3-DT-D3-private-high-single"),
        pytest.param("private", "5000.01", True, "confirmed", id="R3-DT-D4-private-high-second"),
        pytest.param("savings", "5000.00", False, "rejected", id="R3-DT-D5-savings-low-single"),
        pytest.param("savings", "5000.00", True, "confirmed", id="R3-DT-D6-savings-low-second"),
        pytest.param("savings", "5000.01", False, "rejected", id="R3-DT-D7-savings-high-single"),
        pytest.param("savings", "5000.01", True, "rejected", id="R3-DT-D8-savings-high-second"),
    ],
)
def test_confirmation_follows_decision_table(
    api, create, account_type, amount, second_confirmation, expected
):
    """R3, DT: the amounts are the values either side of the threshold of 5000.00."""
    transfer_id = create(amount=amount, account_type=account_type).json()["id"]
    body = {"second_confirmation": second_confirmation}
    response = api.post(f"/transfers/{transfer_id}/confirm", json=body)
    assert response.status_code == 200
    assert response.json()["status"] == expected
    assert api.get(f"/transfers/{transfer_id}").json()["status"] == expected


def test_confirmation_without_body_gives_no_second_confirmation(api, create):
    """R3, EP: a confirmation without a body belongs to "no second confirmation" (column D3)."""
    transfer_id = create(amount="5000.01").json()["id"]
    assert api.post(f"/transfers/{transfer_id}/confirm").json()["status"] == "rejected"


def test_unknown_account_type_is_refused(create):
    """R3, EP: an account type other than private or savings is an invalid partition."""
    response = create(account_type="business")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "account_type"]


def test_confirmation_with_empty_object_gives_no_second_confirmation(api, create):
    """R3, EP: a body without the key counts as "no second confirmation" (column D3)."""
    transfer_id = create(amount="5000.01").json()["id"]
    response = api.post(f"/transfers/{transfer_id}/confirm", json={})
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
