"""Fixed-model holdout metrics and paired customer-cluster uncertainty."""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from src.model_metrics import recommend


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_records(root, records):
    for record in records:
        path = Path(root) / record['path']
        if not path.is_file() or digest(path) != record['sha256']:
            raise RuntimeError(f"Frozen artifact changed or missing: {record['path']}")


def score_cases(cases, metadata, indexes, popular_items, method, cohort, k=5, train_vocabulary=None):
    records = []
    vocabulary = set(popular_items) if train_vocabulary is None else set(train_vocabulary)
    candidates = set(popular_items)
    for invoice, observed, target in cases:
        customer, segment = metadata[invoice]
        index = indexes[segment] if method == 'segment_rules' else indexes
        ranked, used_rule = recommend(observed, index, popular_items, k)
        assert len(ranked) == len(set(ranked)) and not set(ranked) & observed
        records.append({
            'cohort': cohort, 'method': method, 'InvoiceNo': invoice,
            'CustomerID': customer, 'Segment': segment,
            'bootstrap_unit': f'customer:{customer}' if customer else f'guest_invoice:{invoice}',
            'target': target, 'target_unseen_in_train': target not in vocabulary,
            'target_outside_candidate_items': target not in candidates,
            'observed_products': len(observed), 'recommendations': '|'.join(ranked),
            'returned_count': len(ranked), 'hit': int(target in ranked),
            'used_rule': int(used_rule),
        })
    return pd.DataFrame(records)


def summarize(frame, k=5):
    n = len(frame)
    if not n:
        raise ValueError('No eligible baskets in this cohort.')
    hits = int(frame['hit'].sum())
    return {'eligible_baskets': n, 'hits': hits,
            'hit_rate_at_5': hits/n, 'recall_at_5': hits/n,
            'precision_at_5_fixed_denominator': hits/(n*k),
            'rule_coverage': float(frame['used_rule'].mean()),
            'zero_rule_fallback_rate': float(1-frame['used_rule'].mean()),
            'short_recommendation_rate': float(frame['returned_count'].lt(k).mean()),
            'returned_recommendations': int(frame['returned_count'].sum()),
            'hidden_targets_outside_train_vocabulary': int(frame['target_unseen_in_train'].sum()),
            'bootstrap_units': frame['bootstrap_unit'].nunique()}


def bootstrap_hit_rates(frame, method_names, repeats=2000, seed=20261118):
    """Resample the same customer units for all methods; retain basket weights."""
    names = list(method_names)
    subset = frame.loc[frame['method'].isin(names)]
    if subset.duplicated(['InvoiceNo', 'method']).any():
        raise ValueError('Duplicate invoice/method predictions.')
    hits = subset.pivot(index=['InvoiceNo', 'bootstrap_unit'], columns='method', values='hit')
    if hits[names].isna().any().any():
        raise ValueError('Paired comparisons require identical invoice cohorts.')
    grouped = hits[names].groupby(level='bootstrap_unit').sum()
    counts = hits.groupby(level='bootstrap_unit').size().reindex(grouped.index).to_numpy()
    values = grouped.to_numpy()
    rng = np.random.default_rng(seed)
    samples = np.empty((repeats, len(names)))
    for i in range(repeats):
        draw = rng.integers(0, len(grouped), size=len(grouped))
        samples[i] = values[draw].sum(axis=0)/counts[draw].sum()
    return names, samples
