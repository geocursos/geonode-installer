"""Remoção explícita e limitada aos recursos identificados do projeto."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def output(args):
    return subprocess.check_output(args, text=True).strip()


def run(args):
    subprocess.run(args, check=True)


def fingerprint(c):
    return hashlib.sha256(json.dumps({k: v for k, v in c.items()
        if k not in {'UPDATE_LAYERS_ENABLED', 'UPDATE_LAYERS_INTERVAL_HOURS', 'MIN_RAM_GB', 'MIN_DISK_GB'}}, sort_keys=True).encode()).hexdigest()


def inspect_many(kind, ids):
    return json.loads(output(['docker', kind, 'inspect', *ids])) if ids else []


def inventory(project):
    compose = ['docker', 'compose', '--project-directory', str(project), '--env-file', str(project / '.env'), '-f', str(project / 'docker-compose.yml')]
    config = json.loads(output(compose + ['config', '--format', 'json']))
    name = config['name']
    containers = inspect_many('container', output(['docker', 'ps', '-aq']).split())
    volumes = inspect_many('volume', output(['docker', 'volume', 'ls', '-q']).split())
    networks = inspect_many('network', output(['docker', 'network', 'ls', '-q']).split())
    images = inspect_many('image', output(['docker', 'image', 'ls', '-aq', '--no-trunc']).split())
    owned = lambda obj: (obj.get('Labels') or {}).get('com.docker.compose.project') == name
    target = [o for o in containers if owned({'Labels':o['Config'].get('Labels')})]
    # Require the Compose working directory to match, not just a matching name.
    for o in target:
        wd = o['Config']['Labels'].get('com.docker.compose.project.working_dir', '')
        if not wd or Path(wd).resolve() != project:
            raise ValueError('Container com mesmo nome de projeto pertence a outro diretório; remoção bloqueada.')
    tv = [o['Name'] for o in volumes if owned(o)]
    tn = [o['Name'] for o in networks if owned(o)]
    target_ids = {o['Id'] for o in target}
    for o in containers:
        if o['Id'] not in target_ids and any(m.get('Name') in tv for m in o.get('Mounts', [])):
            raise ValueError('Volume do projeto também está ligado a outro container; remoção bloqueada.')
    target_images = {o['Image'] for o in target}
    for service in config['services'].values():
        if service.get('image'):
            found = subprocess.run(['docker', 'image', 'inspect', service['image']], text=True, capture_output=True)
            if found.returncode == 0:
                target_images.update(i['Id'] for i in json.loads(found.stdout))
    foreign = []
    foreign += ['container ' + o.get('Name', o['Id']) for o in containers if o['Id'] not in target_ids]
    foreign += ['volume ' + o['Name'] for o in volumes if o['Name'] not in tv]
    foreign += ['rede ' + o['Name'] for o in networks if o['Name'] not in tn and o['Name'] not in ('bridge','host','none')]
    foreign += ['imagem ' + o['Id'] for o in images if o['Id'] not in target_images and not owned({'Labels':o.get('Config',{}).get('Labels')})]
    # External resources are never removed by the project uninstall.
    external = [v.get('name',k) for section in ('volumes','networks') for k,v in config.get(section,{}).items() if v.get('external')]
    return {'name':name, 'containers':[o['Id'] for o in target], 'volumes':tv, 'networks':tn,
            'foreign':sorted(set(foreign)), 'external':external}


def global_inventory(project):
    # Este plano é global: não filtra por labels nem depende do Compose já removido.
    def ids(args):
        return sorted(set(output(args).split()))
    return {
        'name': 'TODO O DOCKER LOCAL',
        'containers': ids(['docker', 'container', 'ls', '-aq', '--no-trunc']),
        'volumes': ids(['docker', 'volume', 'ls', '-q']),
        'networks': sorted(n['Name'] for n in inspect_many('network',
            ids(['docker', 'network', 'ls', '-q'])) if n['Name'] not in ('bridge', 'host', 'none')),
        'images': ids(['docker', 'image', 'ls', '-aq', '--no-trunc']),
        'build_cache': 'TODO (incluindo caches de build em /var/lib/docker)',
        'foreign': [], 'external': [],
    }


def validate_complete_target():
    endpoint = os.environ.get('DOCKER_HOST')
    if not endpoint:
        endpoint = output(['docker', 'context', 'inspect', '--format', '{{.Endpoints.docker.Host}}'])
    if endpoint != 'unix:///var/run/docker.sock':
        raise ValueError('Remoção completa exige o Docker local em /var/run/docker.sock.')
    if os.environ.get('DOCKER_CONTEXT'):
        raise ValueError('Remova DOCKER_CONTEXT antes da remoção completa do Docker local.')
    for folder in ('/var/lib/docker', '/var/lib/containerd'):
        path = Path(folder)
        if path.resolve() != path or path.is_mount():
            raise ValueError('Diretório de dados é link ou ponto de montagem: ' + folder)


def ensure_unmounted(path):
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        mount = Path(line.split()[4].replace('\\040', ' '))
        if mount == path or mount.is_relative_to(path):
            raise ValueError('Ainda há montagem ativa em ' + str(path) + '; limpeza interrompida.')


def remove_empty_parent(project):
    # Limitar a limpeza ao pai imediato; nunca subir até /opt.
    parent = project.parent
    if parent == Path('/opt') or not parent.is_relative_to('/opt'):
        return
    if parent.is_symlink() or parent.resolve() != parent or parent.is_mount():
        print('Pasta pai preservada (link simbólico ou ponto de montagem): ' + str(parent))
        return
    try:
        parent.rmdir()
    except FileNotFoundError:
        pass
    except OSError as exc:
        print('Pasta pai preservada (não vazia ou remoção não permitida): ' + str(parent)
              + f' [errno={exc.errno}]')
    else:
        print('Pasta pai vazia removida: ' + str(parent))


def validate_containerd_namespaces(namespaces):
    unknown = sorted(set(namespaces) - {'moby', 'moby_history'})
    if unknown:
        raise ValueError('Containerd possui namespaces não reconhecidos como Docker: '
                         + ', '.join(unknown) + '; remoção global bloqueada.')


def uninstall(c, remove_docker=False, preview=False, completely=False):
    remove_docker = remove_docker or completely
    if os.geteuid() != 0:
        raise ValueError('Execute com sudo/root')
    import re
    if not re.fullmatch(r'[a-z][a-z0-9_]{2,39}', c['PROJECT_NAME']):
        raise ValueError('PROJECT_NAME inválido')
    raw = Path(c['INSTALL_DIR'])
    project = raw.resolve()
    if not raw.is_absolute() or '..' in raw.parts or project != raw or not str(project).startswith('/opt/') or len(project.parts) < 4:
        raise ValueError('Diretório inválido ou contendo links simbólicos; remoção bloqueada.')
    if Path.cwd().resolve().is_relative_to(project) or Path(__file__).resolve().is_relative_to(project):
        raise ValueError('Execute o pacote do instalador fora do diretório que será removido.')
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        mount = Path(line.split()[4].replace('\\040', ' '))
        if mount == project or mount.is_relative_to(project):
            raise ValueError('Há um ponto de montagem no diretório do projeto; remoção bloqueada.')
    marker = project / '.installer-state.json'
    if not (completely and not project.exists()) and (not marker.is_file() or json.loads(marker.read_text()).get('fingerprint') != fingerprint(c)):
        raise ValueError('Instalação não identificada ou env diferente do original; remoção bloqueada.')
    os.umask(0o077)
    with open('/run/geonode-installer.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if completely:
            validate_complete_target()
        if remove_docker:
            info = json.loads(output(['docker', 'info', '--format', '{{json .}}']))
            if info.get('DockerRootDir') != '/var/lib/docker' or info.get('Swarm', {}).get('LocalNodeState') not in (None, 'inactive'):
                raise ValueError('Docker com armazenamento personalizado ou Swarm; remoção global bloqueada.')
            if shutil.which('ctr'):
                namespaces = output(['ctr','namespaces','list','-q']).split()
                validate_containerd_namespaces(namespaces)
        get_inventory = global_inventory if completely else inventory
        plan = get_inventory(project)
        if completely:
            print('ATENÇÃO: TODOS os recursos do Docker local serão apagados, inclusive outros projetos.')
        print('REMOÇÃO DEFINITIVA: ' + c['PROJECT_NAME'])
        print('Diretório: ' + str(project))
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        print('Remove também cron, auxiliar, checksum e logs do updatelayers deste projeto.')
        print('Pasta pai: ' + str(project.parent) + ' (remover somente se vazia; /opt sempre preservado).')
        print('Docker: ' + ('remover pacotes e dados globais' if remove_docker else 'preservar'))
        if remove_docker and (plan['foreign'] or plan['external']):
            raise ValueError('Remoção do Docker bloqueada: existem recursos externos ou de outros projetos. Use sem --remove-docker.')
        if preview:
            print('Prévia concluída. Nenhum recurso alterado.')
            return
        expected = 'APAGAR TODO O DOCKER' if completely else c['PROJECT_NAME']
        prompt = 'Digite APAGAR TODO O DOCKER para confirmar: ' if completely else 'Digite o nome do projeto para confirmar a perda dos dados: '
        if input(prompt).strip() != expected:
            raise ValueError('Confirmação não corresponde; nenhuma alteração feita.')
        # Revalidar inventário após a confirmação, antes de modificar o host.
        if get_inventory(project) != plan:
            raise ValueError('Inventário mudou durante a confirmação; execute novamente.')
        name = 'geonode-updatelayers-' + c['PROJECT_NAME']
        cron = Path('/etc/cron.d') / name
        cron.unlink(missing_ok=True)
        state = Path('/var/lib') / name
        state.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Esperar a execução em curso encerrar antes de remover containers.
        with (state / 'lock').open('w') as task_lock:
            print('Aguardando eventual updatelayers em execução...', flush=True)
            fcntl.flock(task_lock, fcntl.LOCK_EX)
            for container in plan['containers']:
                run(['docker', 'container', 'rm', '-f', container])
            for volume in plan['volumes']:
                run(['docker', 'volume', 'rm', volume])
            for network in plan['networks']:
                run(['docker', 'network', 'rm', network])
            if completely:
                run(['docker', 'image', 'prune', '--all', '--force'])
                run(['docker', 'builder', 'prune', '--all', '--force'])
            for folder in (Path('/usr/local/lib') / name, state):
                if folder.is_symlink():
                    raise ValueError('Diretório auxiliar é link simbólico; limpeza interrompida.')
                if folder.exists():
                    shutil.rmtree(folder)
            for path in [Path('/etc/logrotate.d') / name, *Path('/var/log').glob(name + '.log*')]:
                path.unlink(missing_ok=True)
            if project.exists():
                shutil.rmtree(project)
        if remove_docker:
            # Não fazer autoremove: dependências podem ser usadas por outros programas.
            run(['systemctl', 'stop', 'docker.service', 'docker.socket', 'containerd.service'])
            packages = ['docker-ce','docker-ce-cli','docker-ce-rootless-extras','docker-buildx-plugin','docker-compose-plugin','containerd.io']
            installed = [p for p in packages if subprocess.run(['dpkg-query','-W','-f=${Status}',p], capture_output=True,text=True).stdout == 'install ok installed']
            if installed:
                run(['apt-get','purge','-y',*installed])
            for folder in ('/var/lib/docker','/var/lib/containerd'):
                path=Path(folder)
                if path.is_symlink():
                    raise ValueError('Diretório Docker é link simbólico; limpeza interrompida.')
                if path.exists():
                    ensure_unmounted(path)
                    shutil.rmtree(path)
            Path('/etc/apt/sources.list.d/docker.list').unlink(missing_ok=True)
            Path('/etc/apt/keyrings/docker.asc').unlink(missing_ok=True)
        remove_empty_parent(project)
        print('Desinstalação concluída. Usuário do sistema e dependências gerais preservados.')
