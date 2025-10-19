"""Helpers for inner transaction fields missing in the current PyTeal release."""

from __future__ import annotations

from typing import Iterable, Tuple

from pyteal import Expr, Seq
from pyteal.types import TealType, require_type
from pyteal.errors import verifyProgramVersion
from pyteal.ir import Op, TealBlock, TealOp


class _InnerTxnSetBoxes(Expr):
    """Expression that emits ``itxn_field Boxes`` with a single reference."""

    def __init__(self, app_id: Expr, box_name: Expr) -> None:
        super().__init__()
        require_type(app_id, TealType.uint64)
        require_type(box_name, TealType.bytes)
        self._app_id = app_id
        self._box_name = box_name

    def __teal__(self, options):
        verifyProgramVersion(
            Op.itxn_field.min_version,
            options.version,
            "Program version too low to set inner transaction boxes",
        )
        return TealBlock.FromOp(
            options,
            TealOp(self, Op.itxn_field, "Boxes"),
            self._app_id,
            self._box_name,
        )

    def type_of(self):
        return TealType.none

    def has_return(self):
        return False

    def __str__(self) -> str:
        return "(itxn_field Boxes)"


def itxn_set_box_reference(app_id: Expr, box_name: Expr) -> Expr:
    """Emit ``itxn_field Boxes`` for a single ``(app_id, box_name)`` tuple."""

    return _InnerTxnSetBoxes(app_id, box_name)


def itxn_set_box_references(entries: Iterable[Tuple[Expr, Expr]]) -> Expr:
    """Emit ``itxn_field Boxes`` for each tuple in ``entries``."""

    exprs = [itxn_set_box_reference(app_id, box_name) for app_id, box_name in entries]
    if len(exprs) == 1:
        return exprs[0]
    return Seq(*exprs)
