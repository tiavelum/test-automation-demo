"""R1, the amount range of a transfer, and R2, the daily limit of an account, tested with
equivalence partitioning (EP) and boundary value analysis (BVA)."""

from decimal import Decimal

import pytest


@pytest.mark.parametrize(
    "amount",
    [
        pytest.param("0.01", id="R1-BVA-lowest-valid-0.01"),
        pytest.param("2500.50", id="R1-EP-valid-2500.50"),
        pytest.param("10000.00", id="R1-BVA-highest-valid-10000.00"),
    ],
)
def test_amount_in_valid_partition_is_accepted(create, amount):
    response = create(amount=amount)
    assert response.status_code == 201
    assert response.json()["status"] == "created"
    assert Decimal(response.json()["amount"]) == Decimal(amount)


@pytest.mark.parametrize(
    "amount",
    [
        pytest.param("0.00", id="R1-BVA-highest-invalid-below-0.00"),
        pytest.param("-100.00", id="R1-EP-invalid-below-negative"),
        pytest.param("10000.01", id="R1-BVA-lowest-invalid-above-10000.01"),
        pytest.param("50000.00", id="R1-EP-invalid-above-50000.00"),
        pytest.param("12.345", id="R1-EP-invalid-three-decimal-places"),
        pytest.param("ten", id="R1-EP-invalid-not-a-number"),
        pytest.param(None, id="R1-EP-invalid-null"),
    ],
)
def test_amount_in_invalid_partition_is_refused(create, amount):
    response = create(amount=amount)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "amount"]


def test_daily_total_at_limit_is_accepted(create):
    """R2, BVA: transfers that add up to exactly the daily limit of 20000.00 are accepted."""
    for amount in ("10000.00", "9999.99", "0.01"):
        assert create(amount=amount).status_code == 201


def test_daily_total_above_limit_is_refused(create):
    """R2, BVA: the transfer that takes the daily total to 20000.01 is refused."""
    for amount in ("10000.00", "10000.00"):
        assert create(amount=amount).status_code == 201
    response = create(amount="0.01")
    assert response.status_code == 422
    assert response.json()["detail"] == "daily limit exceeded"


def test_cancelled_and_rejected_transfers_do_not_count(api, create):
    """R2, EP: cancelled and rejected transfers form the partition the daily limit leaves out."""
    cancelled = create(amount="10000.00").json()["id"]
    api.post(f"/transfers/{cancelled}/cancel").raise_for_status()
    rejected = create(amount="10000.00").json()["id"]
    assert api.post(f"/transfers/{rejected}/confirm").json()["status"] == "rejected"
    for amount in ("10000.00", "10000.00"):
        assert create(amount=amount).status_code == 201


def test_daily_limit_applies_per_account(create, account):
    """R2, EP: the transfers of another account form a partition the daily limit leaves out."""
    for amount in ("10000.00", "10000.00"):
        assert create(amount=amount).status_code == 201
    assert create(amount="10000.00", account_id=f"{account}-other").status_code == 201


def test_confirmed_and_executed_transfers_count(api, create):
    """R2, EP: confirmed and executed transfers count towards the daily limit."""
    for amount in ("10000.00", "10000.00"):
        transfer_id = create(amount=amount).json()["id"]
        body = {"second_confirmation": True}
        api.post(f"/transfers/{transfer_id}/confirm", json=body).raise_for_status()
    api.post(f"/transfers/{transfer_id}/execute").raise_for_status()
    assert create(amount="0.01").status_code == 422
