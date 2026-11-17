"""Protect edited English documentation for the frozen final study."""
from __future__ import annotations
import json,re,sys
from pathlib import Path


def retain_frozen_english_reports(root, documents):
    """After final freeze, verify provenance and retain the edited reports.

    Earlier stage builders predate the English documentation edit. They must
    not overwrite the final English reports with their historical draft text.
    Missing reports must be restored from the submitted/versioned documents,
    rather than silently replaced with an earlier-language draft.
    """
    root=Path(root)
    lock_path=root/'results/models/final_evaluation_lock.json'
    if not lock_path.exists():
        return False
    sys.path.insert(0,str(root))
    from src.final_evaluation import digest,verify_records
    lock=json.loads(lock_path.read_text(encoding='utf-8'))
    verify_records(root,lock['files'])
    receipt_path=root/'results/tables/final_test/evaluation_receipt.json'
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    if digest(lock_path)!=receipt['freeze_lock_sha256']:
        raise RuntimeError('The final freeze lock differs from its evaluation receipt.')
    verify_records(root,receipt['files'])
    vietnamese=re.compile('[\u0102\u0103\u0110\u0111\u0128\u0129\u0168\u0169\u01a0\u01a1\u01af\u01b0\u1ea0-\u1ef9]')
    for name in documents:
        path=root/name
        if not path.is_file():
            raise RuntimeError(f'Restore the maintained English report before running this stage: {name}')
        content=path.read_text(encoding='utf-8')
        if vietnamese.search(content) or '\ufffd' in content:
            raise RuntimeError(f'Expected intact English final documentation: {name}')
    print(json.dumps({'english_reports_retained':list(documents),
                      'frozen_sources_and_results_verified':True,'final_test_rescored':False}))
    return True
