"""Tests for common.logging — consistent structured logging."""

import logging
import sys
from io import StringIO

import pytest

from common.logging import get_logger, setup_logging


class TestSetupLogging:
    """setup_logging should configure the root agent-fw logger."""

    def test_setup_creates_logger(self):
        logger = setup_logging()
        assert logger is not None
        assert logger.name == "agent-fw"

    def test_setup_respects_level(self):
        logger = setup_logging(level="DEBUG")
        assert logger.level == logging.DEBUG

    def test_setup_default_level_is_info(self):
        logger = setup_logging()
        assert logger.level == logging.INFO


class TestGetLogger:
    """get_logger should return module-prefixed loggers."""

    def test_returns_logger_with_prefix(self):
        logger = get_logger("governance")
        assert logger.name == "agent-fw.governance"

    def test_different_modules_get_different_loggers(self):
        gov = get_logger("governance")
        pm = get_logger("pattern-memory")
        assert gov.name != pm.name

    def test_none_module_returns_root(self):
        logger = get_logger(None)
        assert logger.name == "agent-fw"

    def test_caching_returns_same_logger(self):
        l1 = get_logger("governance")
        l2 = get_logger("governance")
        assert l1 is l2


class TestLoggerOutput:
    """Loggers should produce structured output."""

    def test_logger_emits_messages(self, caplog):
        setup_logging(level="DEBUG")
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG, logger="agent-fw.test"):
            logger.info("test message")
        assert "test message" in caplog.text

    def test_logger_includes_module_name(self, caplog):
        setup_logging(level="DEBUG")
        logger = get_logger("governance")
        with caplog.at_level(logging.DEBUG, logger="agent-fw.governance"):
            logger.info("checking claims")
        # The logger name should appear in the log record
        assert any("governance" in record.name for record in caplog.records)

    def test_logger_has_timestamp(self, caplog):
        setup_logging(level="DEBUG")
        logger = get_logger("test")
        with caplog.at_level(logging.DEBUG, logger="agent-fw.test"):
            logger.info("timestamped")
        # Log records should have a timestamp
        assert len(caplog.records) > 0
        assert caplog.records[0].created > 0
