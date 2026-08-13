"""List-endpoint pagination / sorting contract (RULES API-010, API-011, API-013)."""

from fastapi import Query
from pymongo import ASCENDING, DESCENDING

from app.core.errors import AppError

DEFAULT_SIZE = 20
MAX_SIZE = 100


class PageRequest:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="1-based page number"),
        size: int = Query(DEFAULT_SIZE, ge=1, le=MAX_SIZE, description="Page size (max 100)"),
        sort: str | None = Query(None, description="sort=field,direction e.g. created_at,desc"),
    ):
        self.page = page
        self.size = size
        self.sort_raw = sort

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.size

    def sort_spec(self, allowed: set[str], default: str = "created_at") -> list[tuple[str, int]]:
        if not self.sort_raw:
            return [(default, DESCENDING)]
        parts = self.sort_raw.split(",")
        field = parts[0].strip()
        direction = (parts[1].strip().lower() if len(parts) > 1 else "asc")
        if field not in allowed or direction not in {"asc", "desc"}:
            raise AppError(
                "VALIDATION-001",
                details=[{"field": "sort", "issue": f"Allowed sort fields: {sorted(allowed)} with asc|desc"}],
            )
        return [(field, ASCENDING if direction == "asc" else DESCENDING)]


def page_response(items: list, total: int, page_request: PageRequest) -> dict:
    return {
        "items": items,
        "page": page_request.page,
        "size": page_request.size,
        "total": total,
        "total_pages": (total + page_request.size - 1) // page_request.size if page_request.size else 0,
    }
