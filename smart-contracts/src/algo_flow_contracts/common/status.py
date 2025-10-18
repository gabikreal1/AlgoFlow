"""Status helpers for workflow lifecycle."""

from typing import Dict

from pyteal import Int

from . import constants


def status_to_int(status_code: int) -> Int:
    return Int(status_code)


def active() -> Int:
    return status_to_int(constants.INTENT_STATUS_ACTIVE)


def executing() -> Int:
    return status_to_int(constants.INTENT_STATUS_EXECUTING)


def success() -> Int:
    return status_to_int(constants.INTENT_STATUS_SUCCESS)


def failed() -> Int:
    return status_to_int(constants.INTENT_STATUS_FAILED)


def cancelled() -> Int:
    return status_to_int(constants.INTENT_STATUS_CANCELLED)


def known_status_codes() -> Dict[int, str]:
    return constants.INTENT_STATUS_NAMES.copy()
