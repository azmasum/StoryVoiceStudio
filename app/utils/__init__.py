"""Shared application utilities."""
from app.utils.errors import UserFacingError, report_exception
from app.utils.hardware import HardwareInfo, detect_hardware
from app.utils.logging_setup import get_logger, setup_logging
from app.utils.updates import check_for_update

__all__ = [
    "UserFacingError",
    "report_exception",
    "HardwareInfo",
    "detect_hardware",
    "get_logger",
    "setup_logging",
    "check_for_update",
]
