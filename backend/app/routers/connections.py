"""Connections router: per-user, token-based connector credentials.

The decrypted secret is never returned — list/get expose only name + type.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.connectors import CONNECTORS
from app.crypto import encrypt_json
from app.database import get_db
from app.models import Connection, User
from app.ownership import get_owned_connection
from app.schemas import ConnectionCreate, ConnectionResponse

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("/catalog")
async def connector_catalog() -> dict[str, Any]:
    """The available connector types and their secret/node field names."""
    return CONNECTORS


@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    data: ConnectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Connection:
    if data.connector_type not in CONNECTORS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown connector type: {data.connector_type}",
        )
    connection = Connection(
        owner_id=current_user.id,
        name=data.name,
        connector_type=data.connector_type,
        encrypted_secret=encrypt_json(data.secret),
    )
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return connection


@router.get("", response_model=list[ConnectionResponse])
async def list_connections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Connection]:
    result = await db.execute(
        select(Connection)
        .where(Connection.owner_id == current_user.id)
        .order_by(Connection.created_at.desc())
    )
    return list(result.scalars().all())


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    connection = await get_owned_connection(db, connection_id, current_user)
    await db.delete(connection)
    await db.commit()
