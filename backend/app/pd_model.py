"""
Модель вероятности дефолта (слой 2 политики): логистическая регрессия на признаках F1–F6.

    PD = 1 / (1 + exp(-(b0 + Σ bi·xi)))

Коэффициенты — config/pd_model.yaml. Сейчас там временная калибровка под допущения
из тестовых данных (scripts/calibrate_pd.py); модель Ильи (задача 2) встаёт на это место
заменой файла — контракт вход/выход тот же.
"""
import math

from app.policy import pd_model_config

# как признак превращается во вход модели
TRANSFORMS = {
    "age": lambda f: math.log(max(f["F1_business_age_months"], 1)),
    "turnover": lambda f: math.log(max(f["F2_avg_monthly_turnover"], 1) / 1e6),
    "turnover_cv": lambda f: f["F3_turnover_cv"],
    "debt_load": lambda f: f["F4_debt_load"],
    "overdue_count": lambda f: f["F5_overdue_30plus_count_24m"],
    "overdue_max_months": lambda f: f["F5_max_overdue_days_24m"] / 30,
    "amount_to_turnover": lambda f: f["F6_amount_to_turnover"],
}

# к какому признаку политики относится вход — для текстов «почему так решили»
FEATURE_OF = {
    "age": "F1", "turnover": "F2", "turnover_cv": "F3", "debt_load": "F4",
    "overdue_count": "F5", "overdue_max_months": "F5", "amount_to_turnover": "F6",
}


class ModelUnavailable(Exception):
    pass


def inputs(features: dict) -> dict[str, float]:
    return {name: fn(features) for name, fn in TRANSFORMS.items()}


def predict(features: dict) -> dict:
    """На вход F1–F6, на выход pd, вклад каждого признака и версия модели."""
    try:
        cfg = pd_model_config()
        x = inputs(features)
        coef, mean = cfg["coefficients"], cfg["means"]
        logit = cfg["intercept"] + sum(coef[k] * x[k] for k in x)
    except Exception as e:  # битый конфиг, не тот признак — заявку отдаём человеку (M6)
        raise ModelUnavailable(str(e)) from e

    # вклад считаем относительно «среднего» клиента: плюс — риск выше среднего
    contributions = {}
    for k in x:
        f = FEATURE_OF[k]
        contributions[f] = round(contributions.get(f, 0) + coef[k] * (x[k] - mean[k]), 3)
    return {
        "pd": 1 / (1 + math.exp(-logit)),
        "contributions": contributions,
        "model_version": cfg["version"],
    }
