"""Helpers to expose PyTeal expressions for shared constants."""

from pyteal import Bytes, Int

from . import constants


def box_prefix_intent() -> Bytes:
    return Bytes(constants.BOX_PREFIX_INTENT_LITERAL)


def box_prefix_audit() -> Bytes:
    return Bytes(constants.BOX_PREFIX_AUDIT_LITERAL)


def box_key_separator() -> Bytes:
    return Bytes(constants.BOX_KEY_SEPARATOR_LITERAL)


def max_workflow_bytes() -> Int:
    return Int(constants.MAX_WORKFLOW_BYTES_LITERAL)


def max_audit_log_bytes() -> Int:
    return Int(constants.MAX_AUDIT_LOG_BYTES_LITERAL)


def g_owner_key() -> Bytes:
    return Bytes(constants.G_OWNER_LITERAL)


def g_keeper_key() -> Bytes:
    return Bytes(constants.G_KEEPER_LITERAL)


def g_version_key() -> Bytes:
    return Bytes(constants.G_VERSION_LITERAL)


def g_next_intent_key() -> Bytes:
    return Bytes(constants.G_NEXT_INTENT_LITERAL)


def g_min_collateral_key() -> Bytes:
    return Bytes(constants.G_MIN_COLLATERAL_LITERAL)


def g_storage_app_key() -> Bytes:
    return Bytes(constants.G_STORAGE_APP_LITERAL)


def g_fee_split_bps_key() -> Bytes:
    return Bytes(constants.G_FEE_SPLIT_BPS_LITERAL)


def g_executor_app_key() -> Bytes:
    return Bytes(constants.G_EXECUTOR_APP_LITERAL)


def log_topic_intent_created() -> Bytes:
    return Bytes(constants.LOG_TOPIC_INTENT_CREATED_LITERAL)


def log_topic_intent_status() -> Bytes:
    return Bytes(constants.LOG_TOPIC_INTENT_STATUS_LITERAL)


def log_topic_execution_result() -> Bytes:
    return Bytes(constants.LOG_TOPIC_EXECUTION_RESULT_LITERAL)
