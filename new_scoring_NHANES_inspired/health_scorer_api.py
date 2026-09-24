"""Versioned, dependency-free integration boundary; domain rules remain unchanged."""
from copy import deepcopy
from datetime import date
import argparse
import json
from pathlib import Path

from metabolism_score import score_metabolism, VERSION as METABOLISM_VERSION
from liver_kidney_score import score_liver_kidney, VERSION as ORGAN_VERSION
from inflammation_score import score_inflammation, VERSION as INFLAMMATION_VERSION
from nutrition_score import score_nutrition, VERSION as NUTRITION_VERSION
from system_stability_score import score_system_stability, VERSION as STABILITY_VERSION

API_VERSION = '1.0'
PACKAGE_VERSION = '0.1.2'
SCORERS = {
    'metabolism': (score_metabolism, METABOLISM_VERSION),
    'organ-stress': (score_liver_kidney, ORGAN_VERSION),
    'inflammation': (score_inflammation, INFLAMMATION_VERSION),
    'nutrition': (score_nutrition, NUTRITION_VERSION),
    'system-stability': (score_system_stability, STABILITY_VERSION),
}


class ContractError(ValueError):
    """Invalid shared request envelope, before any domain is evaluated."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError('Duplicate JSON keys are not supported.')
        result[key] = value
    return result


def loads_request(raw):
    def reject_constant(_):
        raise ContractError('Nonfinite JSON numbers are not supported.')
    return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=reject_constant)


def metadata():
    return {'api_version': API_VERSION, 'package_version': PACKAGE_VERSION,
            'model_versions': {key: value[1] for key, value in SCORERS.items()},
            'model_status': 'preliminary_not_clinically_validated',
            'overall_score': None, 'overall_score_status': 'not_defined'}


def score_request(request):
    """Evaluate requested domains with one explicit date; preserve complete engine output.

    A domain's `processing_status=ok` means evaluation succeeded, NOT that points
    are available. Omitted domains are not evaluated. No cross-domain inference.
    """
    if not isinstance(request, dict) or set(request) != {'api_version', 'evaluation_date', 'domains'}:
        raise ContractError('Required fields: api_version, evaluation_date, domains; no extra fields.')
    if request['api_version'] != API_VERSION:
        raise ContractError('Unsupported api_version; expected 1.0.')
    try:
        stamp = request['evaluation_date']
        if not isinstance(stamp, str) or len(stamp) != 10:
            raise ValueError
        today = date.fromisoformat(stamp)
        if today.isoformat() != stamp:
            raise ValueError
    except ValueError:
        raise ContractError('evaluation_date must be YYYY-MM-DD.') from None
    domains = request['domains']
    if not isinstance(domains, dict) or not domains or set(domains) - SCORERS.keys():
        raise ContractError('domains must contain one or more supported domain IDs.')
    try:
        # Also rejects NaN/Infinity supplied directly by a Python caller, including 1e999 JSON.
        json.dumps(request, allow_nan=False)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ContractError('Request must contain finite JSON data.') from None
    results = {}
    for domain, raw in domains.items():
        scorer, version = SCORERS[domain]
        try:
            if not isinstance(raw, dict):
                raise ValueError
            if 'evaluation_date' in raw and raw['evaluation_date'] != stamp:
                raise ValueError
            result = scorer(deepcopy(raw), today=today)
            json.dumps(result, allow_nan=False)
            results[domain] = {'processing_status': 'ok', 'model_version': version, 'result': result}
        except (ValueError, TypeError, OverflowError, RecursionError):
            results[domain] = {'processing_status': 'error', 'model_version': version,
                               'error': {'code': 'invalid_domain_request',
                                         'message': 'Check this domain contract and any conflicting evaluation_date.'}}
    failures = sum(value['processing_status'] == 'error' for value in results.values())
    return {**metadata(), 'evaluation_date': stamp,
            'processing_status': 'ok' if failures == 0 else 'error' if failures == len(results) else 'partial',
            'domains': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('--output', type=Path, help='Explicitly save result (contains supplied health data).')
    args = parser.parse_args()
    try:
        result = score_request(loads_request(args.request.read_text(encoding='utf-8-sig')))
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        parser.exit(2, 'Invalid shared scoring request. See INTEGRATION_HANDOFF.md.\n')
    encoded = json.dumps(result, indent=2, allow_nan=False, ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(encoded, encoding='utf-8')
    else:
        print(encoded)
    return 0 if result['processing_status'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
