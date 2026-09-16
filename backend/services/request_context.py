from __future__ import annotations

from contextvars import ContextVar

_user_id_var: ContextVar[str | None] = ContextVar("genresearch_user_id", default=None)


def set_user_id(user_id: str | None):
    return _user_id_var.set(user_id)


def get_user_id() -> str | None:
    return _user_id_var.get()


def reset_user_id(token) -> None:
    _user_id_var.reset(token)