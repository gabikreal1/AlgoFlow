"""Structured log helpers."""

from pyteal import Concat, Expr, Log, ScratchVar, Seq, Subroutine, TealType

from .expressions import (
    log_topic_execution_result,
    log_topic_intent_created,
    log_topic_intent_status,
)


@Subroutine(TealType.none)
def log_intent_created(intent_id_bytes: Expr, owner: Expr, version_bytes: Expr) -> Expr:
    payload = Concat(
        log_topic_intent_created(),
        intent_id_bytes,
        owner,
        version_bytes,
    )
    return Log(payload)


@Subroutine(TealType.none)
def log_intent_status(intent_id_bytes: Expr, status_bytes: Expr, actor: Expr) -> Expr:
    payload = Concat(
        log_topic_intent_status(),
        intent_id_bytes,
        status_bytes,
        actor,
    )
    return Log(payload)


@Subroutine(TealType.none)
def log_execution_result(intent_id_bytes: Expr, status_bytes: Expr, detail: Expr) -> Expr:
    tmp = ScratchVar()
    return Seq(
        tmp.store(detail),
        Log(
            Concat(
                log_topic_execution_result(),
                intent_id_bytes,
                status_bytes,
                tmp.load(),
            )
        ),
    )
