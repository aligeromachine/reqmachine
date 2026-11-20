# ─────────────────────────── Конфиг ───────────────────────────

from typing import ClassVar


class Config:
    API_TIMEOUT: tuple[float, float] = (3.0, 60.0)
    API_UPLOAD_TIMEOUT: tuple[float, float] = (10.0, 600.0)
    API_HEADERS: ClassVar[dict[str, str]] = {
        "Cache-Control": "no-cache",
        "Accept": "*/*",
    }
    RETRY_TOTAL: int = 0
    RETRY_BACKOFF: float = 0.5
    RETRY_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})
    CHUNK_SIZE: int = 5 * 1024 * 1024  # 5 MiB
