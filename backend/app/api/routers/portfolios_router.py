from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.database import get_conn

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


class Holding(BaseModel):
    ticker: str
    weight: float


class PortfolioIn(BaseModel):
    id: str | None = None
    name: str
    holdings: list[Holding]


@router.get("")
def list_portfolios():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM portfolios ORDER BY rowid").fetchall()
    return [
        {"id": r["id"], "name": r["name"], "holdings": json.loads(r["holdings"])}
        for r in rows
    ]


@router.post("", status_code=201)
def create_portfolio(body: PortfolioIn):
    pid = body.id or str(uuid.uuid4())
    holdings_json = json.dumps([h.model_dump() for h in body.holdings])
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM portfolios WHERE id=?", (pid,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail=f"Portfolio '{pid}' already exists")
        conn.execute(
            "INSERT INTO portfolios (id, name, holdings) VALUES (?,?,?)",
            (pid, body.name, holdings_json),
        )
        conn.commit()
    return {"id": pid, "name": body.name, "holdings": body.holdings}


@router.delete("/{portfolio_id}", status_code=204)
def delete_portfolio(portfolio_id: str):
    with get_conn() as conn:
        result = conn.execute(
            "DELETE FROM portfolios WHERE id=?", (portfolio_id,)
        )
        conn.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Portfolio not found")
