"""Helpers for working with PyTeal ABI values."""

from pyteal import Expr, abi


def uint64_to_int(value: abi.Uint64) -> Expr:
    return value.get()
