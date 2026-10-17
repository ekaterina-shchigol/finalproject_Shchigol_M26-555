class InsufficientFundsError(ValueError):
    """Недостаточно средств в валютном кошельке."""

    def __init__(self, available: float, required: float, code: str) -> None:
        super().__init__(
            f"Недостаточно средств: доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )


class CurrencyNotFoundError(ValueError):
    """Код валюты отсутствует в реестре."""

    def __init__(self, code: str) -> None:
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(RuntimeError):
    """Не удалось получить актуальные курсы."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")