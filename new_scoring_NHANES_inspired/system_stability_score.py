"""System Stability reference summary. Standard library only; no numerical score."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
import math
from pathlib import Path

_PARAMS = json.loads(Path(__file__).with_name('system_stability_v01_parameters.json').read_text(encoding='utf-8'))
VERSION = _PARAMS['model_version']
CORE = tuple(_PARAMS['core_markers'])
CONTEXT = tuple(_PARAMS['context_markers'])
_CATEGORIES = ('low', 'within_reference', 'high')
_CRITICAL = ('critical', 'critical_low', 'critical_high')
_DIRECTIONS = {'low': 'low', 'high': 'high', 'within_reference': 'within_reference',
               'critical_low': 'low', 'critical_high': 'high'}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _positive(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        return False


def _safe(value):
    """Retain rejected nonfinite numbers as text in JSON-safe provenance."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {k: _safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe(v) for v in value]
    return value


def _json_shape(value):
    if value is None or type(value) in (str, int, float, bool):
        return
    if isinstance(value, list):
        for item in value:
            _json_shape(item)
        return
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        for item in value.values():
            _json_shape(item)
        return
    raise ValueError('Request must contain JSON-shaped values and string object keys')


def _date(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError('Expected YYYY-MM-DD')
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('Expected YYYY-MM-DD')
    return parsed


def _append(items, code):
    if code not in items:
        items.append(code)


def _classify(value, lower, upper, qualifier):
    if qualifier == '=':
        return 'low' if value < lower else 'high' if value > upper else 'within_reference'
    if (qualifier == '<' and value <= lower) or (qualifier == '<=' and value < lower):
        return 'low'
    if (qualifier == '>' and value >= upper) or (qualifier == '>=' and value > upper):
        return 'high'
    return 'indeterminate_bound'


def _observation(marker, raw, selected, blockers, today):
    result = {'marker': marker, 'observation_id': None, 'selected': selected,
              'observation': deepcopy(raw), 'score': None, 'normalized_value': None,
              'normalized_unit': None, 'normalized_lower_limit': None,
              'normalized_upper_limit': None, 'qualifier': None,
              'specimen_age_days': None, 'reference_status': 'unavailable',
              'classification_basis': 'unavailable', 'source_flags': [],
              'errors': [], 'reasons': list(blockers), 'notices': []}
    if not isinstance(raw, dict):
        result['errors'].append('invalid_observation')
        return result
    result['observation_id'] = raw.get('observation_id')
    if not _text(result['observation_id']):
        result['errors'].append('invalid_observation_id')
    flags = raw.get('source_flags', [])
    if not isinstance(flags, list):
        result['errors'].append('invalid_source_flags')
        # Even a malformed scalar critical flag must remain visible.
        flags = [flags]
    result['source_flags'] = deepcopy(flags)
    for flag in flags:
        if flag not in _PARAMS['recognized_source_flags']:
            _append(result['notices'], 'unmapped_source_flag')
        else:
            _append(result['notices'], 'laboratory_flag')
    if any(flag in _CRITICAL for flag in flags):
        _append(result['notices'], 'source_critical_flag')

    value, unit, qualifier = raw.get('value'), raw.get('unit'), raw.get('qualifier', '=')
    result['qualifier'] = qualifier
    if not _positive(value):
        result['errors'].append('invalid_value')
    if qualifier not in _PARAMS['supported_qualifiers']:
        result['errors'].append('unsupported_qualifier')
    units = _PARAMS['core_unit_multipliers'] if marker in CORE else _PARAMS['calcium_unit_multipliers']
    factor = units.get(unit) if isinstance(unit, str) else None
    if factor is None:
        result['errors'].append('unsupported_unit')
    normalized = None
    if _positive(value) and factor is not None:
        normalized = Decimal(str(value)) * Decimal(str(factor))
        if not _positive(float(normalized)):
            result['errors'].append('invalid_normalized_value')
        else:
            result['normalized_value'] = float(normalized)
            result['normalized_unit'] = _PARAMS['canonical_unit']

    lower, upper = raw.get('lower_limit'), raw.get('upper_limit')
    reference_unit = raw.get('reference_unit')
    reference_factor = units.get(reference_unit) if isinstance(reference_unit, str) else None
    reference = None
    if not (_positive(lower) and _positive(upper) and lower < upper):
        result['reasons'].append('invalid_reference_limits')
    elif reference_factor is None:
        result['reasons'].append('unsupported_reference_unit')
    else:
        reference = (Decimal(str(lower)) * Decimal(str(reference_factor)),
                     Decimal(str(upper)) * Decimal(str(reference_factor)))
        if not all(_positive(float(x)) for x in reference):
            result['reasons'].append('invalid_normalized_reference')
        else:
            result['normalized_lower_limit'], result['normalized_upper_limit'] = map(float, reference)
    if raw.get('reference_applicability') != 'confirmed':
        result['reasons'].append('reference_applicability_unconfirmed')
    if not _text(raw.get('reference_provenance')):
        result['reasons'].append('reference_provenance_required')
    if raw.get('reference_marker', marker) != marker:
        result['reasons'].append('reference_analyte_mismatch')
    if not _text(raw.get('report_id')):
        result['reasons'].append('report_id_required')
    try:
        collection = _date(raw.get('specimen_date'))
        if collection > today:
            result['reasons'].append('future_specimen_date')
        else:
            result['specimen_age_days'] = (today - collection).days
    except ValueError:
        result['reasons'].append('invalid_specimen_date')
    allowed_specimens = ('serum', 'plasma', 'whole_blood') if marker == 'ionized_calcium' else ('serum', 'plasma')
    if raw.get('specimen_type') not in allowed_specimens:
        result['reasons'].append('unsupported_or_unknown_specimen')
    if marker == 'total_co2':
        assay = raw.get('assay_type')
        if assay != 'chemistry_total_co2' and not (
                assay == 'chemistry_bicarbonate' and raw.get('chemistry_alias_verified') is True):
            result['reasons'].append('chemistry_co2_identity_required')
    reliability = raw.get('reliability', 'unknown')
    if reliability == 'unknown':
        result['notices'].append('reliability_unknown')
    elif reliability == 'unreliable':
        result['reasons'].append('unreliable_result')
    elif reliability != 'not_flagged':
        result['reasons'].append('invalid_reliability')
    interference = raw.get('interference_affects_result', False)
    if type(interference) is not bool:
        result['reasons'].append('invalid_interference_status')
    elif interference:
        _append(result['reasons'], 'unreliable_result')
        result['notices'].append('specimen_interference')

    if not result['errors'] and not result['reasons']:
        result['reference_status'] = _classify(normalized, *reference, qualifier)
        result['classification_basis'] = 'derived'
        if result['reference_status'] == 'indeterminate_bound':
            result['reasons'].append('indeterminate_bound')
    elif any(flag in _PARAMS['recognized_source_flags'] for flag in flags):
        result['classification_basis'] = 'source_only'
    directions = [flag for flag in flags if isinstance(flag, str) and flag in _DIRECTIONS]
    if (result['reference_status'] in _CATEGORIES and
            any(_DIRECTIONS[flag] != result['reference_status'] for flag in directions)):
        result['notices'].append('source_flag_conflict')
    # Contradictory source flags also prevent a reassuring summary without a derived category.
    if len({_DIRECTIONS[flag] for flag in directions}) > 1:
        _append(result['notices'], 'source_flag_conflict')
    if result['reference_status'] in ('low', 'high') or any(flag in ('low', 'high') for flag in flags):
        result['notices'].append('outside_reference')
    return result


def score_system_stability(request, *, today=None):
    """Return a reference summary for explicitly selected observations.

    `today` is a date; defaults to host date. Invalid envelope shapes raise
    ValueError. Malformed observations and selection metadata return reasons.
    All numerical score fields are None by design. See ENGINE_README.
    """
    _json_shape(request)
    if not isinstance(request, dict):
        raise ValueError('Request must be an object')
    observations = request.get('observations', {})
    selection = request.get('selection', {})
    if not isinstance(observations, dict) or not isinstance(selection, dict):
        raise ValueError('observations and selection must be objects')
    chosen = selection.get('observation_ids', {})
    if not isinstance(chosen, dict):
        raise ValueError('selection.observation_ids must be an object')
    today = date.today() if today is None else today
    if type(today) is not date:
        raise ValueError('today must be a datetime.date')

    flat = [(marker, raw) for marker, values in observations.items()
            for raw in (values if isinstance(values, list) else [values])]
    selection_reasons = []
    if not _text(selection.get('report_id')):
        selection_reasons.append('selected_report_required')
    try:
        if _date(selection.get('specimen_date')) > today:
            selection_reasons.append('invalid_selected_specimen_date')
    except ValueError:
        selection_reasons.append('invalid_selected_specimen_date')
    if selection.get('specimen_id') is not None and not _text(selection['specimen_id']):
        selection_reasons.append('invalid_selected_specimen_id')
    # A multi-specimen report requires a specimen ID, even on the same date.
    specimen_ids = {raw.get('specimen_id') for _, raw in flat if isinstance(raw, dict)
                    and raw.get('report_id') == selection.get('report_id') and _text(raw.get('specimen_id'))}
    if len(specimen_ids) > 1 and not _text(selection.get('specimen_id')):
        selection_reasons.append('specimen_selection_required')
    id_counts = {}
    for _, raw in flat:
        if isinstance(raw, dict) and _text(raw.get('observation_id')):
            key = raw['observation_id']
            id_counts[key] = id_counts.get(key, 0) + 1
    reasons = list(selection_reasons)
    for marker in chosen:
        if marker not in CORE + CONTEXT:
            _append(reasons, 'unsupported_selected_marker')
    records, unsupported = [], []
    for marker in CORE + CONTEXT:
        candidates = [raw for key, raw in flat if key == marker]
        selected_id = chosen.get(marker)
        if candidates and not _text(selected_id):
            _append(reasons, f'{marker}:observation_selection_required')
        if _text(selected_id) and not any(isinstance(raw, dict) and raw.get('observation_id') == selected_id for raw in candidates):
            _append(reasons, f'{marker}:selected_observation_not_found')
        for raw in candidates:
            selected = _text(selected_id) and isinstance(raw, dict) and raw.get('observation_id') == selected_id
            blockers = list(selection_reasons) if selected else ['observation_not_selected']
            if selected:
                if id_counts.get(selected_id, 0) != 1:
                    blockers.append('ambiguous_observation_id')
                if raw.get('report_id') != selection.get('report_id'):
                    blockers.append('selected_report_mismatch')
                if raw.get('specimen_date') != selection.get('specimen_date'):
                    blockers.append('selected_collection_mismatch')
                if _text(selection.get('specimen_id')) and raw.get('specimen_id') != selection['specimen_id']:
                    blockers.append('selected_specimen_mismatch')
            records.append(_observation(marker, raw, bool(selected), blockers, today))
    for marker, raw in flat:
        if marker not in CORE + CONTEXT:
            unsupported.append({'marker': marker, 'observation': deepcopy(raw), 'errors': ['unsupported_marker']})
            _append(reasons, 'unsupported_marker')

    core = [r for r in records if r['selected'] and r['marker'] in CORE]
    present = [marker for marker in CORE if any(r['marker'] == marker for r in core)]
    usable = [marker for marker in CORE if any(r['marker'] == marker and r['reference_status'] in _CATEGORIES for r in core)]
    flags = [flag for r in core for flag in r['source_flags']]
    notices = [code for r in core for code in r['notices']]
    if 'source_critical_flag' in notices:
        status = 'source_critical_flag'
    elif 'source_flag_conflict' in notices:
        status = 'source_flag_conflict'
    elif 'outside_reference' in notices:
        status = 'outside_reference'
    elif len(usable) == len(CORE) and 'unmapped_source_flag' not in notices:
        status = 'all_within_reference'
    elif usable or 'within_reference' in flags:
        status = 'partial'
    else:
        status = 'unavailable'
    domain_notices = [{'code': 'single_collection_not_temporal_stability', 'marker': None,
                       'observation_id': None, 'selected': None}]
    for r in records:
        for code in r['notices']:
            domain_notices.append({'code': code, 'marker': r['marker'],
                                   'observation_id': r['observation_id'], 'selected': r['selected']})
        if r['selected']:
            for code in r['errors'] + r['reasons']:
                _append(reasons, f"{r['marker']}:{code}")
    missing = [marker for marker in CORE if marker not in present]
    for marker in missing:
        _append(reasons, f'{marker}:missing_selected_observation')
    result = {'model_version': VERSION, 'domain_label': _PARAMS['domain_label'],
              'result_label': _PARAMS['result_label'], 'domain_score': None,
              'domain_aggregation_status': _PARAMS['domain_aggregation_status'],
              'panel_status': status, 'evaluation_date': today.isoformat(),
              'selection': deepcopy(selection), 'request': deepcopy(request),
              'coverage': {'present_count': len(present), 'interpretable_count': len(usable),
                           'expected_count': len(CORE), 'missing_markers': missing,
                           'uninterpretable_markers': [m for m in present if m not in usable]},
              'reasons': reasons, 'notices': domain_notices,
              'observations': [r for r in records if r['marker'] in CORE],
              'context_observations': [r for r in records if r['marker'] in CONTEXT],
              'unsupported_observations': unsupported}
    return _safe(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('--today', type=_date, default=None, help='Evaluation date YYYY-MM-DD')
    args = parser.parse_args()
    try:
        request = json.loads(args.request.read_text(encoding='utf-8-sig'))
        result = score_system_stability(request, today=args.today)
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Invalid request: {exc}\n')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
