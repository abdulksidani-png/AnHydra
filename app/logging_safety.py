"""Drop query strings from access logs and redact accidental credential strings."""
import logging
import re


class RedactCredentials(logging.Filter):
    def filter(self, record):
        if record.name == "uvicorn.access" and isinstance(record.args, tuple) and len(record.args) == 5:
            args = list(record.args)
            args[2] = str(args[2]).split("?", 1)[0]
            record.args = tuple(args)
        message = record.getMessage()
        message = re.sub(r"(?i)\bBearer\s+[^\s,;\"']+", "Bearer [REDACTED]", message)
        message = re.sub(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[REDACTED]", message)
        message = re.sub(r"(?i)postgres(?:ql)?(?:\+psycopg)?://[^\s]+", "[REDACTED_DATABASE_URL]", message)
        record.msg, record.args = message, ()
        return True


def install_redaction():
    redactor = RedactCredentials()
    for name in ("", "uvicorn", "uvicorn.error", "uvicorn.access", "httpx", "httpcore", "sqlalchemy.engine"):
        logger = logging.getLogger(name)
        logger.addFilter(redactor)
        for handler in logger.handlers:
            handler.addFilter(redactor)
