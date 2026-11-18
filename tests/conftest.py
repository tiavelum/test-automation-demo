"""Fixtures of the API tests: a client for the service under test and helpers that create
transfers through its API."""

import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")

# The events that take a new transfer to each status (R4); the amount that `transfer_in` uses
# for "rejected" makes R3 refuse the confirmation.
PATHS = {
    "created": [],
    "confirmed": ["confirm"],
    "executed": ["confirm", "execute"],
    "cancelled": ["cancel"],
    "rejected": ["confirm"],
}


class Api:
    def __init__(self, session: requests.Session) -> None:
        self.session = session

    def get(self, path: str) -> requests.Response:
        return self.session.get(BASE_URL + path, timeout=5)

    def post(self, path: str, json: object = None) -> requests.Response:
        return self.session.post(BASE_URL + path, json=json, timeout=5)


@pytest.fixture(scope="session")
def api():
    with requests.Session() as session:
        try:
            session.get(f"{BASE_URL}/health", timeout=5).raise_for_status()
        except requests.RequestException as error:
            pytest.exit(f"The service does not answer at {BASE_URL}: {error}", returncode=1)
        yield Api(session)


@pytest.fixture
def account():
    """An account of its own for each test, so that no test uses another's daily limit (R2)."""
    return f"CH-{uuid.uuid4().hex[:12]}"


@pytest.fixture
def create(api, account):
    """Returns a function that posts a new transfer and returns the response."""

    def create(amount="100.00", account_type="private", account_id=None):
        body = {
            "account": account_id or account,
            "recipient": "CH-recipient",
            "account_type": account_type,
            "amount": amount,
        }
        return api.post("/transfers", json=body)

    return create


@pytest.fixture
def transfer_in(api, create):
    """Returns a function that brings a new transfer into a status and returns its id."""

    def transfer_in(status):
        transfer_id = create(amount="5000.01" if status == "rejected" else "100.00").json()["id"]
        for event in PATHS[status]:
            api.post(f"/transfers/{transfer_id}/{event}").raise_for_status()
        assert api.get(f"/transfers/{transfer_id}").json()["status"] == status
        return transfer_id

    return transfer_in
