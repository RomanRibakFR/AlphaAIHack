"""
Модель вероятности дефолта (слой 2 политики) — модель задачи 2: две логистические регрессии,
для ИП и для юрлиц. Сами модели и код расчёта — models/pd/<ip|ul>/ (model.json + score.py),
пути — config/decision_policy.yaml → model. Бэкенд готовит вход (app.features.model_inputs)
и вызывает score.py как есть, ничего не пересчитывая сам.
"""
import importlib.util
import json
from functools import lru_cache
from pathlib import Path

from app.policy import config_dir, policy

OK = "SYNTHETIC_SIMULATOR"  # так score.py помечает успешный расчёт


class ModelUnavailable(Exception):
    pass


def root() -> Path:
    # models/ лежит рядом с config/: в репозитории — в корне, в контейнере — в /app
    return config_dir().parent


@lru_cache
def scorer():
    # score.py у ИП и ЮЛ одинаковый, модель выбирается файлом model.json
    spec = importlib.util.spec_from_file_location("pd_score", root() / "models" / "pd" / "ul" / "score.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache
def model(is_legal: bool) -> dict:
    path = policy()["model"]["ul_path" if is_legal else "ip_path"]
    return json.loads((root() / path).read_text(encoding="utf-8"))


def predict(inputs: dict, is_legal: bool) -> dict:
    """Вход — сырые данные в формате score.py; выход — pd, признаки, вклад каждого признака и версия модели."""
    try:
        result = scorer().score(inputs, model(is_legal))
    except Exception as e:  # битый файл модели — заявку отдаём человеку (M6)
        raise ModelUnavailable(str(e)) from e
    if result["status"] != OK:  # например, у юрлица нет отчётности
        raise ModelUnavailable("; ".join(result["errors"]))
    details = result["contribution_details"]
    return {
        "pd": result["pd_probability"],
        "features": {x["feature"]: x["input"] for x in details},
        # вклад в логит: плюс — риск выше среднего заёмщика, минус — ниже
        "contributions": {x["feature"]: round(x["logit_contribution"], 4) for x in details},
        "clipping_warnings": result["clipping_warnings"],
        "model_version": result["model_id"],
    }
