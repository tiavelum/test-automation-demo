"""A minimal money-transfer service: the system under test of this repository.

The business rules it implements are specified in docs/business-rules.md; the rule ids in
the comments below (R1 to R4) refer to that document.
"""

import os
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

MIN_AMOUNT = Decimal("0.01")
MAX_AMOUNT = Decimal("10000.00")
DAILY_LIMIT = Decimal("20000.00")
SECOND_CONFIRMATION_THRESHOLD = Decimal("5000.00")
FORM_PAGE = Path(__file__).with_name("transfer-form.html")

Status = Literal["created", "confirmed", "executed", "cancelled", "rejected"]


class TransferRequest(BaseModel):
    account: str = Field(min_length=1)
    recipient: str = Field(min_length=1)
    account_type: Literal["private", "savings"]
    # R1: the amount range per transfer, in CHF with at most two decimal places.
    amount: Decimal = Field(ge=MIN_AMOUNT, le=MAX_AMOUNT, decimal_places=2)


class ConfirmRequest(BaseModel):
    second_confirmation: bool = False


class Transfer(TransferRequest):
    id: str
    status: Status
    created_on: date


app = FastAPI(title="Money transfer")
# The handlers are async and never wait, so they run one at a time on the event loop and
# no two requests change `transfers` at once.
transfers: dict[str, Transfer] = {}


def is_allowed(transfer: Transfer, second_confirmation: bool) -> bool:
    """R3: whether a confirmation is accepted, as the decision table states it."""
    within_threshold = transfer.amount <= SECOND_CONFIRMATION_THRESHOLD
    if transfer.account_type == "savings":
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
async def form_page() -> FileResponse:
    return FileResponse(FORM_PAGE)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/transfers", status_code=201)
async def create_transfer(request: TransferRequest) -> Transfer:
    today = datetime.now(UTC).date()
    # R2: the daily limit counts every transfer of the account created today that is
    # neither cancelled nor rejected.
    used = sum(
        (
            t.amount
            for t in transfers.values()
            if t.account == request.account
            and t.created_on == today
            and t.status not in {"cancelled", "rejected"}
        ),
        Decimal("0"),
    )
    if used + request.amount > DAILY_LIMIT:
        raise HTTPException(status_code=422, detail="daily limit exceeded")
    transfer = Transfer(
        **request.model_dump(), id=uuid.uuid4().hex, status="created", created_on=today
    )
    transfers[transfer.id] = transfer
    return transfer


@app.get("/transfers/{transfer_id}")
async def read_transfer(transfer_id: str) -> Transfer:
    return get_transfer(transfer_id)


@app.post("/transfers/{transfer_id}/confirm")
async def confirm_transfer(transfer_id: str, request: ConfirmRequest | None = None) -> Transfer:
    second_confirmation = request.second_confirmation if request else False
    transfer = get_transfer(transfer_id)
    target = "confirmed" if is_allowed(transfer, second_confirmation) else "rejected"
    return move(transfer_id, {"created"}, target)


@app.post("/transfers/{transfer_id}/execute")
async def execute_transfer(transfer_id: str) -> Transfer:
    return move(transfer_id, {"confirmed"}, "executed")


@app.post("/transfers/{transfer_id}/cancel")
async def cancel_transfer(transfer_id: str) -> Transfer:
    return move(transfer_id, {"created", "confirmed"}, "cancelled")


if __name__ == "__main__":
    uvicorn.run(
        app, host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000"))
    )
