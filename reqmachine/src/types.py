from typing import TypeAlias

# ─────────────────────────── Типы ───────────────────────────

TStr: TypeAlias = str | bytes
JsonDict: TypeAlias = dict[str, bool | int | str | list | dict]
JsonList: TypeAlias = list[JsonDict | str | int | float | bool]
JsonValue: TypeAlias = bool | int | float | str | bytes | None  | dict | list
ResponseRequest: TypeAlias = JsonValue

