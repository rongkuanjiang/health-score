"""Preliminary hs-CRP component, standard library only. See INFLAMMATION_V01_SPEC.md."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import json
import math
from pathlib import Path

_PARAMS = json.loads(Path(__file__).with_name('inflammation_v01_parameters.json').read_text(encoding='utf-8'))
VERSION = _PARAMS['model_version']
_CRP = ('hs_crp', 'standard_crp', 'unknown_assay_crp')
_COUNTS = ('wbc', 'absolute_neutrophils', 'absolute_lymphocytes', 'other_differential_counts')
_MARKERS = ('hs_crp', *_PARAMS['context_only'])


def _finite(value, zero=False):
    try:
        return type(value) in (int, float) and math.isfinite(value) and (value >= 0 if zero else value > 0)
    except OverflowError:
        return False


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {k: _safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe(v) for v in value]
    return value


def _notice(target, code, text):
    target['notices'].append({'code': code, 'text': text})


def display_score(value):
    return None if value is None else str(Decimal(str(value)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))


def _curve(value):
    """Only call for validated exact concentrations in (0, 10]."""
    anchors = _PARAMS['hs_crp']['anchors']
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if value <= x1:
            return y0 + (value-x0)/(x1-x0)*(y1-y0)
    raise ValueError('Concentration outside the scoring curve')


def _parse_date(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError('Expected YYYY-MM-DD')
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('Expected YYYY-MM-DD')
    return parsed


def _observation(marker, raw, index, today):
    r = {'marker': marker, 'observation_id': None, 'observation': deepcopy(raw),
         'normalized_value': None, 'normalized_unit': None, 'qualifier': None,
         'specimen_age_days': None, 'errors': [], 'metadata_reasons': [], 'notices': [],
         'reference_status': 'unavailable', 'valid_measurement': False}
    if not isinstance(raw, dict):
        r['errors'].append('invalid_observation')
        return r
    r['observation_id'] = raw.get('observation_id', f'{marker}:{index}')
    if not _text(r['observation_id']):
        r['errors'].append('invalid_observation_id')
    q = raw.get('qualifier', '=')
    r['qualifier'] = q
    if q not in _PARAMS['hs_crp']['supported_qualifiers']:
        r['errors'].append('unsupported_qualifier')
    value, unit = raw.get('value'), raw.get('unit')
    zero_allowed = marker not in _CRP and q == '='
    if not _finite(value, zero=zero_allowed):
        r['errors'].append('invalid_value')
    if marker in _CRP:
        multipliers, canonical = _PARAMS['hs_crp']['unit_multipliers'], 'mg/L'
    elif marker in _COUNTS:
        multipliers, canonical = _PARAMS['cbc_absolute_count_unit_multipliers_to_10e9_l'], '10^9/L'
        if marker != 'wbc' and unit == '%':
            multipliers, canonical = {'%': 1}, '%'
    else:
        multipliers, canonical = {'mm/h': 1}, 'mm/h'
    factor = multipliers.get(unit) if isinstance(unit, str) else None
    if factor is None:
        r['errors'].append('unsupported_unit')
    if not r['errors']:
        try:
            normalized = value * factor
        except OverflowError:
            normalized = float('inf')
        if not _finite(normalized, zero=zero_allowed) or (canonical == '%' and normalized > 100):
            r['errors'].append('invalid_normalized_value')
        else:
            r.update(normalized_value=normalized, normalized_unit=canonical, valid_measurement=True)
    reliability = raw.get('reliability', 'unknown')
    if reliability in ('unreliable', 'invalid'):
        r['metadata_reasons'].append('unreliable_result')
    elif reliability == 'unknown':
        _notice(r, 'reliability_unknown', 'Laboratory reliability has not been confirmed.')
    elif reliability != 'valid':
        r['metadata_reasons'].append('invalid_reliability')
    if raw.get('lab_flag') is not None:
        _notice(r, 'laboratory_flag', deepcopy(raw['lab_flag']))
    if not _text(raw.get('report_id')):
        r['metadata_reasons'].append('report_id_required')
    if raw.get('specimen_date') is None:
        r['metadata_reasons'].append('specimen_date_required')
    else:
        try:
            parsed = _parse_date(raw['specimen_date'])
            if parsed > today:
                raise ValueError('Future specimen')
            r['specimen_age_days'] = (today-parsed).days
        except (ValueError, TypeError):
            r['metadata_reasons'].append('invalid_specimen_date')
    # Limits are in the original observation unit, never silently reinterpreted.
    lower, upper = raw.get('lower_limit'), raw.get('upper_limit')
    applicable = (raw.get('reference_range_applicable') is True and
                  raw.get('reference_unit', unit) == unit and _finite(lower, zero=True)
                  and _finite(upper) and lower < upper)
    if applicable and r['valid_measurement'] and q == '=':
        r['reference_status'] = 'low' if value < lower else 'high' if value > upper else 'within_range'
        if r['reference_status'] != 'within_range':
            _notice(r, 'outside_reference_range', f'Result is {r["reference_status"]} relative to the supplied applicable laboratory range.')
    elif marker not in _CRP:
        _notice(r, 'reference_interpretation_unavailable', 'An applicable exact-result laboratory reference comparison is unavailable.')
    if canonical == '%':
        _notice(r, 'percentage_not_absolute_count', 'This is a differential percentage, not an absolute cell count.')
    if marker in _CRP and r['valid_measurement']:
        _threshold_notices(r, marker == 'hs_crp' and _assay_supported(raw))
    return r


def _assay_supported(raw):
    return raw.get('assay_type') == 'hs_crp' or (
        raw.get('assay_type') == 'research_equivalent_hs_crp' and
        raw.get('assay_equivalence_verified') is True and
        _text(raw.get('assay_equivalence_provenance')))


def _threshold_notices(r, high_sensitivity):
    x, q = r['normalized_value'], r['qualifier']
    maximum = _PARAMS['hs_crp']['maximum_scored_mg_l_inclusive']
    above = (q in ('=', '>=') and x > maximum) or (q == '>' and x >= maximum)
    if above:
        _notice(r, 'crp_above_10', 'CRP is above 10 mg/L. Clinical interpretation is needed; this does not establish the cause.')
    threshold = _PARAMS['hs_crp']['risk_enhancer_notice_mg_l_inclusive']
    if high_sensitivity:
        if q in ('=', '>', '>=') and x >= threshold:
            _notice(r, 'hs_crp_risk_enhancer', 'hs-CRP is at least 2 mg/L, a cardiovascular risk-enhancing finding; this is not an individual risk estimate.')
        elif q != '=' and not ((q == '<' and x <= threshold) or (q == '<=' and x < threshold)):
            _notice(r, 'threshold_indeterminate_from_bound', 'The reported bound does not establish whether hs-CRP is at least 2 mg/L.')
    if q != '=' and not above and not (q in ('<', '<=') and x <= maximum):
        _notice(r, 'upper_threshold_indeterminate_from_bound', 'The bound does not establish whether CRP exceeds 10 mg/L.')


def score_inflammation(request, *, today=None):
    """Score a JSON-shaped request without mutation; malformed envelopes raise ValueError."""
    today = date.today() if today is None else today
    if type(today) is not date:
        raise ValueError('today must be a datetime.date')
    if not isinstance(request, dict):
        raise ValueError('request must be an object')
    for key in ('person', 'context', 'observations'):
        if not isinstance(request.get(key, {}), dict):
            raise ValueError(f'{key} must be an object')
    person, context = request.get('person', {}), request.get('context', {})
    observations = []
    for marker, raw in request.get('observations', {}).items():
        if marker not in _MARKERS:
            raise ValueError(f'Unsupported marker: {marker}')
        for index, item in enumerate(raw if isinstance(raw, list) else [raw]):
            observations.append(_observation(marker, item, index, today))
    candidates = [o for o in observations if o['marker'] == 'hs_crp']
    c = {'score': None, 'display_score': None, 'status': 'unavailable', 'reasons': [],
         'notices': [], 'observation_id': None}
    chosen = None
    ids = [o['observation_id'] for o in observations if _text(o['observation_id'])]
    duplicate_ids = len(ids) != len(set(ids))
    # Measurement errors first; never drop a malformed competing hs-CRP record.
    selector = request.get('selected_hs_crp_id')
    if selector is not None:
        matches = [o for o in candidates if o['observation_id'] == selector] if _text(selector) else []
        if len(matches) == 1 and not duplicate_ids:
            chosen = matches[0]
        else:
            c['reasons'].append('selection_required')
    elif len(candidates) == 1 and not duplicate_ids:
        chosen = candidates[0]
    elif candidates:
        c['reasons'].append('selection_required')
    else:
        c['reasons'].append('missing_hs_crp')
    if duplicate_ids:
        c['reasons'].insert(0, 'duplicate_observation_id')
    if chosen:
        c['observation_id'] = chosen['observation_id']
        c['reasons'] = chosen['errors'] + c['reasons']
        c['notices'].extend(deepcopy(chosen['notices']))
    age = person.get('age')
    if not _finite(age):
        c['reasons'].append('invalid_age')
    elif age < _PARAMS['minimum_point_age']:
        c['reasons'].append('pediatric_points_not_defined')
    elif age >= _PARAMS['older_age_notice_threshold']:
        _notice(c, 'older_age_limited_evidence', 'Exact-age evidence is limited at age 85 and above.')
    pregnancy = person.get('pregnancy_status', 'unknown')
    if pregnancy not in _PARAMS['eligible_pregnancy_statuses']:
        c['reasons'].append('pregnancy_outside_scope' if pregnancy == 'pregnant' else 'pregnancy_eligibility_unknown')
    if chosen:
        raw = chosen['observation']
        if not isinstance(raw, dict) or not _assay_supported(raw):
            c['reasons'].append('unsupported_or_unknown_assay')
        c['reasons'].extend(chosen['metadata_reasons'])
    acute = context.get('acute_context', 'unknown')
    if acute != _PARAMS['required_acute_context']:
        c['reasons'].append('acute_context_present' if acute == 'present' else 'acute_context_unknown')
    for field in ('chronic_inflammatory_condition', 'inflammation_affecting_treatment'):
        state = context.get(field, 'unknown')
        if state not in ('present', 'absent', 'unknown'):
            c['reasons'].append('invalid_' + field)
        if state != 'absent':
            _notice(c, field + ('_present' if state == 'present' else '_unknown'),
                    f'{field.replace("_", " ").capitalize()} is {state}; interpretation is limited and points are not adjusted.')
    value, result_status = None, 'scored'
    if chosen and chosen['valid_measurement']:
        x, q = chosen['normalized_value'], chosen['qualifier']
        maximum = _PARAMS['hs_crp']['maximum_scored_mg_l_inclusive']
        if (q in ('=', '>=') and x > maximum) or (q == '>' and x >= maximum):
            c['reasons'].append('above_scoring_range')
        elif q == '=':
            value = _curve(x)
        elif q in ('<', '<=') and x <= _PARAMS['hs_crp']['anchors'][1][0]:
            value, result_status = 100.0, 'scored_from_bound'
        else:
            c['reasons'].append('bounded_result')
    _notice(c, 'single_measurement_not_persistent_inflammation', 'One selected measurement cannot establish persistent inflammation.')
    c['reasons'] = list(dict.fromkeys(c['reasons']))
    if not c['reasons'] and value is not None:
        c.update(score=value, display_score=display_score(value), status=result_status)
    available = c['score'] is not None
    result = {
        'model_version': VERSION, 'domain_label': _PARAMS['domain_label'],
        'evaluation_date': today.isoformat(), 'input': deepcopy(request),
        'domain_score': None, 'domain_aggregation_status': _PARAMS['domain_aggregation_status'],
        'status': 'component_available' if available else 'context_only' if any(o['valid_measurement'] for o in observations) else 'unavailable',
        'components': {'hs_crp': c}, 'observations': observations,
        'coverage': {'hs_crp_present': bool(candidates), 'hs_crp_usable': available,
                     'missing_requirements': list(c['reasons']),
                     'context_markers_present': list(dict.fromkeys(o['marker'] for o in observations if o['marker'] != 'hs_crp'))},
        'notices': [{'code': 'limited_marker_coverage', 'text': 'This component does not measure all inflammation or immune function.'},
                    {'code': 'provisional_points', 'text': 'Experimental points are not clinically validated or a disease probability.'}],
    }
    return _safe(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('--today', type=_parse_date, help='Reproducible evaluation date (YYYY-MM-DD)')
    args = parser.parse_args()
    try:
        result = score_inflammation(json.loads(args.request.read_text(encoding='utf-8-sig')), today=args.today)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False, ensure_ascii=False))


if __name__ == '__main__':
    main()
