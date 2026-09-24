"""Preliminary metabolism v0.2 age extension. Standard library only.

See AGE_EXTENSION_AND_DETAILS.md and the original METABOLISM_V01_SPEC.md.
Not a clinically validated assessment.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import json
import math
from pathlib import Path

_PARAMS = json.loads(Path(__file__).with_name('metabolism_v01_parameters.json').read_text())
VERSION = _PARAMS['model_version']
MARKERS = tuple(_PARAMS['required_markers'])
LIPIDS = MARKERS[1:]


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        return False


def display_score(score):
    """Half-up to one decimal; never display a tiny positive score as zero."""
    if score is None:
        return None
    if 0 < score < 0.1:
        return '<0.1'
    return str(Decimal(str(score)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))


def _curve(marker, x, nonfasting=False):
    p = _PARAMS['curves'][marker]
    anchors = p['nonfasting_anchors'] if nonfasting else p['anchors']
    if marker == 'hba1c' and x < 4:
        return None, 'below_model_coverage'
    if marker == 'hdl_c' and x >= p['exclusive_upper_coverage']:
        return None, 'high_hdl_outside_model_coverage'
    if x <= anchors[0][0]:
        return (10 * (x / 0.5)**2 if marker == 'hdl_c' else anchors[0][1]), 'scored'
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if x <= x1:
            return y0 + (x-x0)/(x1-x0)*(y1-y0), 'scored'
    if marker == 'hdl_c':
        return 100.0, 'scored'
    x0, y0 = anchors[-1]
    return y0 * 2**(-(x-x0)/p['above_last_anchor']['interval']), 'scored'


def _normalize(marker, observation):
    if observation is None:
        return None, None, 'missing'
    if not isinstance(observation, dict):
        return None, None, 'invalid_input'
    value, unit = observation.get('value'), observation.get('unit')
    if value is None:
        return None, None, 'missing'
    if observation.get('qualifier') not in (None, '=') or (isinstance(value, str) and value.lstrip().startswith(('<', '>', '≤', '≥'))):
        return None, None, 'censored_result'
    if not _number(value):
        return None, None, 'invalid_input'
    f = _PARAMS['conversion_factors']
    conversions = {
        'hba1c': {'%': (1, 0), 'mmol/mol': (f['hba1c_ifcc_to_ngsp_slope'], f['hba1c_ifcc_to_ngsp_intercept'])},
        'triglycerides': {'mmol/L': (1, 0), 'mg/dL': (f['triglycerides_mg_dl_to_mmol_l'], 0)},
        'apob': {'g/L': (1, 0), 'mg/dL': (f['apob_mg_dl_to_g_l'], 0)},
        'glucose': {'mmol/L': (1, 0), 'mg/dL': (1, 0)},
        'bmi': {'kg/m²': (1, 0), 'kg/m2': (1, 0)},
        'waist': {'cm': (1, 0), 'in': (2.54, 0)},
        'systolic_bp': {'mmHg': (1, 0)}, 'diastolic_bp': {'mmHg': (1, 0)},
    }
    cholesterol = {'mmol/L': (1, 0), 'mg/dL': (f['cholesterol_mg_dl_to_mmol_l'], 0)}
    accepted = cholesterol if marker in ('ldl_c', 'hdl_c', 'total_cholesterol') else conversions.get(marker, {})
    if not isinstance(unit, str) or unit not in accepted:
        return None, None, 'unsupported_unit'
    scale, offset = accepted[unit]
    normalized = value * scale + offset
    if not _number(normalized):
        return None, None, 'invalid_input'
    canonical = {'hba1c': '%', 'apob': 'g/L', 'glucose': unit, 'bmi': 'kg/m²', 'waist': 'cm', 'systolic_bp': 'mmHg', 'diastolic_bp': 'mmHg'}.get(marker, 'mmol/L')
    return normalized, canonical, None


def _date(value, today):
    if value is None:
        return None, None
    try:
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value or parsed > today:
            raise ValueError
        return parsed, None
    except (ValueError, TypeError):
        return None, 'invalid_specimen_date'


def _flag(result, code, text):
    result['flags'].append({'code': code, 'text': text})


def _fasting(context):
    state = context.get('fasting_status', 'unknown')
    hours = context.get('fasting_hours')
    if state not in ('fasting', 'nonfasting', 'unknown'):
        return 'unknown', 'invalid_fasting_status', False
    if hours is None:
        return state, None, False
    if not (_number(hours) or (type(hours) in (int, float) and hours == 0)):
        return state, 'invalid_fasting_hours', False
    duration_state = 'fasting' if 8 <= hours < 24 else 'nonfasting' if hours < 8 else 'unknown'
    conflict = duration_state == 'unknown' or (state != 'unknown' and duration_state != state)
    if conflict:
        resolved = context.get('use_unknown_fasting_on_conflict') is True
        return 'unknown', None if resolved else 'fasting_context_conflict', True
    return duration_state, None, False


def _aggregate(scores, children):
    blocked = [key for key in children if scores[key] is None]
    value = None if blocked else sum(scores[key] for key in children)/len(children)
    return {'score': value, 'display_score': display_score(value), 'status': 'incomplete' if blocked else 'scored', 'blocked_prerequisites': blocked}


def score_metabolism(request, *, today=None):
    """Score one explicitly selected snapshot; return a fresh JSON-compatible dict.

    Invalid observation data gets statuses. Invalid envelope shapes raise ValueError.
    `today` accepts a date for reproducible metadata validation; defaults to date.today().
    """
    if not isinstance(request, dict):
        raise ValueError('request must be an object')
    for key in ('person', 'context', 'observations', 'optional_observations'):
        if key in request and not isinstance(request[key], dict):
            raise ValueError(f'{key} must be an object')
    today = today or date.today()
    person, context = request.get('person', {}), request.get('context', {})
    observations = request.get('observations', {})
    result = {'model_version': VERSION, 'model_status': 'preliminary_not_clinically_validated',
              'numerical_age_adjustment': False, 'numerical_sex_adjustment': False,
              'status': 'incomplete', 'score': None, 'display_score': None,
              'flags': [], 'blocking_reasons': [], 'markers': {}, 'components': {},
              'coverage': {'scored': 0, 'required': 4}, 'snapshot_date': None,
              'alternative_nonfasting': None, 'optional_context': {},
              'provenance': deepcopy(request)}
    pregnancy = person.get('pregnancy_status', 'unknown')
    gate = None
    if pregnancy == 'yes':
        gate = 'pregnancy_outside_scope'
        result['status'] = 'outside_scope'
        result['interpretation'] = 'This prototype does not support assessment during pregnancy.'
    elif pregnancy not in ('no', 'not_applicable'):
        gate = 'pregnancy_eligibility_required'
        result['status'] = 'eligibility_required'
        result['interpretation'] = 'Establish pregnancy eligibility before using this prototype.'
    age = person.get('age')
    age_issue = 'age_required' if age is None else 'invalid_age' if not _number(age) else None
    younger = age_issue is None and age < _PARAMS['adult_reference_minimum_age']
    older = age_issue is None and age >= _PARAMS['older_age_notice_from']
    result['age_applicability'] = 'not_assessed' if gate or age_issue else 'younger_age_extrapolation' if younger else 'older_age_limited_evidence' if older else 'adult_reference'
    if not gate and younger:
        _flag(result, 'younger_age_extrapolation', 'Experimental estimate for someone under 20: this uses unchanged adult scoring curves, has not been evaluated for this age group, and may be inaccurate. Pediatric reference ranges differ. Adult clinical labels are not applied; use the laboratory report and an age-appropriate clinical assessment.')
    elif not gate and older:
        _flag(result, 'older_age_limited_evidence', 'Experimental estimate for age 85+: this score is not age-adjusted and may be inaccurate. Our NHANES data group ages 85 and above together, so performance at your exact age has not been established. This is not a personalized treatment target.')
    fasting, fasting_issue, fasting_conflict = (None, None, False) if gate else _fasting(context)
    result['fasting_status'] = fasting
    normalized = {m: _normalize(m, observations.get(m)) for m in MARKERS}
    dates = {}
    metadata_issues = []
    for marker in MARKERS:
        raw = observations.get(marker)
        obs = raw if isinstance(raw, dict) else {}
        value, unit, issue = normalized[marker]
        r = {'marker': marker, 'version': 'hba1c-v0.1-unadjusted' if marker == 'hba1c' else VERSION,
             'original': deepcopy(raw), 'normalized_value': None if gate else value,
             'normalized_unit': None if gate else unit, 'score': None, 'display_score': None,
             'status': gate or issue or 'scored', 'reasons': [], 'flags': [],
             'report_id': obs.get('report_id'), 'source_id': obs.get('source_id'),
             'specimen_date': obs.get('specimen_date'), 'interpretation': []}
        result['markers'][marker] = r
        if gate:
            r['reasons'] = [gate]
            continue
        parsed, date_issue = _date(obs.get('specimen_date'), today)
        dates[marker] = parsed
        if date_issue:
            metadata_issues.append(f'{marker}:{date_issue}')
        reasons = [issue] if issue else []
        reliability = obs.get('reliability', 'unknown')
        if reliability not in ('valid', 'invalid', 'unknown'):
            reasons.append('invalid_reliability_status')
        elif reliability == 'invalid':
            reasons.append('laboratory_invalid')
        interference = context.get('hba1c_interference', 'unknown')
        if marker == 'hba1c':
            if interference == 'yes':
                reasons.append('interpretation_interference')
            elif interference not in ('no', 'unknown'):
                reasons.append('invalid_interference_status')
            elif interference == 'unknown':
                _flag(r, 'hba1c_interference_unknown', 'HbA1c interference context is incomplete.')
        if marker == 'triglycerides':
            if fasting_issue:
                reasons.append(fasting_issue)
            if fasting_conflict:
                _flag(r, 'fasting_conflict_recorded', 'Conflicting fasting context was retained; an explicit unknown route is required.')
        trusted = issue is None and reliability in ('valid', 'unknown') and (marker != 'hba1c' or interference in ('no', 'unknown'))
        tg, _, tg_issue = normalized['triglycerides']
        tg_obs = observations.get('triglycerides')
        tg_trusted = tg_issue is None and isinstance(tg_obs, dict) and tg_obs.get('reliability', 'unknown') in ('valid', 'unknown')
        # Only use TG to judge LDL reliability when it is demonstrably from the selected report.
        same_report = isinstance(obs.get('report_id'), str) and bool(obs.get('report_id').strip()) and isinstance(tg_obs, dict) and obs.get('report_id') == tg_obs.get('report_id')
        if marker == 'ldl_c':
            method = context.get('ldl_method', 'unknown')
            if method not in ('direct', 'friedewald', 'other_lab_calculated', 'unknown'):
                reasons.append('invalid_ldl_method')
            if not tg_trusted or not same_report:
                _flag(r, 'ldl_reliability_context_incomplete', 'Same-report trustworthy triglycerides are unavailable.')
            else:
                if tg >= _PARAMS['friedewald_tg_exclusive_upper_mmol_l']:
                    if method == 'friedewald':
                        reasons.append('ldl_calculation_unreliable')
                    elif method == 'unknown':
                        reasons.append('ldl_method_required')
                    elif method == 'other_lab_calculated' and reliability != 'valid':
                        reasons.append('ldl_validity_confirmation_required')
                if trusted and tg > 1.5:
                    _flag(r, 'ldl_limited_at_elevated_tg', 'LDL alone has limitations at elevated triglycerides; ApoB/non-HDL remain context only.')
        if trusted and not younger:
            _clinical_flags(marker, value, r, person, fasting, fasting_issue)
        if value is not None:
            score, coverage = _curve(marker, value, marker == 'triglycerides' and fasting == 'nonfasting')
            if coverage != 'scored':
                reasons.append(coverage)
            if not reasons:
                r['score'] = score
                if marker == 'triglycerides' and fasting == 'unknown':
                    r['alternative_nonfasting_score'] = _curve(marker, value, True)[0]
        r['reasons'] = reasons
        r['status'] = reasons[0] if reasons else 'scored'
        r['display_score'] = display_score(r['score'])
        r['interpretation'] = [f['text'] for f in r['flags']]
    scores = {m: result['markers'][m]['score'] for m in MARKERS}
    result['coverage']['scored'] = sum(s is not None for s in scores.values())
    c = result['components']
    c['blood_sugar'] = _aggregate(scores, ['hba1c'])
    c['triglycerides_hdl'] = _aggregate(scores, ['triglycerides', 'hdl_c'])
    scores['triglycerides_hdl'] = c['triglycerides_hdl']['score']
    c['lipid_health'] = _aggregate(scores, ['ldl_c', 'triglycerides_hdl'])
    if gate:
        result['blocking_reasons'] = [gate]
        for component in c.values():
            component['status'] = result['status']
        return _json_safe(result)
    result['blocking_reasons'] = [f'{m}:{r["status"]}' for m, r in result['markers'].items() if r['score'] is None]
    if age_issue:
        result['blocking_reasons'].append(age_issue)
    # Report IDs explicitly declare selection; a bundle never overrides contradictory IDs/dates.
    reports = [result['markers'][m]['report_id'] for m in LIPIDS]
    report_ok = all(isinstance(x, str) and bool(x.strip()) for x in reports) and len(set(reports)) == 1
    if not report_ok:
        metadata_issues.append('single_lipid_report_required')
        for name in ('triglycerides_hdl', 'lipid_health'):
            c[name].update(score=None, display_score=None, status='incomplete')
            c[name]['blocked_prerequisites'].append('single_lipid_report_required')
    lipid_dates = [dates[m] for m in LIPIDS if dates[m] is not None]
    if len(set(lipid_dates)) > 1:
        metadata_issues.append('lipid_report_dates_conflict')
        for name in ('triglycerides_hdl', 'lipid_health'):
            c[name].update(score=None, display_score=None, status='incomplete')
            c[name]['blocked_prerequisites'].append('lipid_report_dates_conflict')
    known_dates = [d for d in dates.values() if d is not None]
    result['snapshot_date'] = max(known_dates).isoformat() if known_dates else None
    if len(known_dates) < 4:
        bundle = request.get('snapshot_id')
        if not isinstance(bundle, str) or not bundle.strip():
            metadata_issues.append('snapshot_selection_required')
        _flag(result, 'dates_unverified', 'Some specimen dates are unavailable; the selected bundle is historical or undated.')
    misaligned = any(abs((dates['hba1c'] - d).days) > _PARAMS['maximum_specimen_gap_days'] for d in lipid_dates) if dates['hba1c'] else False
    if misaligned:
        metadata_issues.append('dates_not_aligned')
    result['blocking_reasons'].extend(metadata_issues)
    if age_issue in ('age_required', 'invalid_age'):
        result['status'] = 'eligibility_required'
    elif misaligned:
        result['status'] = 'dates_not_aligned'
    elif not result['blocking_reasons']:
        result['status'] = 'scored'
        result['score'] = (scores['hba1c'] + c['lipid_health']['score'])/2
        result['display_score'] = display_score(result['score'])
    alt = result['markers']['triglycerides'].get('alternative_nonfasting_score')
    if alt is not None:
        alt_tg_hdl = (alt + scores['hdl_c'])/2 if c['triglycerides_hdl']['score'] is not None else None
        alt_lipid = (scores['ldl_c'] + alt_tg_hdl)/2 if c['lipid_health']['score'] is not None else None
        result['alternative_nonfasting'] = {'triglycerides': alt, 'triglycerides_hdl': alt_tg_hdl,
            'lipid_health': alt_lipid, 'metabolism': (scores['hba1c'] + alt_lipid)/2 if result['score'] is not None else None,
            'interpretation': 'Sensitivity result using the nonfasting curve; not a confidence interval.'}
    for m, r in result['markers'].items():
        result['flags'].extend(dict(f, marker=m) for f in r['flags'])
    if context.get('acute_illness') == 'yes':
        _flag(result, 'acute_illness_context', 'Acute illness limits wellness interpretation of this measured profile.')
    result['optional_context'] = _optional(request.get('optional_observations', {}), result['markers']['hdl_c'], today)
    return _json_safe(result)


def _clinical_flags(marker, x, r, person, fasting, fasting_issue):
    if marker == 'hba1c':
        if x >= 6.5:
            _flag(r, 'a1c_diabetes_range', 'Diabetes diagnostic-range measurement; confirmation and clinical context apply.')
        elif x >= 6:
            _flag(r, 'a1c_prediabetes_range', 'Canadian prediabetes measurement range; this is not a new diagnosis.')
    elif marker == 'ldl_c':
        if x >= 5:
            _flag(r, 'ldl_markedly_elevated', 'LDL cholesterol is markedly elevated; discuss the result with a clinician.')
        if x < 0.5:
            _flag(r, 'ldl_low_value_review', 'Low LDL value is a model review trigger, not a diagnosis.')
    elif marker == 'triglycerides':
        if fasting == 'unknown':
            _flag(r, 'tg_fasting_unknown', 'Fasting status unknown: reference values are 1.7 fasting and 2.0 nonfasting mmol/L; primary uses the fasting curve.')
        elif not fasting_issue and x >= (1.7 if fasting == 'fasting' else 2):
            _flag(r, 'tg_elevated_reference' if fasting == 'fasting' else 'tg_elevated_nonfasting_reference', 'At or above the selected triglyceride reference; not an insulin resistance diagnosis.')
        if x >= 10:
            _flag(r, 'tg_very_high', 'Very high triglycerides need prompt clinical review because of pancreatitis risk.')
        elif x >= 5.6:
            _flag(r, 'tg_markedly_elevated', 'Triglycerides are markedly elevated; discuss this result with a clinician.')
        if x < 0.3:
            _flag(r, 'tg_low_value_review', 'Low triglyceride value is a model review trigger, not a diagnosis.')
    elif marker == 'hdl_c':
        reference = person.get('sex_reference', 'unknown')
        threshold = 1 if reference == 'male' else 1.3 if reference == 'female' else None
        if threshold is None:
            _flag(r, 'hdl_reference_unknown', 'Low HDL reference thresholds: male <1.0, female <1.3 mmol/L; no category assigned.')
        elif x < threshold:
            _flag(r, 'hdl_low_reference', 'Below the selected sex-reference HDL threshold; numerical points are unadjusted.')
        if x >= 2.5:
            _flag(r, 'hdl_high_outside_coverage', 'This prototype does not interpret this high HDL region numerically.')


def _optional(observations, hdl, today):
    results = {}
    supported = ('total_cholesterol', 'apob', 'glucose', 'bmi', 'waist', 'systolic_bp', 'diastolic_bp')
    for marker, raw in observations.items():
        obs = raw if isinstance(raw, dict) else {}
        value, unit, issue = _normalize(marker, raw)
        _, date_issue = _date(obs.get('specimen_date'), today)
        if marker not in supported:
            issue = 'unsupported_optional_marker'
        elif obs.get('reliability', 'unknown') not in ('valid', 'unknown'):
            issue = issue or 'laboratory_invalid'
        elif marker == 'glucose' and obs.get('type') not in ('fasting', 'random'):
            issue = issue or 'glucose_type_required'
        results[marker] = {'original': deepcopy(raw), 'normalized_value': value, 'normalized_unit': unit,
                           'status': issue or date_issue or 'context_only'}
    total = results.get('total_cholesterol')
    if total and total['status'] == 'context_only':
        tc_obs = observations['total_cholesterol']
        hdl_obs = hdl['original'] if isinstance(hdl['original'], dict) else {}
        comparable = isinstance(tc_obs.get('report_id'), str) and bool(tc_obs['report_id'].strip()) and tc_obs['report_id'] == hdl['report_id']
        comparable = comparable and (not tc_obs.get('specimen_date') or not hdl.get('specimen_date') or tc_obs['specimen_date'] == hdl['specimen_date'])
        _, hdl_date_issue = _date(hdl_obs.get('specimen_date'), today)
        trustworthy = hdl['normalized_value'] is not None and hdl_obs.get('reliability', 'unknown') in ('valid', 'unknown') and hdl_date_issue is None
        value = total['normalized_value'] - hdl['normalized_value'] if comparable and trustworthy else None
        results['non_hdl_c'] = {'normalized_value': value if value is not None and value > 0 else None,
            'normalized_unit': 'mmol/L', 'status': 'context_only' if value is not None and value > 0 else 'inconsistent_lipids' if value is not None else 'same_report_values_required'}
    return results


def _json_safe(value):
    # Preserve invalid nonfinite provenance as text so strict JSON serialization succeeds.
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path, help='JSON snapshot request')
    args = parser.parse_args()
    print(json.dumps(score_metabolism(json.loads(args.request.read_text(encoding='utf-8'))), indent=2, allow_nan=False))
