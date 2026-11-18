"""A minimal money-transfer service: the system under test of this repository.

The business rules it implements are specified in docs/business-rules.md; the rule ids in
the comments below (R1 to R4) refer to that document.
"""

import os
import threading
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

MIN_AMOUNT = Decimal("0.01")
MAX_AMOUNT = Decimal("10000.00")
DAILY_LIMIT = Decimal("20000.00")
SECOND_CONFIRMATION_THRESHOLD = Decimal("5000.00")
FORM_PAGE = Path(__file__).with_name("transfer-form.html")


class AccountType(StrEnum):
    PRIVATE = "private"
    SAVINGS = "savings"


class Status(StrEnum):
    CREATED = "created"
    CONFIRMED = "confirmed"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TransferRequest(BaseModel):
    account: Annotated[str, Field(min_length=1)]
    recipient: Annotated[str, Field(min_length=1)]
    account_type: AccountType
    # R1: the amount range per transfer, in CHF with at most two decimal places.
    amount: Annotated[Decimal, Field(ge=MIN_AMOUNT, le=MAX_AMOUNT, decimal_places=2)]


class ConfirmRequest(BaseModel):
    second_confirmation: bool = False


class Transfer(TransferRequest):
    id: str
    status: Status
    created_on: date


app = FastAPI(title="Money transfer")
transfers: dict[str, Transfer] = {}
# Request handlers run in a thread pool, so every read-modify-write of `transfers` holds it.
lock = threading.Lock()


def is_allowed(transfer: Transfer, second_confirmation: bool) -> bool:
    """R3: whether a confirmation is accepted, as the decision table states it."""
    within_threshold = transfer.amount <= SECOND_CONFIRMATION_THRESHOLD
    if transfer.account_type is AccountType.SAVINGS:
        return within_threshold and second_confirmation
    return within_threshold or second_confirmation


def get_transfer(transfer_id: str) -> Transfer:
    if transfer_id not in transfers:
        raise HTTPException(status_code=404, detail="transfer not found")
    return transfers[transfer_id]


def move(transfer_id: str, allowed_from: set[Status], target: Status) -> Transfer:
    """R4: moves a transfer to `target`, if its current status allows that transition."""
    transfer = get_transfer(transfer_id)
    if transfer.status not in allowed_from:
        raise HTTPException(
            status_code=409, detail=f"transition from {transfer.status} to {target} not allowed"
        )
    transfer.status = target
    return transfer


@app.get("/", include_in_schema=False)
def form_page() -> FileResponse:
    return FileResponse(FORM_PAGE)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/transfers", status_code=201)
def create_transfer(request: TransferRequest) -> Transfer:
    today = datetime.now(UTC).date()
    with lock:
        # R2: the daily limit counts every transfer of the account created today that is
        # neither cancelled nor rejected.
        used = sum(
            (
                t.amount
                for t in transfers.values()
                if t.account == request.account
                and t.created_on == today
                and t.status not in {Status.CANCELLED, Status.REJECTED}
            ),
            Decimal("0"),
        )
        if used + request.amount > DAILY_LIMIT:
            raise HTTPException(status_code=422, detail="daily limit exceeded")
        transfer = Transfer(
            **request.model_dump(), id=uuid.uuid4().hex, status=Status.CREATED, created_on=today
        )
        transfers[transfer.id] = transfer
    return transfer


@app.get("/transfers/{transfer_id}")
def read_transfer(transfer_id: str) -> Transfer:
    return get_transfer(transfer_id)


@app.post("/transfers/{transfer_id}/confirm")
def confirm_transfer(transfer_id: str, request: ConfirmRequest | None = None) -> Transfer:
    second_confirmation = request.second_confirmation if request else False
    with lock:
        transfer = get_transfer(transfer_id)
        target = Status.CONFIRMED if is_allowed(transfer, second_confirmation) else Status.REJECTED
        return move(transfer_id, {Status.CREATED}, target)


@app.post("/transfers/{transfer_id}/execute")
def execute_transfer(transfer_id: str) -> Transfer:
    with lock:
        return move(transfer_id, {Status.CONFIRMED}, Status.EXECUTED)


@app.post("/transfers/{transfer_id}/cancel")
def cancel_transfer(transfer_id: str) -> Transfer:
    with lock:
        return move(transfer_id, {Status.CREATED, Status.CONFIRMED}, Status.CANCELLED)


if __name__ == "__main__":
    uvicorn.run(
        app, host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000"))
    )
