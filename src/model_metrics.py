"""Independent count checks, masked-basket validation and cluster diagnostics."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict

import numpy as np
import pandas as pd


def bitsets(transactions: list[set[str]]) -> dict[str, int]:
    result = defaultdict(int)
    for row, items in enumerate(transactions):
        bit = 1 << row
        for item in items:
            result[item] |= bit
    return dict(result)


def item_count(items, index: dict[str, int]) -> int:
    values = [index.get(item, 0) for item in items]
    if not values:
        raise ValueError("An itemset must not be empty.")
    result = values[0]
    for value in values[1:]:
        result &= value
    return result.bit_count()


def decode_rules(frame: pd.DataFrame, transactions: list[set[str]]) -> pd.DataFrame:
    result = frame.copy()
    n = len(transactions)
    index = bitsets(transactions)
    result["A"] = result["antecedent"].map(lambda value: tuple(str(value).split("|")))
    result["B"] = result["consequent"].map(lambda value: tuple(str(value).split("|")))
    result["max_len"] = result["A"].map(len) + result["B"].map(len)
    for row in result.itertuples(index=False):
        expected = (item_count(row.A, index), item_count(row.B, index), item_count(row.A + row.B, index), n)
        if expected != (row.count_a, row.count_b, row.count_ab, row.n_transactions):
            raise AssertionError(f"Independent rule counts differ for {row.antecedent} -> {row.consequent}: {expected}")
    result["support"] = result["count_ab"] / n
    result["confidence"] = result["count_ab"] / result["count_a"]
    result["lift"] = result["confidence"] / (result["count_b"] / n)
    return result


def evaluate_rule_stability(rules: pd.DataFrame, transactions: list[set[str]], prefix="validation") -> pd.DataFrame:
    result = rules.copy()
    index = bitsets(transactions)
    for key, source in [("count_a", "A"), ("count_b", "B")]:
        result[f"{prefix}_{key}"] = result[source].map(lambda items: item_count(items, index))
    result[f"{prefix}_count_ab"] = [item_count(a + b, index) for a, b in zip(result["A"], result["B"])]
    result[f"{prefix}_support"] = result[f"{prefix}_count_ab"] / len(transactions)
    result[f"{prefix}_confidence"] = result[f"{prefix}_count_ab"] / result[f"{prefix}_count_a"].replace(0, np.nan)
    result[f"{prefix}_lift"] = result[f"{prefix}_confidence"] / (result[f"{prefix}_count_b"].replace(0, np.nan) / len(transactions))
    return result


def masked_cases(invoice_ids, transactions, seed=42):
    cases = []
    for invoice, items in zip(invoice_ids, transactions):
        ordered = sorted(items)
        if len(ordered) < 2:
            continue
        position = int.from_bytes(hashlib.sha256(f"{seed}:{invoice}".encode()).digest()[:8], "big") % len(ordered)
        target = ordered[position]
        cases.append((str(invoice), set(ordered) - {target}, target))
    return cases


def popularity(transactions):
    counts = Counter(item for items in transactions for item in items)
    return sorted(counts, key=lambda item: (-counts[item], item))


def recommend(observed, rules_by_anchor, popular_items, k=5):
    scores = {}
    for anchor in observed:
        for antecedent, consequent, score in rules_by_anchor.get(anchor, []):
            if consequent not in observed and antecedent.issubset(observed):
                scores[consequent] = max(scores.get(consequent, (-1, -1, -1)), score)
    ranked = sorted(scores, key=lambda item: (-scores[item][0], -scores[item][1], -scores[item][2], item))[:k]
    used_rule = bool(ranked)
    for item in popular_items:
        if len(ranked) == k:
            break
        if item not in observed and item not in ranked:
            ranked.append(item)
    return ranked, used_rule


def rule_index(rules):
    index = defaultdict(list)
    for row in rules.itertuples(index=False):
        if len(row.B) != 1:
            continue
        index[min(row.A)].append((frozenset(row.A), row.B[0], (float(row.confidence), float(row.lift), int(row.count_ab))))
    return index


def completion_metrics(cases, rules, popular_items, k=5):
    index = rule_index(rules)
    hits = covered = recommendations = 0
    for _, observed, target in cases:
        ranked, used_rule = recommend(observed, index, popular_items, k)
        hits += target in ranked
        covered += used_rule
        recommendations += len(ranked)
    n = len(cases)
    return {"eligible_baskets": n, "hits": hits, "hit_rate_at_5": hits / n if n else np.nan,
            "rule_coverage": covered / n if n else np.nan, "baskets_with_rule_recommendation": covered,
            "returned_recommendations": recommendations}


def pairwise_distances(values):
    squared = np.sum(values * values, axis=1)
    distances = squared[:, None] + squared[None, :] - 2 * values @ values.T
    np.maximum(distances, 0, out=distances)
    np.sqrt(distances, out=distances)
    np.fill_diagonal(distances, 0)
    return distances


def silhouette(distances, labels):
    unique = np.unique(labels)
    if not 2 <= len(unique) < len(labels):
        raise ValueError("Silhouette requires between two and n-1 clusters.")
    means = np.column_stack([distances[:, labels == value].mean(axis=1) for value in unique])
    scores = np.zeros(len(labels))
    for position, value in enumerate(unique):
        mask = labels == value
        size = int(mask.sum())
        if size == 1:
            continue
        a = means[mask, position] * size / (size - 1)
        b = np.min(np.delete(means[mask], position, axis=1), axis=1)
        denominator = np.maximum(a, b)
        scores[mask] = np.divide(b-a, denominator, out=np.zeros_like(a), where=denominator > 0)
    return float(scores.mean())


def adjusted_rand(labels_a, labels_b):
    _, a = np.unique(labels_a, return_inverse=True)
    _, b = np.unique(labels_b, return_inverse=True)
    contingency = np.zeros((a.max()+1, b.max()+1), dtype=np.int64)
    np.add.at(contingency, (a, b), 1)
    choose2 = lambda values: np.sum(values * (values-1) / 2)
    total = len(a) * (len(a)-1) / 2
    observed = choose2(contingency)
    left = choose2(contingency.sum(axis=1)); right = choose2(contingency.sum(axis=0))
    expected = left * right / total
    denominator = (left + right) / 2 - expected
    return 1.0 if denominator == 0 else float((observed-expected)/denominator)
