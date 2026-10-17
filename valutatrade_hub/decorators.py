from functools import wraps

from valutatrade_hub.logging_config import configure_logging


def log_action(action: str, verbose: bool = False):
    """Записать результат операции и пробросить её ошибку дальше."""

    def decorator(function):
        @wraps(function)
        def wrapper(user, currency_code, amount):
            logger = configure_logging()
            username = user.username

            try:
                result = function(user, currency_code, amount)
            except Exception as error:
                logger.info(
                    "action=%s username=%r currency_code=%r amount=%r "
                    "base=USD result=ERROR error_type=%s error_message=%r",
                    action,
                    username,
                    currency_code,
                    amount,
                    type(error).__name__,
                    str(error),
                )
                raise

            before, after, estimated = result
            details = f" before={before:.4f} after={after:.4f}" if verbose else ""
            logger.info(
                "action=%s username=%r currency_code=%r amount=%r "
                "rate=%.8f base=USD result=OK%s",
                action,
                username,
                currency_code,
                amount,
                estimated / amount,
                details,
            )
            return result

        return wrapper

    return decorator