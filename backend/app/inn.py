def _check_digit(digits: str, weights: list[int]) -> int:
    return sum(int(d) * w for d, w in zip(digits, weights)) % 11 % 10


def is_valid_inn(inn: str) -> bool:
    """10 цифр — юрлицо, 12 — ИП. Проверяем контрольные цифры."""
    if not inn.isdigit():
        return False
    if len(inn) == 10:
        return _check_digit(inn, [2, 4, 10, 3, 5, 9, 4, 6, 8]) == int(inn[9])
    if len(inn) == 12:
        return (
            _check_digit(inn, [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) == int(inn[10])
            and _check_digit(inn, [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]) == int(inn[11])
        )
    return False
