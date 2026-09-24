"""Verify the delivered archive in an isolated temporary directory using only its files."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile
from build_handoff import build


def main():
    archive = build()
    with tempfile.TemporaryDirectory(prefix='health-scorer-handoff-') as temp:
        destination = Path(temp).resolve()
        with ZipFile(archive) as package:
            for name in package.namelist():
                (destination / name).resolve().relative_to(destination)
            package.extractall(destination)
        root = destination / 'health-scorer'
        manifest = json.loads((root / 'MANIFEST.json').read_text())
        for name, expected in manifest['files'].items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', '.', '-p', 'test_*.py'], cwd=root, check=True)
        for name in ['worked', 'incomplete', 'age16', 'partial-error']:
            run = subprocess.run([sys.executable, 'health_scorer_api.py', f'integration_examples/{name}.request.json'],
                                 cwd=root, capture_output=True, text=True, encoding='utf-8')
            assert run.returncode == (1 if name == 'partial-error' else 0), run.stderr
            assert json.loads(run.stdout) == json.loads((root / f'integration_examples/{name}.response.json').read_text(encoding='utf-8'))
        node = shutil.which('node')
        if node:
            subprocess.run([node, 'test_integration_client.mjs'], cwd=root, check=True)
        else:
            print('Node unavailable; packaged JS checks not run.')
    print('PASS: extracted package hashes, isolated tests, four CLI fixtures and exit codes.')


if __name__ == '__main__':
    main()
