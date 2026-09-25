"""Preliminary nutrition marker engine. Points are experimental, not clinical validation."""
import argparse
from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import json
import math
from pathlib import Path


_PARAMS = json.loads(Path(__file__).with_name('nutrition_v01_parameters.json').read_text(encoding='utf-8'))
VERSION = _PARAMS['model_version']
WEIGHTS = _PARAMS['weights']
CORE = {
    'b12': {'analyte': 'total_vitamin_b12', 'unit': 'pmol/L',
            'units': {'pmol/L': 1, 'pg/mL': 0.738, 'ng/L': 0.738},
            'anchors': [(0, 0), (150, 50), (220, 80), (300, 100)]},
    'ferritin': {'analyte': 'ferritin', 'unit': 'ug/L',
                 'units': {'ug/L': 1, 'µg/L': 1, 'μg/L': 1, 'ng/mL': 1},
                 'anchors': [(0, 0), (15, 40), (30, 75), (100, 100)]},
}
_D = _PARAMS['vitamin_d']
_MARKERS = ('vitamin_d', *WEIGHTS, *_PARAMS['context_only'])
_CONTEXT_FIELDS = ('vitamin_d_supplementation', 'vitamin_d_treatment', 'relevant_conditions')


def _finite(value, zero=False):
    try:
        return type(value) in (int, float) and math.isfinite(value) and (value >= 0 if zero else value > 0)
    except OverflowError:
        return False


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _safe(value):
    """Copy JSON-shaped data; preserve rejected nonfinite inputs as provenance strings."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise ValueError('JSON object keys must be strings')
        return {k: _safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe(v) for v in value]
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise ValueError('Request must contain only JSON-shaped values')


def _notice(target, code, text):
    target['notices'].append({'code': code, 'text': text})


def _parse_date(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError('Expected YYYY-MM-DD')
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('Expected YYYY-MM-DD')
    return parsed


def display_score(value):
    return None if value is None else str(Decimal(str(value)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))


def _curve(value):
    for (x0, y0), (x1, y1) in zip(_D['anchors'], _D['anchors'][1:]):
        if value <= x1:
            return y0 + (value - x0) / (x1 - x0) * (y1 - y0)
    raise ValueError('Outside scoring interval')


def _reference_notice(value, qualifier):
    """Bounds are over positive concentrations; an endpoint is never an exact result."""
    bands = _D['reference_bands']
    if qualifier == '=':
        for b in bands:
            lo, hi = b['minimum'], b['maximum']
            lower_ok = value >= lo if b['minimum_inclusive'] else value > lo
            upper_ok = hi is None or (value <= hi if b['maximum_inclusive'] else value < hi)
            if lower_ok and upper_ok:
                return b['notice']
    elif ((qualifier == '<' and value <= bands[0]['maximum']) or
          (qualifier == '<=' and value < bands[0]['maximum'])):
        return bands[0]['notice']
    elif ((qualifier == '>' and value >= bands[-1]['minimum']) or
          (qualifier == '>=' and value > bands[-1]['minimum'])):
        return bands[-1]['notice']
    return 'reference_band_indeterminate_from_bound'


_BAND_TEXT = {
    'below_reference_band': 'This vitamin D result is below the selected adult reference band; clinical interpretation is needed.',
    'possible_inadequacy_band': 'This vitamin D result falls in the selected possible-inadequacy band.',
    'reference_adequacy_band': 'This vitamin D result is in the selected reference adequacy band; it does not establish overall nutritional adequacy.',
    'above_scoring_range_review': 'This vitamin D result is above the prototype scoring range; clinical interpretation is needed.',
    'reference_band_indeterminate_from_bound': 'The reported bound spans reference bands; no single band can be assigned.',
}


def _observation(marker, raw, today, eligible_reference):
    o = {'marker': marker, 'observation_id': None, 'observation': deepcopy(raw),
         'normalized_value': None, 'normalized_unit': None, 'qualifier': None,
         'specimen_age_days': None, 'errors': [], 'metadata_reasons': [],
         'reliability_reasons': [], 'notices': [], 'reference_status': 'unavailable',
         'valid_measurement': False}
    if not isinstance(raw, dict):
        o['errors'].append('invalid_observation')
        return o
    o['observation_id'] = raw.get('observation_id')
    if not _text(o['observation_id']):
        o['metadata_reasons'].append('observation_id_required')
    value, unit, q = raw.get('value'), raw.get('unit'), raw.get('qualifier', '=')
    o['qualifier'] = q
    if not _finite(value, zero=marker != 'vitamin_d' and q == '='):
        o['errors'].append('invalid_value')
    if q not in _D['supported_qualifiers']:
        o['errors'].append('unsupported_qualifier')
    factor = _D['unit_multipliers'].get(unit) if isinstance(unit, str) else None
    if marker == 'vitamin_d':
        if raw.get('analyte') != _D['required_analyte']:
            o['metadata_reasons'].append('unsupported_analyte')
        if raw.get('specimen_type') not in _D['supported_specimen_types']:
            o['metadata_reasons'].append('unsupported_or_unknown_specimen_type')
        if factor is None:
            o['metadata_reasons'].append('unsupported_unit')
    elif not _text(unit):
        o['metadata_reasons'].append('unit_required')
    else:
        factor = 1
    if not o['errors'] and factor is not None:
        try:
            normalized = value * factor
        except OverflowError:
            normalized = float('inf')
        if not _finite(normalized, zero=marker != 'vitamin_d' and q == '='):
            o['errors'].append('invalid_normalized_value')
        else:
            o.update(normalized_value=normalized,
                     normalized_unit=_D['canonical_unit'] if marker == 'vitamin_d' else unit,
                     valid_measurement=True)
    if not _text(raw.get('report_id')):
        o['metadata_reasons'].append('report_id_required')
    if raw.get('specimen_date') is None:
        o['metadata_reasons'].append('specimen_date_required')
    else:
        try:
            collected = _parse_date(raw['specimen_date'])
            if today is not None:
                if collected > today:
                    o['metadata_reasons'].append('future_specimen_date')
                else:
                    o['specimen_age_days'] = (today - collected).days
        except ValueError:
            o['metadata_reasons'].append('invalid_specimen_date')
    reliability = raw.get('reliability', 'unknown')
    if reliability in ('unreliable', 'invalid'):
        o['reliability_reasons'].append('unreliable_result')
    elif reliability == 'unknown':
        _notice(o, 'reliability_unknown', 'Laboratory reliability has not been confirmed.')
    elif reliability != 'valid':
        o['reliability_reasons'].append('invalid_reliability')
    if raw.get('lab_flag') is not None:
        _notice(o, 'laboratory_flag', deepcopy(raw['lab_flag']))
    lower, upper = raw.get('lower_limit'), raw.get('upper_limit')
    applicable = (raw.get('reference_range_applicable') is True and _text(unit) and
                  raw.get('reference_unit', unit) == unit and
                  _finite(lower, zero=True) and _finite(upper) and lower < upper and
                  raw.get('reference_analyte', marker) == marker and
                  raw.get('reference_specimen_type', raw.get('specimen_type')) == raw.get('specimen_type'))
    if applicable and o['valid_measurement'] and q == '=' and not o['reliability_reasons']:
        o['reference_status'] = 'low' if value < lower else 'high' if value > upper else 'within_range'
        if o['reference_status'] != 'within_range':
            _notice(o, 'outside_reference_range', f'Result is {o["reference_status"]} relative to the supplied applicable laboratory range.')
    else:
        _notice(o, 'reference_interpretation_unavailable', 'An applicable exact-result laboratory reference comparison is unavailable.')
    if (marker == 'vitamin_d' and o['valid_measurement'] and eligible_reference and
            'unsupported_analyte' not in o['metadata_reasons'] and
            'unsupported_or_unknown_specimen_type' not in o['metadata_reasons'] and not o['reliability_reasons']):
        code = _reference_notice(o['normalized_value'], q)
        _notice(o, code, _BAND_TEXT[code])
    return o


def _core_component(marker, observations, request, common_reasons):
    config = CORE[marker]
    c = {'score': None, 'display_score': None, 'status': 'unavailable',
         'weight': WEIGHTS[marker], 'weighted_contribution': None,
         'observation_id': None, 'reasons': list(common_reasons), 'notices': []}
    candidates = [o for o in observations if o['marker'] == marker]
    selector = request.get('selected_observation_ids', {}).get(marker)
    matches = [o for o in candidates if o['observation_id'] == selector] if selector is not None else candidates
    if len(matches) != 1:
        c['reasons'].append('missing_' + marker if not candidates else 'selection_required')
        return c, None
    o = matches[0]
    raw = o['observation']
    if not isinstance(raw, dict):
        c['reasons'].append('invalid_observation')
        return c, None
    c['observation_id'] = o['observation_id']
    c['notices'] = deepcopy(o['notices'])
    c['reasons'].extend(o['errors'] + o['metadata_reasons'] + o['reliability_reasons'])
    unit = raw.get('unit')
    factor = config['units'].get(unit) if isinstance(unit, str) else None
    if factor is None:
        c['reasons'].append('unsupported_unit')
    if raw.get('analyte') != config['analyte']:
        c['reasons'].append('unsupported_analyte')
    if raw.get('specimen_type') not in ('serum', 'plasma'):
        c['reasons'].append('unsupported_or_unknown_specimen_type')
    if o['qualifier'] != '=':
        c['reasons'].append('bounded_result')
    if not _finite(raw.get('value')):
        c['reasons'].append('invalid_value')
    lower, upper = raw.get('lower_limit'), raw.get('upper_limit')
    range_ok = (raw.get('reference_range_applicable') is True and factor is not None
                and raw.get('reference_unit', unit) == unit
                and raw.get('reference_analyte', marker) == marker
                and raw.get('reference_specimen_type', raw.get('specimen_type')) == raw.get('specimen_type')
                and _finite(lower, zero=True) and _finite(upper) and lower < upper)
    if not range_ok:
        c['reasons'].append('applicable_reference_range_required')
    elif upper * factor < config['anchors'][-1][0]:
        c['reasons'].append('reference_range_incompatible_with_curve')
    elif _finite(raw.get('value')) and raw['value'] > upper:
        c['reasons'].append('above_reference_range_review')
    context = request.get('context', {})
    fields = ('iron_confounders', 'recent_iron_treatment_or_transfusion') if marker == 'ferritin' else ('b12_supplementation_or_treatment',)
    for field in fields:
        state = context.get(field, 'unknown')
        if state not in ('absent', 'present', 'unknown'):
            state = 'unknown'
        if marker == 'ferritin' and state == 'present':
            c['reasons'].append(field + '_present')
        if state != 'absent':
            _notice(c, field + '_' + state, f'{field.replace("_", " ")} is {state}; nutrient adequacy cannot be inferred.')
    if marker == 'ferritin':
        _notice(c, 'ferritin_interpretation_limit', 'Ferritin can rise with inflammation or illness. Missing CRP does not exclude inflammation; these points do not establish iron sufficiency.')
    if not c['reasons']:
        value = raw['value'] * factor
        if not _finite(value):
            c['reasons'].append('invalid_normalized_value')
        else:
            anchors = config['anchors']
            points = 100.0
            for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
                if value <= x1:
                    points = y0 + (value - x0) * (y1 - y0) / (x1 - x0)
                    break
            c.update(score=points, display_score=display_score(points), status='scored',
                     normalized_value=value, normalized_unit=config['unit'],
                     weighted_contribution=points * WEIGHTS[marker])
    c['reasons'] = list(dict.fromkeys(c['reasons']))
    return c, o


def score_nutrition(request, *, today=None):
    """Return a new JSON-safe result. Supply evaluation_date in request or explicit today.

    Invalid envelope shapes raise ValueError; invalid individual observations are retained.
    There is deliberately no implicit host-date fallback.
    """
    if not isinstance(request, dict):
        raise ValueError('request must be an object')
    _safe(request)  # Validate supported Python value types before numerical processing.
    for key in ('person', 'context', 'observations', 'selected_observation_ids'):
        if not isinstance(request.get(key, {}), dict):
            raise ValueError(f'{key} must be an object')
    if today is not None and type(today) is not date:
        raise ValueError('today must be a datetime.date')
    evaluation_reasons = []
    supplied_date = request.get('evaluation_date')
    if supplied_date is not None:
        try:
            parsed = _parse_date(supplied_date)
            if today is not None and today != parsed:
                raise ValueError('Conflicting dates')
            today = parsed
        except ValueError:
            evaluation_reasons.append('invalid_evaluation_date')
            today = None
    elif today is None:
        evaluation_reasons.append('evaluation_date_required')
    person, context = request.get('person', {}), request.get('context', {})
    age = person.get('age')
    pregnancy = person.get('pregnancy_status', 'unknown')
    eligible_reference = (_finite(age) and age >= _PARAMS['minimum_point_age'] and
                          pregnancy in _PARAMS['eligible_pregnancy_statuses'])
    observations = []
    for marker, raw in request.get('observations', {}).items():
        if marker not in _MARKERS:
            raise ValueError(f'Unsupported marker: {marker}')
        for item in raw if isinstance(raw, list) else [raw]:
            observations.append(_observation(marker, item, today, eligible_reference))
    ids = [o['observation_id'] for o in observations if _text(o['observation_id'])]
    for o in observations:
        if _text(o['observation_id']) and ids.count(o['observation_id']) > 1:
            o['errors'].append('duplicate_observation_id')
    candidates = [o for o in observations if o['marker'] == 'vitamin_d']
    c = {'score': None, 'display_score': None, 'status': 'unavailable',
         'reasons': [], 'notices': [], 'observation_id': None}
    chosen, selection_reasons = None, []
    selector = request.get('selected_vitamin_d_id')
    if selector is not None:
        matches = [o for o in candidates if _text(selector) and o['observation_id'] == selector]
        if len(matches) == 1:
            chosen = matches[0]
        else:
            selection_reasons.append('selection_required')
    elif len(candidates) == 1:
        chosen = candidates[0]
    elif candidates:
        selection_reasons.append('selection_required')
    if not candidates:
        selection_reasons.append('missing_vitamin_d')
    input_reasons = list(chosen['errors']) if chosen else []
    if not _finite(age):
        input_reasons.append('invalid_age')
    metadata_reasons = evaluation_reasons + (list(chosen['metadata_reasons']) if chosen else [])
    eligibility_reasons = []
    if _finite(age) and age < _PARAMS['minimum_point_age']:
        eligibility_reasons.append('pediatric_points_not_defined')
    if pregnancy not in _PARAMS['eligible_pregnancy_statuses']:
        eligibility_reasons.append('pregnancy_outside_scope' if pregnancy == 'pregnant' else 'pregnancy_status_unknown')
    if _finite(age) and age >= _PARAMS['older_age_notice_threshold']:
        _notice(c, 'older_age_limited_evidence', 'Exact-age evidence is limited at age 85 and above.')
    for field in _CONTEXT_FIELDS:
        state = context.get(field, 'unknown')
        if state not in ('present', 'absent', 'unknown'):
            _notice(c, 'invalid_' + field, 'Invalid optional context was retained and treated as unknown.')
            state = 'unknown'
        if state != 'absent':
            _notice(c, field + '_' + state, f'{field.replace("_", " ").capitalize()} is {state}; points are not adjusted.')
    range_reasons, reliability_reasons = [], []
    if chosen:
        c['observation_id'] = chosen['observation_id']
        c['notices'].extend(deepcopy(chosen['notices']))
        reliability_reasons = chosen['reliability_reasons']
        if chosen['valid_measurement']:
            if chosen['qualifier'] != '=':
                range_reasons.append('bounded_result')
            elif chosen['normalized_value'] > _D['maximum_scored_nmol_l_inclusive']:
                range_reasons.append('above_scoring_range')
    c['reasons'] = list(dict.fromkeys(input_reasons + selection_reasons + metadata_reasons +
                                    eligibility_reasons + reliability_reasons + range_reasons))
    if chosen and not c['reasons']:
        value = _curve(chosen['normalized_value'])
        c.update(score=value, display_score=display_score(value), status='scored')
    available, unusable = [], []
    for index, o in enumerate(observations):
        reasons = list(dict.fromkeys(o['errors'] + o['metadata_reasons'] + o['reliability_reasons']))
        if o is chosen:
            reasons = list(dict.fromkeys(reasons + c['reasons']))
        elif o['marker'] == 'vitamin_d':
            reasons.append('not_selected')
        entry = {'marker': o['marker'], 'observation_id': o['observation_id'],
                 'observation_index': index, 'reasons': reasons}
        (unusable if reasons else available).append(entry)
    has_points = c['score'] is not None
    result = {
        'model_version': VERSION, 'domain_label': _PARAMS['domain_label'],
        'evaluation_date': today.isoformat() if today else None, 'input': deepcopy(request),
        'domain_score': None, 'domain_aggregation_status': _PARAMS['domain_aggregation_status'],
        'status': 'component_available' if has_points else 'unavailable',
        'components': {'vitamin_d': c}, 'observations': observations,
        'coverage': {'scored_component_count': int(has_points), 'defined_component_count': 1,
                     'available': available, 'unusable': unusable,
                     'missing': [] if candidates else [{'marker': 'vitamin_d', 'reasons': ['missing_vitamin_d']}],
                     'missing_requirements': list(c['reasons'])},
        'notices': [
            {'code': 'limited_nutrition_coverage', 'text': 'This component does not measure overall nutrition or diet quality.'},
            {'code': 'provisional_points', 'text': 'Experimental points are not clinically validated or a disease probability.'}],
    }
    components, selected = {}, []
    common = evaluation_reasons + eligibility_reasons + ([] if _finite(age) else ['invalid_age'])
    for marker in WEIGHTS:
        component, observation = _core_component(marker, observations, request, common)
        components[marker] = component
        if observation is not None:
            selected.append(observation)
    reasons = [f'{m}:{reason}' for m, component in components.items() for reason in component['reasons']]
    if not reasons and len(selected) == 2 and len({(o['observation'].get('specimen_date'), o['observation'].get('report_id'), o['observation'].get('specimen_type')) for o in selected}) != 1:
        reasons.append('core_collection_mismatch')
    total = sum(c['weighted_contribution'] for c in components.values()) if not reasons else None
    result.update(domain_score=total, score=total, display_score=display_score(total),
                  status='scored' if total is not None else 'unavailable',
                  domain_aggregation_status='fixed_core', weights=deepcopy(WEIGHTS), reasons=reasons)
    result['components'].update(components)
    for key in ('available', 'unusable'):
        result['coverage'][key] = [entry for entry in result['coverage'][key] if entry['marker'] not in WEIGHTS]
    for index, observation in enumerate(observations):
        marker = observation['marker']
        if marker not in WEIGHTS:
            continue
        component = components[marker]
        selected_result = observation['observation_id'] == component['observation_id'] and component['observation_id'] is not None
        entry = {'marker': marker, 'observation_id': observation['observation_id'],
                 'observation_index': index,
                 'reasons': list(component['reasons']) if selected_result else ['not_selected']}
        result['coverage']['unusable' if entry['reasons'] else 'available'].append(entry)
        if selected_result and component['score'] is not None:
            observation.update(normalized_value=component['normalized_value'], normalized_unit=component['normalized_unit'])
    result['coverage'].update(scored_component_count=sum(c['score'] is not None for c in components.values()),
                              defined_component_count=2, required=list(WEIGHTS),
                              missing=[{'marker': m, 'reasons': ['missing_' + m]} for m in WEIGHTS if not any(o['marker'] == m for o in observations)],
                              missing_requirements=reasons)
    result['notices'][0]['text'] = 'Nutrition summarizes B12 and ferritin only, not diet quality, protein intake or overall nutrient adequacy. Vitamin D is a separate optional component.'
    return _safe(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('--today', type=_parse_date, help='Explicit evaluation date (YYYY-MM-DD)')
    args = parser.parse_args()
    try:
        result = score_nutrition(json.loads(args.request.read_text(encoding='utf-8-sig')), today=args.today)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False, ensure_ascii=False))


if __name__ == '__main__':
    main()
