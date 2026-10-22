#!/usr/bin/env python3
"""Instalador 0.1.11; Ubuntu 24.04 x86_64; instalação Docker oficial."""
import argparse
import fcntl
import hashlib
import ipaddress
import json
import os
import pwd
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time


def run(args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def load(path):
    result = {}
    for i, line in enumerate(Path(path).read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise ValueError(f'Linha {i}: esperado CHAVE=valor')
        k, v = line.split('=', 1)
        if k in result:
            raise ValueError(f'Chave duplicada: {k}')
        result[k] = v.strip().strip('"').strip("'")
    return result


def ensure_user(name):
    try:
        account = pwd.getpwnam(name)
    except KeyError:
        run(['useradd', '--create-home', '--user-group', '--shell', '/bin/bash', name])
        account = pwd.getpwnam(name)
    if account.pw_uid < 1000 or account.pw_dir != '/home/' + name or account.pw_shell != '/bin/bash':
        raise ValueError('Usuário existente incompatível: exige UID >=1000, /home/NOME e /bin/bash')
    return account


def own_tree(path, account):
    os.chown(path, account.pw_uid, account.pw_gid)
    for base, dirs, files in os.walk(path, followlinks=False):
        for name in dirs + files:
            os.chown(Path(base) / name, account.pw_uid, account.pw_gid, follow_symlinks=False)


def as_user(account, args, **kwargs):
    run(['runuser', '-u', account.pw_name, '--', 'env', 'HOME=' + account.pw_dir,
         'USER=' + account.pw_name, 'LOGNAME=' + account.pw_name] + list(args), **kwargs)


def configure(project, c):
    env = project / '.env'
    text = env.read_text()
    secure_cookies = 'True' if c['ENABLE_HTTPS'] == 'true' else 'False'
    values = {'CSRF_COOKIE_SECURE': secure_cookies,
              'SESSION_COOKIE_SECURE': secure_cookies,
              'GEONODE_BASE_IMAGE_VERSION': c['GEONODE_VERSION'],
              'CELERY__WORKER_CONCURRENCY': c['CELERY_WORKERS'],
              'CELERY__AUTOSCALE_VALUES': f"{c['CELERY_WORKERS']},1",
              'CELERY__HARVESTER_CONCURRENCY': '1',
              'CELERY__HARVESTER_AUTOSCALE_VALUES': '1,1'}
    for key, value in values.items():
        if re.search(rf'^{key}=', text, re.M):
            text = re.sub(rf'^{key}=.*$', f'{key}={value}', text, flags=re.M)
        else:
            text += f'\n{key}={value}\n'
    text = re.sub(r'-Xms\S+', '-Xms' + c['GEOSERVER_XMS'], text)
    text = re.sub(r'-Xmx\S+', '-Xmx' + c['GEOSERVER_XMX'], text)
    env.write_text(text)
    env.chmod(0o600)
    uwsgi = project / 'src/uwsgi.ini'
    u = uwsgi.read_text()
    # Remover o autoscaling upstream (até 128 processos) para usar limite fixo.
    u = re.sub(r'^cheaper[^\n]*\n?', '', u, flags=re.M)
    u, n = re.subn(r'^processes\s*=.*$', 'processes = ' + c['UWSGI_PROCESSES'], u, flags=re.M)
    if n != 1:
        raise RuntimeError('Formato uwsgi.ini não reconhecido')
    uwsgi.write_text(u)
    req = project / 'src/requirements.txt'
    r, n = re.subn(r'^GeoNode[^\n]*', 'GeoNode==' + c['GEONODE_VERSION'], req.read_text(), flags=re.M)
    if n != 1:
        raise RuntimeError('Dependência GeoNode não reconhecida')
    req.write_text(r + '\n')
    # O proxy continua acessando internamente o GeoServer. Publicação só no loopback.
    compose = project / 'docker-compose.yml'
    s = compose.read_text()
    if '"8080:8080"' not in s:
        raise RuntimeError('Mapeamento GeoServer não reconhecido; revisão necessária')
    compose.write_text(s.replace('"8080:8080"', '"127.0.0.1:8080:8080"'))


def setup_updatelayers(project, c):
    name = 'geonode-updatelayers-' + c['PROJECT_NAME']
    cron = Path('/etc/cron.d') / name
    if c['UPDATE_LAYERS_ENABLED'] == 'false':
        if cron.exists():
            cron.unlink()
        print('Atualização automática desativada; dados e checksum preservados.')
        return
    run(['apt-get', 'install', '-y', 'cron', 'logrotate'])
    folder = Path('/usr/local/lib') / name
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    folder.chmod(0o700)
    runner = folder / 'updatelayers.py'
    shutil.copyfile(Path(__file__).resolve().with_name('updatelayers.py'), runner)
    runner.chmod(0o600)
    config = folder / 'config.json'
    config.write_text(json.dumps({'project': str(project), 'docker': shutil.which('docker'),
                                 'state': '/var/lib/' + name}))
    config.chmod(0o600)
    log = '/var/log/' + name + '.log'
    hours = int(c['UPDATE_LAYERS_INTERVAL_HOURS'])
    schedule = '0 0 * * *' if hours == 24 else f'0 */{hours} * * *'
    cron.write_text('SHELL=/bin/sh\nPATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n'
                    + f'{schedule} root /usr/bin/python3 {runner} {config} >> {log} 2>&1\n')
    cron.chmod(0o644)
    rotate = Path('/etc/logrotate.d') / name
    rotate.write_text(log + ' {\n weekly\n rotate 4\n compress\n missingok\n notifempty\n copytruncate\n}\n')
    rotate.chmod(0o644)
    run(['systemctl', 'enable', '--now', 'cron'])
    print('Agendamento criado em ' + str(cron))


def minimum_ram_mib(value):
    if not re.fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', value):
        raise ValueError('MIN_RAM_GB: use número não negativo, como 4, 7.5 ou 0 para desativar')
    minimum = float(value) * 1024
    if minimum == float('inf'):
        raise ValueError('MIN_RAM_GB fora do intervalo permitido')
    return minimum


def check_ram(available_mib, value):
    minimum = minimum_ram_mib(value)
    print(f'RAM detectada: {available_mib / 1024:.2f} GiB; mínimo configurado: {value} GiB.', flush=True)
    if minimum and available_mib < minimum:
        raise ValueError('RAM abaixo de MIN_RAM_GB. Ajuste esse parâmetro no env para este ambiente.')
    if not minimum:
        print('Checagem mínima de RAM desativada por MIN_RAM_GB=0.', flush=True)


def minimum_disk_gib(value):
    if not re.fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', value):
        raise ValueError('MIN_DISK_GB: use número não negativo, como 20, 15.5 ou 0 para desativar')
    minimum = float(value)
    if minimum == float('inf'):
        raise ValueError('MIN_DISK_GB fora do intervalo permitido')
    return minimum


def check_disk(free_gib, value):
    minimum = minimum_disk_gib(value)
    print(f'Disco livre no destino: {free_gib:.3f} GiB; mínimo configurado: {value} GiB.', flush=True)
    if minimum and free_gib < minimum:
        raise ValueError('Espaço livre abaixo de MIN_DISK_GB. Ajuste esse parâmetro no env para este ambiente.')
    if not minimum:
        print('Checagem mínima de disco desativada por MIN_DISK_GB=0.', flush=True)


def parse_compose_states(text):
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]


def pending_services(rows, https, web_returncode):
    required_healthy = {'django', 'geoserver', 'db'}
    required_running = {'celery', 'redis', 'geonode'}
    if https:
        required_running.add('letsencrypt')
    pending = []
    by_service = {}
    for row in rows:
        by_service.setdefault(row.get('Service'), []).append(row)
    for service in sorted(required_healthy | required_running):
        instances = by_service.get(service, [])
        if not instances:
            pending.append(service + ': ausente')
            continue
        for row in instances:
            state = row.get('State', 'desconhecido')
            health = row.get('Health') or 'sem healthcheck'
            if state != 'running' or (service in required_healthy and health != 'healthy'):
                pending.append(f'{service}: estado={state}, saúde={health}')
    if web_returncode != 0:
        mode = 'HTTPS com certificado válido' if https else 'HTTP'
        pending.append(f'resposta {mode}: curl retornou {web_returncode}')
    return pending


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--env', default='geonode-install.env')
    p.add_argument('--check', action='store_true', help='Validar configuração/DNS sem instalar')
    p.add_argument('--uninstall-geonode', action='store_true', help='Remover definitivamente o projeto e seus volumes')
    p.add_argument('--uninstall-geonode-completely', action='store_true', help='Apagar TODOS os recursos Docker locais, inclusive outros projetos, e desinstalar Docker')
    p.add_argument('--remove-docker', action='store_true', help='Remover também Docker, somente sem recursos de outros projetos')
    p.add_argument('--preview', action='store_true', help='Mostrar plano de desinstalação sem alterar recursos')
    p.add_argument('--configure-updatelayers', action='store_true', help='Configurar somente a tarefa em instalação existente')
    args = p.parse_args()
    c = load(args.env)
    c.setdefault('MIN_RAM_GB', '14')
    c.setdefault('MIN_DISK_GB', '30')
    c.setdefault('UPDATE_LAYERS_ENABLED', 'true')
    c.setdefault('UPDATE_LAYERS_INTERVAL_HOURS', '1')
    required = set('SYSTEM_USER GEONODE_PROJECT_REF GEONODE_VERSION DJANGO_BOOTSTRAP_VERSION PROJECT_NAME INSTALL_DIR HOSTNAME ENABLE_HTTPS LETSENCRYPT_EMAIL SERVER_IPV4 GEOSERVER_XMS GEOSERVER_XMX UWSGI_PROCESSES CELERY_WORKERS WAIT_SECONDS'.split())
    optional = {'UPDATE_LAYERS_ENABLED', 'UPDATE_LAYERS_INTERVAL_HOURS', 'MIN_RAM_GB', 'MIN_DISK_GB'}
    if set(c) != required | optional:
        raise ValueError(f'Chaves faltando: {required-set(c)}; desconhecidas: {set(c)-required-optional}')
    if args.remove_docker or args.preview:
        if not (args.uninstall_geonode or args.uninstall_geonode_completely):
            raise ValueError('--remove-docker e --preview exigem --uninstall-geonode')
    if args.uninstall_geonode_completely and (args.uninstall_geonode or args.remove_docker):
        raise ValueError('Use --uninstall-geonode-completely sozinho, opcionalmente com --preview')
    if args.uninstall_geonode or args.uninstall_geonode_completely:
        if args.check or args.configure_updatelayers:
            raise ValueError('Não combine desinstalação com instalação/configuração')
        from desinstalar import uninstall
        uninstall(c, args.remove_docker, args.preview, completely=args.uninstall_geonode_completely)
        return
    minimum_ram_mib(c['MIN_RAM_GB'])
    minimum_disk_gib(c['MIN_DISK_GB'])
    for k in ['GEONODE_VERSION', 'DJANGO_BOOTSTRAP_VERSION']:
        if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', c[k]):
            raise ValueError(f'{k}: use versão numérica')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', c['GEONODE_PROJECT_REF']) or c['GEONODE_PROJECT_REF'].startswith('-'):
        raise ValueError('Referência git inválida')
    if not re.fullmatch(r'[a-z][a-z0-9_]{2,39}', c['PROJECT_NAME']):
        raise ValueError('PROJECT_NAME: use letras minúsculas, números e underscore')
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,30}', c['SYSTEM_USER']) or c['SYSTEM_USER'] == 'root':
        raise ValueError('SYSTEM_USER inválido; use por exemplo geonode')
    if c['UPDATE_LAYERS_ENABLED'] not in ('true', 'false'):
        raise ValueError('UPDATE_LAYERS_ENABLED deve ser true ou false')
    if c['UPDATE_LAYERS_INTERVAL_HOURS'] not in ('1', '2', '3', '4', '6', '8', '12', '24'):
        raise ValueError('UPDATE_LAYERS_INTERVAL_HOURS: use 1, 2, 3, 4, 6, 8, 12 ou 24')
    hostname = c['HOSTNAME']
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', hostname) or 'seudominio' in hostname:
        raise ValueError('Preencha HOSTNAME com seu domínio, sem https ou barra')
    if c['ENABLE_HTTPS'] not in ['true', 'false']:
        raise ValueError('ENABLE_HTTPS deve ser true ou false')
    https = c['ENABLE_HTTPS'] == 'true'
    if https and ('.' not in hostname or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', c['LETSENCRYPT_EMAIL']) or 'seudominio' in c['LETSENCRYPT_EMAIL']):
        raise ValueError('HTTPS exige domínio e email válidos')
    for key in ['UWSGI_PROCESSES', 'CELERY_WORKERS', 'WAIT_SECONDS']:
        if not c[key].isdigit() or int(c[key]) < 1:
            raise ValueError(f'{key}: inteiro positivo obrigatório')
    for key in ['GEOSERVER_XMS', 'GEOSERVER_XMX']:
        if not re.fullmatch(r'[1-9][0-9]*[GM]', c[key]):
            raise ValueError(f'{key}: use valor como 2G ou 512M')
    def mib(v):
        return int(v[:-1]) * (1024 if v[-1] == 'G' else 1)
    if mib(c['GEOSERVER_XMS']) > mib(c['GEOSERVER_XMX']):
        raise ValueError('XMS não pode exceder XMX')
    project = Path(c['INSTALL_DIR'])
    if not project.is_absolute() or '..' in project.parts or len(project.parts) < 4 or not str(project).startswith('/opt/'):
        raise ValueError('INSTALL_DIR deve ser subdiretório absoluto de /opt, como /opt/geonode/curso')
    if https:
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            pass
        else:
            raise ValueError('Use domínio para HTTPS, não IP')
    addresses = sorted({x[4][0] for x in socket.getaddrinfo(hostname, None)})
    print('DNS:', ', '.join(addresses), flush=True)
    if c['SERVER_IPV4']:
        ipaddress.IPv4Address(c['SERVER_IPV4'])
        if c['SERVER_IPV4'] not in addresses:
            raise ValueError('SERVER_IPV4 não corresponde ao DNS do domínio')
    if args.check:
        print('Configuração e resolução DNS válidas. Portas e acesso externo não foram testados.')
        return
    if os.geteuid() != 0:
        raise ValueError('Execute como root/sudo')
    os_release = load('/etc/os-release')
    if os_release.get('ID') != 'ubuntu' or os_release.get('VERSION_ID') != '24.04' or os.uname().machine != 'x86_64':
        raise ValueError('Esta versão do instalador exige Ubuntu 24.04 x86_64')
    os.umask(0o077)
    lock = open('/run/geonode-installer.lock', 'w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fingerprint = hashlib.sha256(json.dumps({k: v for k, v in c.items() if k not in optional}, sort_keys=True).encode()).hexdigest()
    marker = project / '.installer-state.json'
    if project.exists() and not marker.exists():
        raise ValueError('Diretório já existe sem identificação deste instalador. Escolha um diretório novo.')
    if marker.exists() and json.loads(marker.read_text())['fingerprint'] != fingerprint:
        raise ValueError('Configuração mudou. Reexecução exige o mesmo env; upgrade não é suportado.')
    if args.configure_updatelayers:
        if not marker.exists():
            raise ValueError('Exige instalação existente identificada pelo instalador')
        setup_updatelayers(project, c)
        return
    ram = int(re.search(r'MemTotal:\s+(\d+)', Path('/proc/meminfo').read_text())[1]) / 1024
    check_ram(ram, c['MIN_RAM_GB'])
    # Novos pais precisam permitir travessia para o usuário dedicado.
    missing = []
    ancestor = project.parent
    while not ancestor.exists():
        missing.append(ancestor)
        ancestor = ancestor.parent
    project.parent.mkdir(parents=True, exist_ok=True)
    for directory in missing:
        directory.chmod(0o755)
    free = shutil.disk_usage(project.parent).free / 1024**3
    check_disk(free, c['MIN_DISK_GB'])
    os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
    run(['apt-get', 'update'])
    run(['apt-get', 'install', '-y', 'ca-certificates', 'curl', 'gnupg', 'git', 'python3-venv'])
    if not shutil.which('docker'):
        Path('/etc/apt/keyrings').mkdir(exist_ok=True)
        run(['curl', '-fsSL', '--retry', '3', 'https://download.docker.com/linux/ubuntu/gpg', '-o', '/etc/apt/keyrings/docker.asc'])
        Path('/etc/apt/keyrings/docker.asc').chmod(0o644)
        Path('/etc/apt/sources.list.d/docker.list').write_text('deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu noble stable\n')
        Path('/etc/apt/sources.list.d/docker.list').chmod(0o644)
        run(['apt-get', 'update'])
        run(['apt-get', 'install', '-y', 'docker-ce', 'docker-ce-cli', 'containerd.io', 'docker-buildx-plugin', 'docker-compose-plugin'])
    run(['systemctl', 'enable', '--now', 'docker'])
    run(['docker', 'compose', 'version'])
    account = ensure_user(c['SYSTEM_USER'])
    as_user(account, ['test', '-x', project.parent])
    if not marker.exists():
        with tempfile.TemporaryDirectory(prefix='.geonode-stage-', dir=project.parent) as td:
            stage = Path(td)
            os.chown(stage, account.pw_uid, account.pw_gid)
            template = stage / 'template'
            as_user(account, ['git', 'clone', '--depth', '1', '--branch', c['GEONODE_PROJECT_REF'], 'https://github.com/GeoNode/geonode-project.git', template])
            commit = subprocess.check_output(['runuser', '-u', account.pw_name, '--', 'git', '-C', str(template), 'rev-parse', 'HEAD'], text=True).strip()
            venv = stage / 'venv'
            as_user(account, ['python3', '-m', 'venv', venv])
            python = venv / 'bin/python'
            as_user(account, [python, '-m', 'pip', 'install', 'Django==' + c['DJANGO_BOOTSTRAP_VERSION']])
            generated = stage / c['PROJECT_NAME']
            generated.mkdir()
            os.chown(generated, account.pw_uid, account.pw_gid)
            as_user(account, [python, '-m', 'django', 'startproject', '--template=' + str(template), '-e', 'py,sh,md,rst,json,yml,ini,env,sample,properties', '-n', 'monitoring-cron', '-n', 'Dockerfile', c['PROJECT_NAME'], generated])
            # Segredos criptográficos, fornecidos por JSON (não aparecem na linha de comando).
            config = dict(hostname=hostname, https=https, email=c['LETSENCRYPT_EMAIL'], env_type='prod')
            for key in ['geonodepwd', 'geoserverpwd', 'pgpwd', 'dbpwd', 'geodbpwd', 'clientid', 'clientsecret', 'secret_key']:
                config[key] = secrets.token_hex(24)
            config_file = stage / 'secrets.json'
            config_file.write_text(json.dumps(config))
            os.chown(config_file, account.pw_uid, account.pw_gid)
            as_user(account, [python, generated / 'create-envfile.py', '--noinput', '--file', config_file], cwd=generated)
            configure(generated, c)
            (generated / '.installer-state.json').write_text(json.dumps({'fingerprint': fingerprint, 'template_commit': commit, 'installer': '0.1.11'}, indent=2))
            own_tree(generated, account)
            generated.rename(project)
    os.chdir(project)
    compose = ['docker', 'compose', '--env-file', '.env', '-f', 'docker-compose.yml']
    run(compose + ['config', '--quiet'])
    print('Construindo imagens; a primeira execução pode demorar.', flush=True)
    run(compose + ['build'])
    run(compose + ['up', '-d'])
    url = ('https' if https else 'http') + '://' + hostname + '/'
    deadline = time.monotonic() + int(c['WAIT_SECONDS'])
    mode = 'HTTPS com certificado válido' if https else 'HTTP'
    print('Aguardando serviços e resposta ' + mode + ' em ' + url, flush=True)
    while time.monotonic() < deadline:
        web = subprocess.run(['curl', '--noproxy', '*', '--fail', '--silent', '--location', '--max-time', '15', '--output', '/dev/null', '--resolve', f'{hostname}:{443 if https else 80}:127.0.0.1', url])
        states = subprocess.check_output(compose + ['ps', '--all', '--format', 'json'], text=True)
        rows = parse_compose_states(states)
        pending = pending_services(rows, https, web.returncode)
        if not pending:
            print('\nInstalação respondeu com sucesso: ' + url)
            print('Usuário: admin. Senha: ADMIN_PASSWORD no arquivo ' + str(project / '.env'))
            print('Ainda valide upload, mapa e dashboard antes da aula.')
            run(compose + ['ps'])
            setup_updatelayers(project, c)
            return
        print('Ainda aguardando: ' + '; '.join(pending), flush=True)
        time.sleep(10)
    run(compose + ['ps', '--all'])
    raise RuntimeError('Tempo excedido. Dados preservados. Consulte docker compose logs --tail=100 no diretório da instalação e execute novamente com o mesmo env. DNS, portas, SSL e tarefas podem precisar de revisão.')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nExecução interrompida. Containers e dados foram mantidos. A configuração final do updatelayers pode estar pendente.', file=sys.stderr)
        sys.exit(130)
    except (ValueError, RuntimeError, OSError, EOFError, subprocess.CalledProcessError) as exc:
        print(f'ERRO: {exc}', file=sys.stderr)
        sys.exit(1)
