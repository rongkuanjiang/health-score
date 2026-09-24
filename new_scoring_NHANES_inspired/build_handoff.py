"""Build an allowlisted handoff ZIP with synthetic examples and SHA-256 manifest."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from health_scorer_api import API_VERSION, PACKAGE_VERSION, SCORERS, score_request

ROOT = Path(__file__).resolve().parent
DOMAIN_FILES = {'metabolism': 'metabolism', 'organ-stress': 'liver_kidney',
                'inflammation': 'inflammation', 'nutrition': 'nutrition',
                'system-stability': 'system_stability'}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def create_examples():
    domains = {domain: json.loads((ROOT / f'example_{name}_request.json').read_text(encoding='utf-8'))
               for domain, name in DOMAIN_FILES.items()}
    full = {'api_version': API_VERSION, 'evaluation_date': '2026-09-24', 'domains': domains}
    incomplete = {'api_version': API_VERSION, 'evaluation_date': '2026-09-24',
                  'domains': {domain: {} for domain in domains}}
    age = deepcopy(full)
    for raw in age['domains'].values():
        raw.setdefault('person', {})['age'] = 16
    partial = deepcopy(full)
    partial['domains']['nutrition'] = {'observations': []}
    for name, request in [('worked', full), ('incomplete', incomplete), ('age16', age), ('partial-error', partial)]:
        write_json(ROOT / 'integration_examples' / f'{name}.request.json', request)
        write_json(ROOT / 'integration_examples' / f'{name}.response.json', score_request(request))


def build(output_dir=None):
    create_examples()
    files = ['health_scorer_api.py', 'dashboard_server.py', 'integration_schema.json',
             'integration_client.mjs', 'INTEGRATION_HANDOFF.md', 'RELEASE_REVIEW.md',
             'README.md', 'DASHBOARD_README.md', 'ENGINE_README.md',
             'AGE_EXTENSION_AND_DETAILS.md', 'HBA1C_V01.md', 'hba1c_evidence_brief.md',
             'NEXT_DOMAIN_PLAN.md', 'PROTOTYPE_PROGRESS_REPORT.md', 'build_handoff.py', 'verify_handoff.py']
    for name in DOMAIN_FILES.values():
        files += [f'{name}_score.py', f'{name}_v01_parameters.json', f'example_{name}_request.json',
                  f'{name.upper()}_V01_SPEC.md', f'test_{name}_score.py',
                  f'nhanes_inventory/{name}_v01_evaluation.md']
        if name != 'metabolism':
            files.append(f'{name.upper()}_ENGINE_README.md')
    files += ['hba1c_score.mjs', 'hba1c_score.test.mjs', 'test_integration.py', 'test_integration_client.mjs',
              'test_dashboard.py']
    files += [str(path.relative_to(ROOT)).replace('\\', '/') for path in (ROOT / 'dashboard').iterdir() if path.is_file()]
    files += [str(path.relative_to(ROOT)).replace('\\', '/') for path in (ROOT / 'integration_examples').glob('*.json')]
    output_dir = Path(output_dir) if output_dir else ROOT / 'dist'
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f'health-scorer-{PACKAGE_VERSION}.zip'
    manifest = {'package_version': PACKAGE_VERSION, 'api_version': API_VERSION,
                'files': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sorted(set(files))}}
    with ZipFile(archive, 'w', ZIP_DEFLATED) as package:
        for name in sorted(set(files)):
            package.write(ROOT / name, f'health-scorer/{name}')
        package.writestr('health-scorer/MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    return archive


if __name__ == '__main__':
    print(build())
