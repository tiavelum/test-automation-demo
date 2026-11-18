"""R4, the status of a transfer, tested with state transition testing (ST): every valid
transition of docs/business-rules.md and every invalid one of its state table."""

import pytest

STATUSES = ["created", "confirmed", "executed", "cancelled", "rejected"]
EVENTS = ["confirm", "execute", "cancel"]
# The events the state table of R4 allows in each status.
VALID = {
    ("created", "confirm"),
    ("created", "cancel"),
    ("confirmed", "execute"),
    ("confirmed", "cancel"),
}


def test_new_transfer_starts_in_created(api, create):
    """R4, ST: the initial state of a transfer is created."""
    created = create().json()
    response = api.get(f"/transfers/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created
    assert created["status"] == "created"


@pytest.mark.parametrize(
    ("start", "event", "target"),
    [
        pytest.param("created", "confirm", "confirmed", id="R4-ST-T1-created-confirm-confirmed"),
        pytest.param("created", "cancel", "cancelled", id="R4-ST-T3-created-cancel-cancelled"),
        pytest.param("confirmed", "execute", "executed", id="R4-ST-T4-confirmed-execute-executed"),
        pytest.param("confirmed", "cancel", "cancelled", id="R4-ST-T5-confirmed-cancel-cancelled"),
    ],
)
def test_valid_transition(api, transfer_in, start, event, target):
    transfer_id = transfer_in(start)
    response = api.post(f"/transfers/{transfer_id}/{event}")
    assert response.status_code == 200
    assert response.json()["status"] == target
    assert api.get(f"/transfers/{transfer_id}").json()["status"] == target


def test_refused_confirmation_leads_to_rejected(api, create):
    """R4, ST, T2: created to rejected, when R3 refuses the confirmation."""
    transfer_id = create(amount="5000.01").json()["id"]
    assert api.post(f"/transfers/{transfer_id}/confirm").json()["status"] == "rejected"


@pytest.mark.parametrize(
    ("start", "event"),
    [
        pytest.param(start, event, id=f"R4-ST-invalid-{start}-{event}")
        for start in STATUSES
        for event in EVENTS
        if (start, event) not in VALID
    ],
)
def test_invalid_transition_is_refused(api, transfer_in, start, event):
    """R4, ST: an event the state table forbids is refused and leaves the status unchanged."""
    transfer_id = transfer_in(start)
    assert api.post(f"/transfers/{transfer_id}/{event}").status_code == 409
    assert api.get(f"/transfers/{transfer_id}").json()["status"] == start


@pytest.mark.parametrize("event", EVENTS, ids=lambda event: f"R4-EP-invalid-unknown-id-{event}")
def test_event_on_unknown_transfer_is_not_found(api, event):
    """R4, EP: an id that no transfer has is an invalid partition of the transfer id."""
    assert api.post(f"/transfers/no-such-id/{event}").status_code == 404
    assert api.get("/transfers/no-such-id").status_code == 404
