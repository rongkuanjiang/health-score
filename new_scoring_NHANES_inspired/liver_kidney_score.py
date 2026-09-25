"""Provisional fixed-weight organ-stress score; see ORGAN_STRESS_V02_SPEC.md."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import json
import math
from pathlib import Path

_PARAMS = json.loads(Path(__file__).with_name('liver_kidney_v01_parameters.json').read_text(encoding='utf-8'))
VERSION = _PARAMS['model_version']
ADULT = 'ckd_epi_2021_creatinine'
U25 = 'ckid_u25_creatinine'


def _finite(value, *, zero=False):
    try:
        return type(value) in (int, float) and math.isfinite(value) and (value >= 0 if zero else value > 0)
    except OverflowError:
        return False


def _json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def display_score(value):
    if value is None:
        return None
    if 0 < value < 0.1:
        return '<0.1'
    return str(Decimal(str(value)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))


def _linear(value, anchors):
    if value <= anchors[0][0]:
        return float(anchors[0][1])
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if value <= x1:
            return y0 + (value-x0)/(x1-x0)*(y1-y0)
    return float(anchors[-1][1])


def _flag(result, code, text):
    result['flags'].append({'code': code, 'text': text})


def _empty():
    return {'score': None, 'display_score': None, 'status': 'unavailable', 'reasons': [], 'flags': []}


def _finish(result, value=None, status='scored'):
    result['reasons'] = list(dict.fromkeys(result['reasons']))
    if not result['reasons'] and value is not None:
        result.update(score=value, display_score=display_score(value), status=status)
    elif result['reasons']:
        result['status'] = result['reasons'][0]
    return result


def _observation(raw, today, *, allow_zero=False):
    r = _empty()
    r.update(observation=deepcopy(raw), normalized_value=None, normalized_unit=None,
             qualifier=None, specimen_age_days=None, available=isinstance(raw, dict) and raw.get('value') is not None)
    if raw is None:
        r['reasons'].append('missing')
        return r
    if not isinstance(raw, dict):
        r['reasons'].append('invalid_input')
        return r
    if raw.get('value') is None:
        r['reasons'].append('missing')
    elif not _finite(raw['value'], zero=allow_zero):
        r['reasons'].append('invalid_value')
    q = raw.get('qualifier', '=')
    r['qualifier'] = q
    if q not in ('=', '>', '>=', '<', '<='):
        r['reasons'].append('unsupported_qualifier')
    reliability = raw.get('reliability', 'unknown')
    if reliability in ('invalid', 'unreliable'):
        r['reasons'].append('unreliable_result')
    elif reliability == 'unknown':
        _flag(r, 'reliability_unknown', 'Laboratory reliability has not been confirmed.')
    elif reliability != 'valid':
        r['reasons'].append('invalid_reliability')
    if raw.get('lab_flag') is not None:
        _flag(r, 'laboratory_flag', raw['lab_flag'])
    stamp = raw.get('specimen_date')
    if stamp is not None:
        try:
            parsed = date.fromisoformat(stamp) if isinstance(stamp, str) and len(stamp) == 10 else None
            if parsed is None or parsed.isoformat() != stamp or parsed > today:
                raise ValueError
            r['specimen_age_days'] = (today-parsed).days
        except (ValueError, TypeError):
            r['reasons'].append('invalid_specimen_date')
    return r


def _report_id(obs):
    value = obs.get('report_id')
    return value if isinstance(value, str) and value.strip() else None


def _equation_issue(equation, age):
    if equation not in _PARAMS['kidney']['supported_reported_equations']:
        return 'unsupported_equation'
    if not _finite(age):
        return 'invalid_age'
    if equation == U25:
        return None if 1 <= age <= 25 else 'equation_age_outside_scope'
    return None if age >= 18 else 'equation_age_outside_scope'


def _calculate(creatinine, person, context, height, result):
    """Return (eGFR, equation); append explicit failures to the result."""
    age = person.get('age')
    equation = context.get('creatinine_equation', U25 if _finite(age) and age < 18 else ADULT)
    result['equation'] = equation
    issue = _equation_issue(equation, age)
    if equation not in (ADULT, U25):
        issue = 'unsupported_calculation_equation'
    if issue:
        result['reasons'].append(issue)
    sex = person.get('equation_sex')
    if sex not in ('male', 'female'):
        result['reasons'].append('equation_sex_required')
    calibration = creatinine.get('calibration')
    if calibration == 'research_calibrated':
        provenance = creatinine.get('calibration_provenance')
        if not isinstance(provenance, str) or not provenance.strip():
            result['reasons'].append('calibration_provenance_required')
    elif calibration != 'idms_traceable':
        result['reasons'].append('calibration_unknown')
    height_m = None
    if equation == U25:
        if height is None:
            result['reasons'].append('height_required')
        else:
            result['reasons'].extend('height_' + reason for reason in height['reasons'])
            height_m = height['normalized_value']
        if creatinine.get('assay_method') != 'enzymatic':
            _flag(result, 'enzymatic_assay_not_confirmed', 'Enzymatic creatinine measurement is not confirmed for CKiD U25.')
        _flag(result, 'u25_population_limitation', 'CKiD U25 was developed for pediatric and young-adult CKD; this does not validate wellness points.')
    if result['reasons']:
        return None
    scr = result['normalized_value']
    try:
        p = _PARAMS['kidney'][equation]
        s = p[sex]
        if equation == ADULT:
            ratio = scr/s['k']
            value = p['coefficient'] * min(ratio, 1)**s['alpha'] * max(ratio, 1)**p['high_creatinine_exponent'] * p['age_base']**age * s['factor']
        else:
            k = s['adult_k'] if age >= 18 else s['base_k'] * s['under_12_base' if age < 12 else 'age_12_to_18_base']**(age-p['age_exponent_origin'])
            value = k * height_m / scr
    except (OverflowError, ZeroDivisionError):
        value = None
    if not _finite(value):
        result['reasons'].append('invalid_computed_egfr')
        return None
    return value


def _height(raw, today):
    if raw is None:
        return None
    r = _observation(raw, today)
    obs = raw if isinstance(raw, dict) else {}
    if obs.get('unit') not in ('cm', 'm'):
        r['reasons'].append('unsupported_unit')
    if r['qualifier'] != '=':
        r['reasons'].append('censored_result')
    if not r['reasons']:
        r['normalized_value'] = obs['value'] / (100 if obs['unit'] == 'cm' else 1)
        r['normalized_unit'] = 'm'
        if not _finite(r['normalized_value']):
            r['reasons'].append('invalid_value')
    if obs.get('specimen_date') is None:
        _flag(r, 'height_date_unknown', 'Height should be measured near specimen collection; its date is unknown.')
    _finish(r)
    if not r['reasons']:
        r['status'] = 'available'
    return r


def _kidney(observations, person, context, point_gates, today):
    r = _empty()
    route = context.get('kidney_route', 'reported' if 'egfr' in observations else 'creatinine')
    key = 'egfr' if route == 'reported' else 'creatinine'
    raw = observations.get(key)
    marker = _observation(raw, today)
    obs = raw if isinstance(raw, dict) else {}
    r.update(route=route, equation=None, egfr=None, egfr_bound=None, score_envelope=None,
             markers={key: marker}, coverage={})
    if route not in ('reported', 'creatinine'):
        marker['reasons'].append('unsupported_kidney_route')
    if not _report_id(obs):
        marker['reasons'].append('report_id_required')
    if obs.get('specimen_date') is None:
        marker['reasons'].append('specimen_date_required')
    for key_context in ('dialysis', 'acute_kidney_injury'):
        state = context.get(key_context, 'unknown')
        if state == 'yes':
            marker['reasons'].append(key_context + '_outside_scope')
        elif state == 'unknown':
            _flag(r, key_context + '_unknown', key_context.replace('_', ' ').capitalize() + ' status is unknown; interpretation is limited.')
        elif state != 'no':
            marker['reasons'].append('invalid_' + key_context + '_status')
    q = marker['qualifier']
    value = None
    if route == 'reported':
        equation = obs.get('equation')
        r['equation'] = equation
        issue = _equation_issue(equation, person.get('age'))
        if issue:
            marker['reasons'].append(issue)
        if obs.get('unit') not in ('mL/min/1.73m2', 'mL/min/1.73m²'):
            marker['reasons'].append('unsupported_unit')
        if _finite(obs.get('value')) and obs.get('unit') in ('mL/min/1.73m2', 'mL/min/1.73m²'):
            marker.update(normalized_value=obs['value'], normalized_unit='mL/min/1.73m2')
        if not marker['reasons']:
            value = obs['value']
    elif route == 'creatinine':
        if q != '=':
            marker['reasons'].append('censored_creatinine_not_supported')
        unit = obs.get('unit')
        if unit not in ('mg/dL', 'µmol/L', 'μmol/L', 'umol/L'):
            marker['reasons'].append('unsupported_unit')
        elif _finite(obs.get('value')):
            marker['normalized_value'] = obs['value'] / (1 if unit == 'mg/dL' else _PARAMS['kidney']['creatinine_umol_l_per_mg_dl'])
            marker['normalized_unit'] = 'mg/dL'
            if not _finite(marker['normalized_value']):
                marker['reasons'].append('invalid_value')
        height = _height(observations.get('height'), today)
        if height is not None:
            r['markers']['height'] = height
        value = _calculate(obs, person, context, height, marker)
        r['equation'] = marker.get('equation')
    if context.get('previous_egfr_equation') is not None and context['previous_egfr_equation'] != r['equation']:
        _flag(r, 'equation_route_changed', 'The eGFR equation changed; longitudinal values may not be directly comparable.')
    points = None
    status = 'scored'
    if value is not None:
        anchors = _PARAMS['kidney']['anchors']
        curve = _linear(value, anchors)
        if q == '=':
            r['egfr'] = value
            points = curve
        else:
            r['egfr_bound'] = {'value': value, 'qualifier': q, 'unit': 'mL/min/1.73m2'}
            envelope = [curve, 100.0] if q in ('>', '>=') else [0.0, curve]
            r['score_envelope'] = envelope
            _flag(r, 'bounded_result', 'The laboratory reported a bound, not an exact eGFR.')
            if envelope[0] == envelope[1]:
                points, status = envelope[0], 'scored_from_bound'
            else:
                r['reasons'].append('bounded_result')
        for threshold, code in ((60, 'egfr_below_60'), (15, 'egfr_below_15')):
            established = q == '=' and value < threshold or q == '<' and value <= threshold or q == '<=' and value < threshold
            if established:
                _flag(r, code, f'This result establishes eGFR below {threshold}. Clinical interpretation is needed; one measurement does not establish chronic disease.')
        if q != '=':
            _flag(r, 'bound_limits_interpretation', 'Interpretation is limited to what the reported bound establishes.')
    _finish(marker)
    marker['usable_for_estimation'] = value is not None
    if value is not None:
        marker['status'] = 'available' if q == '=' else 'bounded_result'
    r['reasons'].extend(marker['reasons'])
    r['reasons'].extend(point_gates)
    # Pediatric or otherwise ineligible people must not receive point envelopes either.
    if point_gates:
        r['score_envelope'] = None
    for m in r['markers'].values():
        r['flags'].extend(m['flags'])
    r['coverage'] = {'selected_input': key, 'available': marker['available'],
                     'usable_for_estimation': value is not None, 'missing_or_unusable': list(marker['reasons'])}
    _finish(r, points, status)
    r['coverage']['usable_for_points'] = r['score'] is not None
    r['coverage']['point_blocking_reasons'] = list(r['reasons'])
    return r


def _liver(observations, context, point_gates, today):
    r = _empty()
    r['markers'] = {}
    for key in _PARAMS['liver']['required_markers']:
        raw = observations.get(key)
        obs = raw if isinstance(raw, dict) else {}
        m = _observation(raw, today)
        r['markers'][key] = m
        if obs.get('unit') not in _PARAMS['liver']['accepted_units'][key]:
            m['reasons'].append('unsupported_unit')
        elif _finite(obs.get('value')):
            m.update(normalized_value=obs['value'], normalized_unit=obs['unit'])
        if obs.get('reference_unit', obs.get('unit')) != obs.get('unit'):
            m['reasons'].append('reference_unit_mismatch')
        if m['qualifier'] != '=':
            m['reasons'].append('censored_result_not_supported')
        lower, upper = obs.get('lower_limit'), obs.get('upper_limit')
        limits_valid = _finite(lower, zero=True) and _finite(upper) and lower < upper
        if not limits_valid:
            m['reasons'].append('invalid_or_missing_reference_limits')
        if obs.get('reference_range_applicable') is not True:
            m['reasons'].append('reference_range_applicability_required')
        points = None
        if not m['reasons']:
            value = m['normalized_value']
            m['upper_limit_ratio'] = value / upper
            if not math.isfinite(m['upper_limit_ratio']):
                m['reasons'].append('invalid_normalized_ratio')
            elif value < lower:
                m['reasons'].append('below_reference_range_not_scored')
            else:
                points = _linear(m['upper_limit_ratio'], _PARAMS['liver']['upper_limit_ratio_anchors'])
            if value > upper:
                _flag(m, key + '_above_upper_limit', f'{key.upper()} exceeds its applicable laboratory upper limit. Clinical interpretation is needed; points do not measure injury severity.')
        m['reasons'].extend(point_gates)
        _finish(m, points)
        m['weight'] = _PARAMS['effective_weights'][key]
        m['weighted_contribution'] = None if m['score'] is None else m['weight'] * m['score']
        r['flags'].extend(dict(flag, marker=key) for flag in m['flags'])
        if m['score'] is None:
            r['reasons'].append(key + '_unavailable')
    raw_markers = [observations.get(key) for key in _PARAMS['liver']['required_markers']]
    records = [obs if isinstance(obs, dict) else {} for obs in raw_markers]
    reports = [_report_id(obs) for obs in records]
    if not all(reports):
        r['reasons'].append('matching_report_ids_required')
    elif len(set(reports)) != 1:
        r['reasons'].append('report_id_mismatch')
    dates = [obs.get('specimen_date') for obs in records]
    if len({str(stamp) for stamp in dates if stamp is not None}) > 1:
        r['reasons'].append('specimen_date_mismatch')
    if any(stamp is None for stamp in dates) and context.get('same_snapshot_confirmed') is not True:
        r['reasons'].append('same_snapshot_confirmation_required')
    r['reasons'].extend(point_gates)
    r['coverage'] = {'available': sum(m['available'] for m in r['markers'].values()), 'required': len(records),
                     'scored': sum(m['score'] is not None for m in r['markers'].values()),
                     'missing_or_unusable': {key: m['reasons'] for key, m in r['markers'].items() if m['reasons']}}
    points = sum(_PARAMS['liver']['weights'][key] * m['score'] for key, m in r['markers'].items()) if not r['reasons'] else None
    _finish(r, points)
    r['coverage']['group_blocking_reasons'] = list(r['reasons'])
    return r


def score_liver_kidney(request, *, today=None):
    """Score one snapshot without mutation; bad envelope shapes raise ValueError.

    Input is JSON data. Nonfinite numeric observations get reasons, and their raw
    provenance is returned as strings so the response always permits strict JSON.
    See LIVER_KIDNEY_ENGINE_README.md for the explicit input contract.
    """
    if not isinstance(request, dict):
        raise ValueError('request must be an object')
    for key in ('person', 'context', 'observations', 'optional_observations'):
        if key in request and not isinstance(request[key], dict):
            raise ValueError(f'{key} must be an object')
    today = today or date.today()
    person, context = request.get('person', {}), request.get('context', {})
    observations = request.get('observations', {})
    r = {'model_version': VERSION, 'model_status': 'preliminary_not_clinically_validated',
         'domain_score': None, 'score': None, 'display_score': None,
         'aggregation_status': 'insufficient_core_data',
         'weights': deepcopy(_PARAMS['effective_weights']),
         'reasons': [], 'flags': [], 'provenance': deepcopy(request)}
    gates = []
    age = person.get('age')
    if not _finite(age):
        gates.append('invalid_age')
    elif age < _PARAMS['minimum_point_age']:
        gates.append('pediatric_points_not_defined')
        _flag(r, 'pediatric_points_not_defined', 'Age-appropriate estimates may be shown, but pediatric wellness points are not defined.')
    elif age >= _PARAMS['older_age_notice_threshold']:
        _flag(r, 'older_age_limited_evidence', 'Evidence at age 85 and above is limited; points are not age-percentile estimates.')
    pregnancy = person.get('pregnancy_status', 'unknown')
    if pregnancy == 'pregnant':
        gates.append('pregnancy_outside_scope')
    elif pregnancy not in ('not_pregnant', 'not_applicable'):
        gates.append('pregnancy_eligibility_required')
    _flag(r, 'preliminary_points', 'Points are unvalidated modeling choices, not organ-function percentages or disease probabilities.')
    _flag(r, 'limited_organ_coverage', 'These components do not assess complete organ health. Normal enzymes or high points do not exclude disease.')
    kidney = _kidney(observations, person, context, gates, today)
    liver = _liver(observations, context, gates, today)
    r['components'] = {'kidney': kidney, 'liver': liver}
    _flag(r, 'weighted_average_limit', 'The total is a weighted summary. An abnormal marker can coexist with a high total; review the individual results and laboratory flags.')
    _flag(r, 'liver_marker_specificity', 'ALP can originate from bone as well as liver. These points summarize measurements, not the cause of an abnormal result.')
    r['optional_context'] = {}
    supplied = request.get('optional_observations', {})
    for key in _PARAMS['context_only']:
        raw = supplied.get(key, observations.get(key))
        m = _observation(raw, today, allow_zero=True)
        if isinstance(raw, dict) and (not isinstance(raw.get('unit'), str) or not raw['unit'].strip()):
            m['reasons'].append('unit_required')
        # Context has no conversion or point rules: retained, never interpreted as normal.
        m['usable_for_display'] = m['available'] and not m['reasons']
        m['status'] = 'context_only' if m['usable_for_display'] else (m['reasons'][0] if m['reasons'] else 'unavailable')
        r['optional_context'][key] = m
        if key in ('uacr', 'cystatin_c', 'bun', 'uric_acid'):
            kidney['flags'].extend(dict(flag, marker=key) for flag in m['flags'])
        else:
            liver['flags'].extend(dict(flag, marker=key) for flag in m['flags'])
    uacr = r['optional_context']['uacr']
    if not uacr['usable_for_display']:
        _flag(kidney, 'uacr_missing_or_unusable', 'Urine albumin information is missing or unusable; kidney-damage coverage is incomplete.')
    r['coverage'] = {key: component['coverage'] for key, component in r['components'].items()}
    r['coverage']['context'] = {key: {'available': m['available'], 'usable_for_display': m['usable_for_display'], 'reasons': m['reasons']} for key, m in r['optional_context'].items()}
    for component in r['components'].values():
        r['flags'].extend(component['flags'])
    count = sum(c['score'] is not None for c in r['components'].values())
    marker_scores = {'egfr': kidney['score'], **{key: m['score'] for key, m in liver['markers'].items()}}
    r['marker_scores'] = marker_scores
    r['weighted_contributions'] = {key: None if value is None else value * r['weights'][key] for key, value in marker_scores.items()}
    r['coverage'].update(required=len(_PARAMS['required_markers']), scored=sum(value is not None for value in marker_scores.values()),
                         missing_or_unusable=[key for key, value in marker_scores.items() if value is None])
    r['reasons'].extend(gates)
    for key, component in r['components'].items():
        if component['score'] is None:
            r['reasons'].append(key + '_unavailable')
        r['reasons'].extend(key + ':' + reason for reason in component['reasons'])
    # A total must not mix a recent organ panel with an unrelated old kidney result.
    # Missing liver dates may be explicitly resolved within its matched report only.
    kidney_raw = kidney['markers'][kidney['coverage']['selected_input']]['observation']
    core_records = [kidney_raw, *(m['observation'] for m in liver['markers'].values())]
    stamps = []
    for obs in core_records:
        stamp = obs.get('specimen_date') if isinstance(obs, dict) else None
        if stamp is not None:
            try:
                stamps.append(date.fromisoformat(stamp))
            except (ValueError, TypeError):
                pass  # Invalid dates already block the component.
    if count == 2:
        if not any(isinstance(obs, dict) and obs.get('specimen_date') for obs in core_records[1:]):
            r['reasons'].append('liver_date_required_for_total')
        elif (max(stamps) - min(stamps)).days > _PARAMS['maximum_specimen_gap_days']:
            r['reasons'].append('specimen_gap_exceeds_90_days')
    r['reasons'] = list(dict.fromkeys(r['reasons']))
    if count == 2 and not r['reasons']:
        r['domain_score'] = sum(r['weighted_contributions'].values())
        r['score'] = r['domain_score']
        r['display_score'] = display_score(r['domain_score'])
        r['aggregation_status'] = 'fixed_weight_complete_core'
    r['status'] = 'scored' if r['domain_score'] is not None else ('partial' if r['coverage']['scored'] else 'unavailable')
    r['coverage']['domain_blocking_reasons'] = list(r['reasons'])
    r['review_required'] = any(f['code'] == 'laboratory_flag' or f['code'].endswith('_above_upper_limit') or f['code'] in ('egfr_below_60', 'egfr_below_15') for f in r['flags'])
    return _json_safe(r)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    args = parser.parse_args()
    result = score_liver_kidney(json.loads(args.request.read_text(encoding='utf-8-sig')))
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
