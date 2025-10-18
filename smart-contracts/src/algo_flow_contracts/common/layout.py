"""Helpers for deriving box keys and field names."""

from pyteal import Bytes, Concat, Expr, Itob

from .expressions import box_key_separator, box_prefix_intent, box_prefix_audit


def intent_box_key(intent_id: Expr) -> Expr:
    return Concat(box_prefix_intent(), Itob(intent_id))


def audit_box_key(intent_id: Expr, index: Expr) -> Expr:
    separator = box_key_separator()
    return Concat(box_prefix_audit(), Itob(intent_id), separator, Itob(index))
