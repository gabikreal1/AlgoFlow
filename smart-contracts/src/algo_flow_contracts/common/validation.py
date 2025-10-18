"""Reusable validation routines."""

from pyteal import Assert, Expr, Int, Len, Or, Subroutine, TealType

from . import constants
from .expressions import max_workflow_bytes


@Subroutine(TealType.none)
def ensure_workflow_size(blob: Expr) -> Expr:
    return Assert(Len(blob) <= max_workflow_bytes())


@Subroutine(TealType.none)
def ensure_nonzero(value: Expr) -> Expr:
    return Assert(value != Int(0))


@Subroutine(TealType.none)
def ensure_owner(sender: Expr, owner: Expr) -> Expr:
    return Assert(sender == owner)


@Subroutine(TealType.none)
def ensure_authorized_keeper(sender: Expr, owner: Expr, keeper: Expr) -> Expr:
    return Assert(Or(sender == owner, sender == keeper))


@Subroutine(TealType.none)
def ensure_fee_bounds(fee_bps: Expr) -> Expr:
    return Assert(fee_bps <= Int(constants.MAX_KEEPER_FEE_BPS))
