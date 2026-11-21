# ─────────────────────────── Типы ───────────────────────────

type JsonDict = dict[str, bool | int | str | list | dict]
type JsonList = list[JsonDict | str | int | float | bool]
type JsonValue = bool | int | float | str | bytes | None | dict | list
type ResponseRequest = dict | list | bytes | None
