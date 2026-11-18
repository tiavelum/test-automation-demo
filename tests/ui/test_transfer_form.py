"""UI tests of the form page with Playwright for Python: R1, the amount range, and R2, the daily
limit, through the form, with equivalence partitioning (EP) and boundary value analysis (BVA),
and the transfer the form creates (R4)."""

import re

import pytest
from playwright.sync_api import Page, expect

CREATED = re.compile(r"^Transfer [0-9a-f]{32} created, status created$")
REFUSED = re.compile(r"^Rejected: ")


def submit_transfer(page: Page, account: str, amount: str, account_type: str = "private") -> None:
    """Fills the form the way a user does, finding each field by its label, and submits it."""
    page.goto("/")
    page.get_by_label("Account", exact=True).fill(account)
    page.get_by_label("Account type").select_option(account_type)
    page.get_by_label("Recipient", exact=True).fill("CH-recipient")
    page.get_by_label("Amount in CHF", exact=True).fill(amount)
    page.get_by_role("button", name="Create transfer").click()


@pytest.mark.parametrize(
    "amount",
    [
        pytest.param("0.01", id="R1-BVA-lowest-valid-0.01"),
        pytest.param("2500.50", id="R1-EP-valid-2500.50"),
        pytest.param("10000.00", id="R1-BVA-highest-valid-10000.00"),
    ],
)
def test_amount_in_valid_partition_is_accepted(page: Page, account, amount):
    submit_transfer(page, account, amount)
    # expect() retries until the page shows the text or its timeout passes, so the test needs
    # no wait for the response of the service.
    expect(page.get_by_role("status")).to_have_text(CREATED)


@pytest.mark.parametrize(
    "amount",
    [
        pytest.param("0.00", id="R1-BVA-highest-invalid-below-0.00"),
        pytest.param("10000.01", id="R1-BVA-lowest-invalid-above-10000.01"),
        pytest.param("ten", id="R1-EP-invalid-not-a-number"),
    ],
)
def test_amount_in_invalid_partition_is_refused(page: Page, account, amount):
    submit_transfer(page, account, amount)
    expect(page.get_by_role("status")).to_have_text(REFUSED)


@pytest.mark.parametrize("amount", [pytest.param("0.01", id="R2-BVA-above-limit-0.01")])
def test_amount_above_daily_limit_is_refused(page: Page, account, amount):
    """R2, BVA: the form shows the reason of the service, a string, not only a validation list."""
    for earlier in ("10000.00", "10000.00"):
        submit_transfer(page, account, earlier)
        expect(page.get_by_role("status")).to_have_text(CREATED)
    submit_transfer(page, account, amount)
    expect(page.get_by_role("status")).to_have_text("Rejected: daily limit exceeded")


@pytest.mark.parametrize("amount", [pytest.param("250.00", id="R4-ST-new-transfer-starts-created")])
def test_new_transfer_starts_in_created(page: Page, account, amount):
    """R4, ST: the transition of a new transfer into its initial state created. The case is
    also an integration check rather than a further state transition test: the transfer the
    form reports is the one the service holds, with the values entered."""
    submit_transfer(page, account, amount, account_type="savings")
    result = page.get_by_role("status")
    expect(result).to_have_text(CREATED)
    transfer_id = result.inner_text().split()[1]
    response = page.request.get(f"/transfers/{transfer_id}")
    assert response.status == 200
    transfer = response.json()
    assert transfer["status"] == "created"
    assert transfer["account"] == account
    assert transfer["account_type"] == "savings"
    assert transfer["amount"] == amount
