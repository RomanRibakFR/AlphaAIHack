"""
Временная калибровка модели PD, пока нет модели Ильи (задача 2).

13 тестовых компаний — мало для честной регрессии, а деление на классы A/B в допущениях
не монотонно по признакам. Поэтому веса экспертные (PRIOR: знак и относительная сила признака),
а по данным подбираем только общий масштаб и сдвиг: PD должен быть близок к assumed_pd,
и главное — компания должна попасть в свой маршрут (A/B — автоматом, C — к специалисту, D — отказ).
Расхождение A/B меняет только ставку.

Запуск из backend/:  python scripts/calibrate_pd.py   -> пишет config/pd_model.yaml
"""
import json
import math
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.features import features  # noqa: E402
from app.pd_model import TRANSFORMS  # noqa: E402
from app.policy import config_dir, policy  # noqa: E402

AS_OF = date(2026, 10, 24)
# экспертные веса на стандартизованных признаках: знак и относительная сила влияния
PRIOR = {"age": -0.35, "turnover": -0.15, "turnover_cv": 0.35, "debt_load": 0.25,
         "overdue_count": 0.3, "overdue_max_months": 0.25, "amount_to_turnover": 0.15}
ROUTE_WEIGHT = 100  # штраф за промах мимо маршрута
MARGIN = 0.15  # запас от границы маршрута в logit


def companies_dir() -> Path:
    for p in (Path("/app/mocks_companies"), Path(__file__).resolve().parents[2] / "mocks" / "companies"):
        if p.exists():
            return p
    raise FileNotFoundError("нет mocks/companies")


def logit(p):
    return math.log(p / (1 - p))


def fit(rows, targets, bands, names):
    """Перебор масштаба s и сдвига b: z = b + s·Σ PRIOR·x_std. Ошибка logit + штраф за маршрут."""
    mean = {k: sum(r[k] for r in rows) / len(rows) for k in names}
    std = {k: (sum((r[k] - mean[k]) ** 2 for r in rows) / len(rows)) ** 0.5 or 1 for k in names}
    base = [sum(PRIOR[k] * (r[k] - mean[k]) / std[k] for k in names) for r in rows]

    def loss(s, b):
        total = 0.0
        for u, y, (lo, hi) in zip(base, targets, bands):
            z = b + s * u
            total += (z - y) ** 2
            if z < lo + MARGIN:
                total += ROUTE_WEIGHT * (z - lo - MARGIN) ** 2
            elif z > hi - MARGIN:
                total += ROUTE_WEIGHT * (z - hi + MARGIN) ** 2
        return total

    grid = ((s / 20, b / 100) for s in range(1, 200) for b in range(-700, 0))
    s, b = min(grid, key=lambda sb: loss(*sb))
    coef = {k: s * PRIOR[k] / std[k] for k in names}
    intercept = b - sum(coef[k] * mean[k] for k in names)
    return intercept, coef


def main():
    grades = policy()["risk_grades"]
    route_of = {g["grade"]: g["route"] for g in grades}
    # границы маршрута в logit: класс A и B — один маршрут auto
    bounds, lo = {}, 1e-6
    for g in grades:
        bounds.setdefault(g["route"], [logit(lo), None])[1] = logit(min(g["pd_max"], 1 - 1e-6))
        lo = g["pd_max"]
    bounds = {grade: tuple(bounds[route]) for grade, route in route_of.items()}

    rows, targets, bands, ids = [], [], [], []
    for file in sorted(companies_dir().glob("*.json")):
        d = json.loads(file.read_text(encoding="utf-8"))
        pd = d["meta"]["expected"]["assumed_pd"]
        if pd is None:
            continue
        f = features(d["egrul"], d["bki"], d["bank"], d["meta"]["scenario"]["amount"], AS_OF)
        rows.append({k: fn(f) for k, fn in TRANSFORMS.items()})
        targets.append(logit(pd))
        bands.append(bounds[d["meta"]["expected"]["assumed_grade"]])
        ids.append((d["meta"]["id"], pd, d["meta"]["expected"]["assumed_grade"]))

    intercept, coef = fit(rows, targets, bands, list(TRANSFORMS))

    def grade(pd):
        return next(g["grade"] for g in grades if pd < g["pd_max"] or g["grade"] == "D")

    ok = True
    for (cid, target, exp_grade), r in zip(ids, rows):
        z = intercept + sum(coef[k] * r[k] for k in TRANSFORMS)
        pd = 1 / (1 + math.exp(-z))
        mark = "✓" if route_of[grade(pd)] == route_of[exp_grade] else "✗"
        ok &= mark == "✓"
        print(f"{mark} {cid}: PD {pd:.3f} (ожидали {target:.2f}), класс {grade(pd)} / {exp_grade}, "
              f"маршрут {route_of[grade(pd)]}")

    means = {k: round(sum(r[k] for r in rows) / len(rows), 4) for k in TRANSFORMS}
    out = {
        "version": "placeholder-0.1",
        "note": "Временная калибровка под assumed_pd тестовых компаний (scripts/calibrate_pd.py). "
                "Заменить коэффициентами модели задачи 2.",
        "intercept": round(intercept, 4),
        "coefficients": {k: round(v, 4) for k, v in coef.items()},
        "means": means,
    }
    path = config_dir() / "pd_model.yaml"
    path.write_text("# Модель PD: логистическая регрессия на F1–F6 (см. backend/app/pd_model.py)\n"
                    + yaml.safe_dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"\nзаписал {path}; все маршруты совпали: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
