"""Logica pura do agente de avaliacao. Sem BD - testavel isoladamente.

Recebe os itens da estratégia (como dicts/objetos simples) e os valores
observados dos indicadores; devolve scores, recomendacao e detalhes.
"""
from dataclasses import dataclass

BUY_THRESHOLD = 70.0
SELL_THRESHOLD = 70.0


@dataclass
class ItemResult:
    item_id: object
    observed_value: float | None
    passed: bool | None
    contribution: float


@dataclass
class EvaluationResult:
    buy_score: float
    sell_score: float
    recommendation: str
    details: list[ItemResult]


def apply_operator(value: float, operator: str, threshold: float | None,
                   threshold_max: float | None = None) -> bool:
    if operator == "<":
        return value < threshold
    if operator == ">":
        return value > threshold
    if operator == "<=":
        return value <= threshold
    if operator == ">=":
        return value >= threshold
    if operator == "==":
        return value == threshold
    if operator == "between":
        if threshold is None or threshold_max is None:
            raise ValueError("operador 'between' requer threshold_value e threshold_value_max")
        return threshold <= value <= threshold_max
    raise ValueError(f"operador desconhecido: {operator}")


def compute_evaluation(items: list[dict], observed: dict[str, float | None]) -> EvaluationResult:
    """items: [{id, metric, operator, threshold_value, threshold_value_max, weight, direction}]
    observed: {metric: valor | None}
    """
    details: list[ItemResult] = []
    sums = {"buy_signal": [0.0, 0.0], "sell_signal": [0.0, 0.0]}  # [contribution, weight avaliavel]

    for item in items:
        value = observed.get(item["metric"])
        weight = float(item["weight"])
        direction = item["direction"]
        if value is None:
            details.append(ItemResult(item.get("id"), None, None, 0.0))
            continue  # peso excluido do denominador
        passed = apply_operator(
            float(value), item["operator"],
            float(item["threshold_value"]) if item.get("threshold_value") is not None else None,
            float(item["threshold_value_max"]) if item.get("threshold_value_max") is not None else None,
        )
        contribution = weight if passed else 0.0
        sums[direction][0] += contribution
        sums[direction][1] += weight
        details.append(ItemResult(item.get("id"), float(value), passed, contribution))

    def score(direction: str) -> float:
        contrib, total = sums[direction]
        return round(100.0 * contrib / total, 2) if total > 0 else 0.0

    buy_score, sell_score = score("buy_signal"), score("sell_signal")
    if sell_score >= SELL_THRESHOLD:
        recommendation = "SELL"
    elif buy_score >= BUY_THRESHOLD:
        recommendation = "BUY"
    else:
        recommendation = "HOLD"
    return EvaluationResult(buy_score, sell_score, recommendation, details)
