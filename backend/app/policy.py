"""Параметры кредитной политики — из config/decision_policy.yaml (его ведёт Аскар, задача 4)."""
import os
from functools import lru_cache
from pathlib import Path

import yaml

HERE = Path(__file__).resolve()
# в контейнере конфиг лежит рядом с приложением, при запуске из репозитория — в корне
CANDIDATES = [HERE.parents[1] / "config", HERE.parents[2] / "config"]


def config_dir() -> Path:
    if os.getenv("CONFIG_DIR"):
        return Path(os.environ["CONFIG_DIR"])
    for path in CANDIDATES:
        if (path / "decision_policy.yaml").exists():
            return path
    raise FileNotFoundError("не нашёл config/decision_policy.yaml")


@lru_cache
def policy() -> dict:
    return yaml.safe_load((config_dir() / "decision_policy.yaml").read_text(encoding="utf-8"))


def product(code: str) -> dict:
    return policy()["products"][code]


def stop_factor(code: str) -> dict:
    return next(s for s in policy()["stop_factors"] if s["code"] == code)
