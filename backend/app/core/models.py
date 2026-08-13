"""Shared document base. UUID primary keys per docs/04 RULE DB-002."""

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class BaseDocument(BaseModel):
    """Every document carries id / created_at / updated_at (RULE DB-003).

    `id` is persisted as MongoDB's `_id`, so no BSON ObjectId is ever produced
    and documents are JSON-serializable without conversion.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = Field(default_factory=new_id)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    deleted_at: datetime | None = None

    def to_mongo(self) -> dict[str, Any]:
        doc = self.model_dump()
        doc["_id"] = doc.pop("id")
        return doc

    @classmethod
    def from_mongo(cls, doc: dict[str, Any] | None):
        if not doc:
            return None
        data = dict(doc)
        if "_id" in data:
            data["id"] = data.pop("_id")
        return cls(**data)
