#!/usr/bin/env python3
"""Executado por root via cron; sem dependências adicionais nos containers."""
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime


def sync(config):
    state = Path(config['state'])
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (state / 'lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Outra atualização está em execução.', flush=True)
            return
        compose = [config['docker'], 'compose', '--project-directory', config['project'],
                   '--env-file', config['project'] + '/.env', '-f', config['project'] + '/docker-compose.yml']
        # find retorna erro se o workspace não existe. O checksum usa conteúdo e nomes.
        result = subprocess.check_output(compose + ['exec', '-T', 'geoserver', 'find',
            '/geoserver_data/data/workspaces/geonode', '-type', 'f', '-exec', 'sha256sum', '{}', '+'])
        if not result.strip():
            raise RuntimeError('Workspace vazio; checksum anterior preservado.')
        digest = hashlib.sha256(b'\n'.join(sorted(result.splitlines()))).hexdigest()
        previous = state / 'checksum.sha256'
        if previous.exists() and previous.read_text().strip() == digest:
            print('Sem alterações no workspace.', flush=True)
            return
        print('Atualizando camadas (primeira execução ou workspace alterado)...', flush=True)
        subprocess.run(compose + ['exec', '-T', 'django', 'python3', 'manage.py', 'updatelayers'], check=True)
        temporary = state / 'checksum.tmp'
        temporary.write_text(digest + '\n')
        temporary.replace(previous)
        print('Atualização concluída.', flush=True)


if __name__ == '__main__':
    print(datetime.now().astimezone().isoformat(), flush=True)
    try:
        sync(json.loads(Path(sys.argv[1]).read_text()))
    except Exception as exc:
        print('ERRO: ' + str(exc), file=sys.stderr, flush=True)
        sys.exit(1)
