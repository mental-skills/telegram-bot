import logging
import sys

SENSITIVE_MARKERS = ("TELEGRAM_BOT_TOKEN", "DATABASE_URL", "token", "password")


class SecretRedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for marker in SENSITIVE_MARKERS:
            if marker.lower() in message.lower():
                record.msg = "[redacted sensitive log message]"
                record.args = ()
                break
        return True


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(SecretRedactingFilter())
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[handler],
        force=True,
    )
