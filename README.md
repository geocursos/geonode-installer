# GeoNode Installer

Instalador automatizado do GeoNode com Docker, configuração por arquivo `.env`, HTTPS opcional e ferramentas para manutenção de ambientes de cursos e testes.

**Desenvolvido pela Geocursos.** Documentação em português referente ao instalador **0.1.11**, com configuração padrão para **GeoNode 5.1.0**.

O objetivo é reduzir a preparação repetitiva de uma VM: preencher os parâmetros, validar a configuração e executar um comando. O instalador configura uma máquina já existente; não provisiona servidores, DNS ou firewall no provedor.

> **Antes de começar:** utilize uma máquina nova com Ubuntu 24.04 x86_64. As opções de desinstalação apagam dados definitivamente. O modo completo remove também recursos Docker de outros projetos.

## Índice

1. [Funcionalidades](#1-funcionalidades)
2. [Requisitos e limites](#2-requisitos-e-limites)
3. [Arquivos do projeto](#3-arquivos-do-projeto)
4. [Instalação rápida](#4-instalação-rápida)
5. [Referência dos parâmetros](#5-referência-dos-parâmetros)
6. [Cenários de configuração](#6-cenários-de-configuração)
7. [Etapas da instalação](#7-etapas-da-instalação)
8. [Primeiro acesso](#8-primeiro-acesso)
9. [Operação e diagnóstico](#9-operação-e-diagnóstico)
10. [Atualização automática de camadas](#10-atualização-automática-de-camadas)
11. [Retomada e alterações de configuração](#11-retomada-e-alterações-de-configuração)
12. [Desinstalação](#12-desinstalação)
13. [Referência dos comandos](#13-referência-dos-comandos)
14. [Solução de problemas](#14-solução-de-problemas)
15. [Segredos, permissões e publicação](#15-segredos-permissões-e-publicação)
16. [Validação e limitações conhecidas](#16-validação-e-limitações-conhecidas)
17. [Histórico das versões](#17-histórico-das-versões)
18. [Contribuições, autoria e referências](#18-contribuições-autoria-e-referências)

## 1. Funcionalidades

- Instala dependências do sistema e, quando o executável Docker não existe, Docker CE e plugins Compose/Buildx.
- Cria ou reutiliza um usuário dedicado compatível para os arquivos da aplicação.
- Obtém uma referência do `geonode-project` oficial e gera o projeto Django.
- Gera senhas aleatórias e o `.env` da aplicação.
- Configura domínio, IP ou `localhost`, com HTTP ou HTTPS.
- Habilita a emissão/renovação de certificado pelo mecanismo Let’s Encrypt do projeto Docker quando solicitado.
- Ajusta heap do GeoServer, processos uWSGI e concorrência Celery.
- Ajusta cookies de sessão e CSRF para HTTP/HTTPS.
- Constrói imagens, inicia containers e aguarda a disponibilidade dos serviços.
- Configura uma tarefa opcional de `updatelayers`, com intervalo definido no `.env`.
- Oferece prévia de desinstalação, remoção do projeto e limpeza completa de Docker em VM dedicada.

Não instala GeoNode manualmente no host, não oferece upgrade automático da aplicação e não cria uma VM na Hetzner ou em outro provedor.

## 2. Requisitos e limites

| Item | Requisito ou comportamento |
| --- | --- |
| Sistema | Ubuntu **24.04**, arquitetura **x86_64**, com systemd/APT |
| Administração | Usuário com `sudo`, ou root |
| Python inicial | Python 3 disponível para executar o instalador |
| Perfil padrão | VM de aproximadamente **16 GB de RAM** |
| RAM mínima validada | **14 GiB**, configurável com `MIN_RAM_GB` |
| Espaço livre validado | **30 GiB** no filesystem de destino, configurável com `MIN_DISK_GB` |
| Internet | Acesso aos repositórios Ubuntu/Docker, GitHub, PyPI e registros de imagens |
| HTTP | Acesso à porta TCP 80 pelo endereço configurado |
| HTTPS | Domínio apontando para a VM e portas TCP 80/443 acessíveis para emissão e uso do certificado |
| Diretório | Subdiretório de `/opt`, como `/opt/geonode/curso_geonode` |

Os mínimos de RAM/disco são verificações configuráveis, não uma garantia de desempenho nem o tamanho fixo da instalação. O consumo varia conforme imagens, cache de build, dados, logs e usuários simultâneos.

A RAM é medida pelo total reportado em `/proc/meminfo`, não pela memória livre no instante. Embora os nomes dos parâmetros usem `GB`, os cálculos usam **GiB**. `df -h` arredonda, podendo mostrar `30G` para um espaço exato menor que 30 GiB.

A checagem de disco usa o filesystem do diretório pai de `INSTALL_DIR`. Se o Docker armazenar imagens em outro filesystem, confira esse espaço separadamente. O instalador não cria swap automaticamente.

Não conte apenas com esta automação para preparar uma produção: backup, monitoramento, capacidade e validação dos fluxos precisam ser organizados para o ambiente real.

## 3. Arquivos do projeto

| Arquivo | Função |
| --- | --- |
| `instalar-geonode.sh` | Entrada Bash; exige root e chama o instalador Python |
| `instalar.py` | Validação, geração, implantação e configuração da tarefa agendada |
| `desinstalar.py` | Implementação das opções de remoção |
| `updatelayers.py` | Comparação do workspace e execução de `manage.py updatelayers` |
| `geonode-install.env` | Parâmetros de entrada; não contém as senhas geradas da aplicação |
| `LEIA-ME.md` | Instruções distribuídas nos pacotes anteriores |
| `README.md` | Esta documentação para o repositório |

Mantenha os arquivos Python juntos. O instalador importa o módulo de desinstalação e copia o auxiliar de atualização a partir de sua própria pasta.

## 4. Instalação rápida

### 4.1. Obter os arquivos

Baixe o pacote da versão desejada, transfira para a VM e descompacte:

```bash
sudo apt-get update
sudo apt-get install -y unzip
unzip geonode-installer-0.1.11.zip
cd geonode-installer-0.1.11
```

Se utilizar um checkout do repositório com os scripts na raiz, entre nessa raiz. Os comandos seguintes são iguais. Prefira uma versão publicada em vez de acompanhar alterações não versionadas durante um curso.

### 4.2. Configurar

```bash
nano geonode-install.env
```

Preencha `HOSTNAME`, o modo HTTPS e os demais parâmetros apropriados à VM. Veja exemplos na seção 6.

### 4.3. Validar

```bash
python3 instalar.py --env geonode-install.env --check
```

Valida chaves, formatos e resolução do endereço. Quando informado, compara `SERVER_IPV4` com os endereços resolvidos.

**Não instala pacotes e não testa portas, acesso externo, recursos reais da máquina, login ou emissão de certificado.** A verificação de sistema operacional e a comparação de RAM/disco ocorrem na execução da instalação.

### 4.4. Executar

```bash
sudo bash instalar-geonode.sh --env geonode-install.env
```

Mantenha a sessão aberta e acompanhe a saída. Alternativamente, execute dentro de uma sessão persistente de terminal preparada previamente.

O Bash muda para sua própria pasta antes de chamar o Python. Para um arquivo de parâmetros fora dessa pasta, use o caminho absoluto em `--env`.

## 5. Referência dos parâmetros

Exemplo completo, com os valores padrão do pacote:

```dotenv
GEONODE_PROJECT_REF=5.1.0
GEONODE_VERSION=5.1.0
DJANGO_BOOTSTRAP_VERSION=5.2
SYSTEM_USER=geonode
PROJECT_NAME=curso_geonode
INSTALL_DIR=/opt/geonode/curso_geonode
HOSTNAME=geonode.seudominio.com.br
ENABLE_HTTPS=true
LETSENCRYPT_EMAIL=contato@seudominio.com.br
SERVER_IPV4=
GEOSERVER_XMS=2G
GEOSERVER_XMX=4G
UWSGI_PROCESSES=4
CELERY_WORKERS=2
WAIT_SECONDS=1800
UPDATE_LAYERS_ENABLED=true
UPDATE_LAYERS_INTERVAL_HOURS=1
MIN_RAM_GB=14
MIN_DISK_GB=30
```

Os domínios de exemplo precisam ser substituídos. Os placeholders `seudominio` são rejeitados.

| Parâmetro | Descrição e valores aceitos |
| --- | --- |
| `GEONODE_PROJECT_REF` | Referência usada no clone do template: branch ou tag válida. O padrão é `5.1.0`. Não é um campo genérico para qualquer SHA; o clone usa `--branch`. |
| `GEONODE_VERSION` | Versão numérica aplicada à dependência GeoNode e à imagem base. Padrão `5.1.0`. |
| `DJANGO_BOOTSTRAP_VERSION` | Django instalado no ambiente temporário para gerar o projeto. Padrão `5.2`. Não determina o Django que executa dentro dos containers. |
| `SYSTEM_USER` | Usuário do host para os arquivos. Começa com letra minúscula; aceita letras minúsculas, números, `_` e `-`; até 31 caracteres. `root` não é aceito. |
| `PROJECT_NAME` | Nome passado à geração do projeto. Entre 3 e 40 caracteres; começa com letra minúscula; demais caracteres: letras minúsculas, números e `_`. |
| `INSTALL_DIR` | Diretório absoluto abaixo de `/opt`, com pelo menos um diretório intermediário. Exemplo: `/opt/geonode/curso_geonode`. |
| `HOSTNAME` | Domínio, IPv4 ou `localhost`, sem protocolo, porta ou barra. HTTPS exige domínio. O validador atual não aceita IPv6 literal. |
| `ENABLE_HTTPS` | Exatamente `true` ou `false`, em minúsculas. |
| `LETSENCRYPT_EMAIL` | E-mail para o certificado; obrigatório em HTTPS. Pode ficar vazio em HTTP. |
| `SERVER_IPV4` | Opcional. IPv4 que deve aparecer na resolução de `HOSTNAME`. Não define o endereço público da aplicação; essa função é de `HOSTNAME`. |
| `GEOSERVER_XMS` | Heap inicial Java, como `512M` ou `2G`; inteiro positivo com `M` ou `G` maiúsculo. |
| `GEOSERVER_XMX` | Heap máximo Java, como `1G` ou `4G`; não pode ser menor que XMS. |
| `UWSGI_PROCESSES` | Inteiro positivo; fixa o número de processos e remove o autoscaling `cheaper` do template. |
| `CELERY_WORKERS` | Inteiro positivo usado na concorrência/autoscaling do worker principal. A concorrência do harvester é configurada separadamente como 1 pelo instalador. |
| `WAIT_SECONDS` | Inteiro positivo; prazo da verificação final após iniciar os containers. Padrão 1800 segundos. Não limita o tempo do build. |
| `UPDATE_LAYERS_ENABLED` | `true` habilita a tarefa; `false` não cria ou remove seu agendamento. Padrão `true`. |
| `UPDATE_LAYERS_INTERVAL_HOURS` | Uma das opções: `1`, `2`, `3`, `4`, `6`, `8`, `12`, `24`. Padrão 1. |
| `MIN_RAM_GB` | Número não negativo; aceita decimal com ponto. Padrão 14. `0` desativa a checagem. |
| `MIN_DISK_GB` | Número não negativo; aceita decimal com ponto. Padrão 30. `0` desativa a checagem. |

Os quatro últimos parâmetros são opcionais em arquivos antigos; o instalador preenche seus padrões. As demais chaves são obrigatórias, mesmo quando o valor permitido é vazio.

### Formato do arquivo

- Use uma linha `CHAVE=valor` por parâmetro.
- Não adicione chaves arbitrárias: nomes desconhecidos e duplicados são rejeitados.
- Comentários devem ocupar uma linha iniciada por `#`.
- Não coloque comentários após o valor na mesma linha.
- Não utilize `export`, substituição de variáveis ou comandos shell: o arquivo é lido como texto, não executado.
- Para decimais, use ponto, não vírgula.

## 6. Cenários de configuração

### 6.1. Domínio com HTTPS

```dotenv
HOSTNAME=geo.exemplo.com.br
ENABLE_HTTPS=true
LETSENCRYPT_EMAIL=administrador@exemplo.com.br
SERVER_IPV4=
```

Configure o DNS antes de executar e libere TCP 80/443. Se usar `SERVER_IPV4`, preencha com o IPv4 público correto. Havendo registro IPv6 no DNS, ele também precisa encaminhar corretamente para a instância.

O projeto Docker fornece o mecanismo de certificados; não é necessário instalar Certbot separadamente no host. O endereço final é `https://geo.exemplo.com.br/`.

### 6.2. VM na rede interna, por IP e sem SSL

```dotenv
HOSTNAME=192.168.186.142
ENABLE_HTTPS=false
LETSENCRYPT_EMAIL=
SERVER_IPV4=
```

Acesso: `http://192.168.186.142/`. Use IP fixo ou reserva DHCP e permita TCP 80 entre o navegador e a VM. Configure o IP real da sua rede.

### 6.3. Localhost

```dotenv
HOSTNAME=localhost
ENABLE_HTTPS=false
LETSENCRYPT_EMAIL=
SERVER_IPV4=
```

Acesso: `http://localhost/`, a partir da própria máquina. Para abrir de outro computador, use o IP/domínio da VM desde a configuração inicial.

### 6.4. Perfil reduzido para laboratório

Exemplo inicial para uma VM de testes com cerca de 8 GB de RAM:

```dotenv
MIN_RAM_GB=7
MIN_DISK_GB=20
GEOSERVER_XMS=512M
GEOSERVER_XMX=1G
UWSGI_PROCESSES=2
CELERY_WORKERS=1
```

A adequação depende dos dados e exercícios. Desabilitar os mínimos é possível:

```dotenv
MIN_RAM_GB=0
MIN_DISK_GB=0
```

Isso não reduz o consumo nem evita falta de recursos. O instalador mantém os outros valores até você alterá-los.

### 6.5. Cookies e Let’s Encrypt em HTTP

Na geração do `.env` da aplicação:

| Modo | `CSRF_COOKIE_SECURE` | `SESSION_COOKIE_SECURE` |
| --- | --- | --- |
| HTTP | `False` | `False` |
| HTTPS | `True` | `True` |

A proteção CSRF continua ativa. O ajuste permite enviar cookies em HTTP no laboratório e exige HTTPS quando esse modo está habilitado.

Em HTTP, a emissão Let’s Encrypt fica desativada e seu container é dispensado da verificação final. **O serviço continua definido no Compose e pode aparecer reiniciando com código 0**; a versão 0.1.11 não o remove nem o coloca automaticamente em um profile inativo. O proxy também mantém os mapeamentos do Compose; desativar HTTPS não é uma regra de firewall para a porta 443.

## 7. Etapas da instalação

1. Lê e valida o arquivo de parâmetros e resolve o endereço.
2. Verifica Ubuntu/arquitetura, permissões, identificação prévia, RAM e disco.
3. Instala dependências e, se necessário, Docker CE/Compose/Buildx; habilita o serviço Docker.
4. Cria/reutiliza o usuário dedicado e prepara os diretórios.
5. Clona a referência do template e registra seu commit.
6. Cria um ambiente Python temporário com o Django de bootstrap.
7. Gera a aplicação, segredos e arquivos de configuração.
8. Ajusta os serviços, atribui os arquivos ao usuário dedicado e grava `.installer-state.json`.
9. Valida o Compose, constrói imagens e inicia containers.
10. Aguarda a resposta web e os estados esperados.
11. Configura o agendamento opcional de atualização de camadas.

### Usuário e permissões

O usuário novo é criado sem senha de login habilitada, sem concessão de sudo e sem inclusão no grupo Docker. Se já existir, precisa ter UID >= 1000, home `/home/NOME` e shell `/bin/bash`. O instalador não redefine permissões, senha ou grupos preexistentes desse usuário.

Download e geração são executados como `SYSTEM_USER`; pacotes e comandos Docker, como root. Isso não determina os usuários dos processos internos de cada imagem.

### Verificação de prontidão

| Serviço Compose | Condição para concluir |
| --- | --- |
| `django`, `geoserver`, `db` | `running` e `healthy` |
| `celery`, `redis`, `geonode` (proxy) | `running` |
| `letsencrypt` | `running`, somente se HTTPS estiver habilitado |
| Endereço web | `curl` retorna sucesso; em HTTPS, sem ignorar a validação do certificado |

O instalador informa os componentes pendentes a cada tentativa. A página inicial abrir antes do fim não significa que GeoServer e os demais componentes já estejam prontos.

A consulta web é feita localmente, direcionando o host configurado para loopback e ignorando proxies do ambiente. Não substitui um teste externo de DNS/firewall.

## 8. Primeiro acesso

Usuário inicial: **`admin`**. Para consultar a senha, ajustando o caminho se necessário:

```bash
sudo awk -F= '/^ADMIN_PASSWORD=/{print $2}' \
  /opt/geonode/curso_geonode/.env
```

Há dois arquivos diferentes:

| Arquivo | Conteúdo |
| --- | --- |
| `geonode-install.env` | Entradas para a automação |
| `/opt/geonode/curso_geonode/.env` | Configuração efetiva e senhas dos serviços |

Não publique o `.env` da aplicação. Faça login e valide upload, visualização de camada, mapa, dashboard e permissões antes da aula ou entrega.

## 9. Operação e diagnóstico

Use caminhos explícitos se o usuário do terminal não puder entrar na pasta da aplicação:

```bash
sudo docker compose \
  --project-directory /opt/geonode/curso_geonode \
  --env-file /opt/geonode/curso_geonode/.env \
  -f /opt/geonode/curso_geonode/docker-compose.yml \
  ps -a
```

Logs:

```bash
sudo docker compose \
  --project-directory /opt/geonode/curso_geonode \
  --env-file /opt/geonode/curso_geonode/.env \
  -f /opt/geonode/curso_geonode/docker-compose.yml \
  logs --tail=100 django geoserver celery geonode letsencrypt
```

Recursos e disco:

```bash
sudo docker stats
df -h
sudo docker system df
```

Os nomes reais dos containers podem diferir de `PROJECT_NAME`. Os comandos usam os **serviços Compose**. Em particular, `geonode` nesse Compose identifica o proxy; `django` identifica a aplicação.

O GeoServer é publicado no host em `127.0.0.1:8080`, mantendo acesso interno pelo proxy. Para uso pelo navegador, utilize o endereço público configurado e a rota disponibilizada pelo portal.

## 10. Atualização automática de camadas

### 10.1. Quando usar

A tarefa é útil principalmente para camadas publicadas **diretamente no GeoServer**, inclusive a partir de um banco PostGIS externo, que precisam ser incorporadas ou ter suas informações atualizadas no catálogo GeoNode.

Camadas enviadas e gerenciadas pelo próprio GeoNode já seguem seu fluxo integrado e não dependem dessa tarefa adicional.

A automação não atualiza registros do banco. O GeoServer consulta os dados na fonte configurada; `updatelayers` atua na integração com o catálogo. Revise também o resultado e as permissões das camadas importadas.

### 10.2. Configuração e funcionamento

```dotenv
UPDATE_LAYERS_ENABLED=true
UPDATE_LAYERS_INTERVAL_HOURS=6
```

O cron executa às 00h, 06h, 12h e 18h, no fuso do servidor. É um agendamento de relógio, não um contador iniciado no momento da instalação. Para 24 horas, executa diariamente à meia-noite.

A tarefa:

1. Obtém um lock para evitar sobreposição.
2. Consulta o conteúdo dos arquivos em `/geoserver_data/data/workspaces/geonode` dentro do GeoServer.
3. Calcula um checksum com os nomes/conteúdos, usando `find`/`sha256sum` no container e `hashlib` no host.
4. Executa `python3 manage.py updatelayers` no serviço `django` na primeira execução ou quando o checksum muda.
5. Salva o checksum somente após sucesso; em falha, permite nova tentativa no próximo horário.

Não instala `checksumdir` dentro do container. O auxiliar e o estado ficam no host, sobrevivendo à recriação dos containers.

**Limites:** monitora somente esse workspace. Alterações apenas em linhas PostGIS, dados externos ou outros workspaces não disparam a tarefa. Workspace vazio ou ausente resulta em erro e preserva o checksum anterior. O comando `updatelayers` é executado sem filtro adicional; não promete atualização de todo tipo de metadado ou conteúdo.

### 10.3. Arquivos e logs

Para `PROJECT_NAME=curso_geonode`:

| Caminho | Uso |
| --- | --- |
| `/etc/cron.d/geonode-updatelayers-curso_geonode` | Agendamento root |
| `/usr/local/lib/geonode-updatelayers-curso_geonode/updatelayers.py` | Auxiliar |
| `/usr/local/lib/geonode-updatelayers-curso_geonode/config.json` | Caminhos e executável Docker |
| `/var/lib/geonode-updatelayers-curso_geonode/checksum.sha256` | Último checksum concluído |
| `/var/lib/geonode-updatelayers-curso_geonode/lock` | Lock da tarefa |
| `/var/log/geonode-updatelayers-curso_geonode.log` | Saída das execuções |
| `/etc/logrotate.d/geonode-updatelayers-curso_geonode` | Rotação semanal, quatro arquivos anteriores |

Alterar o horário diretamente:

```bash
sudo nano /etc/cron.d/geonode-updatelayers-curso_geonode
```

Exemplos: `0 * * * *` para uma hora; `0 */6 * * *` para seis horas. Mantenha `root` e o restante do comando na linha. Uma configuração posterior pelo instalador sobrescreve esse horário com o valor do `.env`.

Logs:

```bash
sudo tail -n 100 /var/log/geonode-updatelayers-curso_geonode.log
```

### 10.4. Configurar em instalação existente

Na pasta do pacote, usando os parâmetros originais da instância:

```bash
sudo python3 instalar.py --env geonode-install.env --configure-updatelayers
```

Não reconstrói imagens nem reinicia a aplicação. Ainda valida configuração/DNS, sistema e identificação da instalação, mas não executa as checagens de RAM/disco da implantação.

Para desativar, defina `UPDATE_LAYERS_ENABLED=false` e repita o comando. Remove apenas o agendamento; auxiliar, estado e logs permanecem até a desinstalação. Uma execução já iniciada não é cancelada.

Executar manualmente:

```bash
sudo python3 \
  /usr/local/lib/geonode-updatelayers-curso_geonode/updatelayers.py \
  /usr/local/lib/geonode-updatelayers-curso_geonode/config.json
```

## 11. Retomada e alterações de configuração

Se a execução falhar ou for interrompida, os containers iniciados continuam independentes do processo do instalador. O `Ctrl+C` encerra com código 130; não remove volumes.

Para tentar novamente, execute o comando de instalação com o mesmo arquivo de parâmetros. Se o projeto já foi gerado, o instalador o reconhece por `.installer-state.json`; não gera novas senhas. A execução normal, entretanto, volta a instalar/verificar pacotes, construir imagens e executar `compose up`.

O registro armazena uma assinatura dos parâmetros. Alterar versão, nome, hostname, usuário, diretório ou dimensionamento de serviços invalida a retomada. Os quatro campos abaixo são excluídos dessa assinatura e podem mudar:

- `MIN_RAM_GB`;
- `MIN_DISK_GB`;
- `UPDATE_LAYERS_ENABLED`;
- `UPDATE_LAYERS_INTERVAL_HOURS`.

Editar somente `geonode-install.env` **não reconfigura** uma aplicação existente. Não há migração automática de HTTP para HTTPS, alteração de hostname, atualização de versão nem reaplicação automática de correções de versões novas em projetos já gerados.

Se a interrupção ocorrer antes da etapa final, o agendamento de camadas pode não ter sido criado. Use a opção específica após confirmar que a instância está operacional.

Não edite o registro de identificação para contornar diferenças. Para atualização de uma instância com dados, planeje um procedimento separado com backup e testes.

## 12. Desinstalação

> **Perda definitiva de dados:** não há backup automático nem rollback. Execute a partir da pasta do instalador, fora de `INSTALL_DIR`, e use os parâmetros originais. Não faça outras operações Docker durante a remoção.

### 12.1. Comparação dos modos

| Modo | Projeto/dados | Imagens/cache | Docker | Outros projetos |
| --- | --- | --- | --- | --- |
| `--uninstall-geonode` | Remove recursos identificados e pasta | Preserva | Preserva | Preserva; dependências compartilhadas podem bloquear |
| `--uninstall-geonode --remove-docker` | Remove | Remove dados globais após verificar exclusividade | Purga pacotes | Bloqueia ao detectar recursos alheios/externos |
| `--uninstall-geonode-completely` | Remove instalação identificada e todos os recursos Docker locais | Remove globalmente | Purga pacotes | **Apaga recursos Docker de outros projetos também** |

### 12.2. Somente o GeoNode

Prévia:

```bash
sudo python3 instalar.py --env geonode-install.env \
  --uninstall-geonode --preview
```

Executar:

```bash
sudo python3 instalar.py --env geonode-install.env \
  --uninstall-geonode
```

Confirmação: digite o valor de `PROJECT_NAME`.

Remove containers, redes e volumes identificados pelas labels Compose, a pasta da aplicação e cron/auxiliar/checksum/logs/logrotate do seu `updatelayers`. Aguarda eventual tarefa em execução antes de remover os containers.

Recursos externos declarados no Compose não são apagados nesse modo. Bind mounts fora da aplicação permanecem. Imagens/cache preservados podem tornar a reinstalação mais rápida mesmo com banco e dados recriados.

A pasta pai imediata de `INSTALL_DIR` é removida apenas se vazia; `/opt` nunca é removida. Não sobe apagando outros ancestrais. A pasta vazia pode ser removida mesmo que já existisse antes da instalação: as versões antigas não registram sua origem. Links simbólicos e pontos de montagem são preservados.

### 12.3. Remover também Docker com verificação de exclusividade

```bash
sudo python3 instalar.py --env geonode-install.env \
  --uninstall-geonode --remove-docker
```

Bloqueia se houver containers de outros projetos (inclusive parados), volumes, redes personalizadas, imagens não associadas ou recursos externos. Imagens antigas/base podem provocar bloqueio conservador. A verificação inicial ocorre antes da exclusão do projeto.

### 12.4. Limpeza completa da VM de laboratório

Prévia:

```bash
sudo python3 instalar.py --env geonode-install.env \
  --uninstall-geonode-completely --preview
```

Executar:

```bash
sudo python3 instalar.py --env geonode-install.env \
  --uninstall-geonode-completely
```

Confirmação obrigatória:

```text
APAGAR TODO O DOCKER
```

Apaga todos os containers, volumes, redes personalizadas, imagens e caches Docker locais, inclusive os que não pertencem ao GeoNode. Depois para os serviços, purga os pacotes Docker CE/containerd.io instalados, remove os dados padrão e o repositório/chave APT usados pelo instalador.

O inventário é revalidado após a confirmação. Este modo não deve ser combinado com `--uninstall-geonode` nem `--remove-docker`.

Se `INSTALL_DIR` já não existe, o modo completo ainda pode limpar Docker e os auxiliares identificados pelo `.env`. Se a pasta existe, exige o registro do instalador e parâmetros compatíveis: não apaga pastas existentes sem identificação.

### 12.5. Proteções que continuam ativas

A remoção de Docker é destinada ao Docker CE local padrão. Continua bloqueada para armazenamento fora de `/var/lib/docker`, Swarm ativo e namespaces containerd desconhecidos.

São reconhecidos **`moby` e `moby_history`**. Outros nomes são apresentados no erro. No modo completo, exige socket `unix:///var/run/docker.sock`, rejeita `DOCKER_CONTEXT` explícito e verifica caminhos de dados. Montagens ativas após parar os serviços interrompem a limpeza desses diretórios.

Não cobre Docker rootless, Desktop, Snap nem outros runtimes. Se houver falha intermediária, parte dos recursos pode já ter sido removida; não há transação nem restauração automática.

### 12.6. O que permanece

- Usuário `SYSTEM_USER` e seu home.
- Dependências gerais, incluindo Python, Git, cron e logrotate.
- Pacote e arquivo de parâmetros fora de `INSTALL_DIR`.
- Configurações personalizadas em `/etc/docker` e credenciais em `~/.docker`.
- Arquivos de bind mounts fora da pasta removida.
- Crontabs manuais antigos e tarefas de outros projetos.
- Caches de builders remotos.

A limpeza não restaura a VM ao estado original do sistema operacional. Para garantir esse estado, recrie a VM.

### 12.7. Reinstalar

Após concluir a remoção:

```bash
sudo bash instalar-geonode.sh --env geonode-install.env
```

Se o Docker foi removido, o instalador volta a instalá-lo. Uma nova geração cria novas senhas.

## 13. Referência dos comandos

| Opção | Uso |
| --- | --- |
| `--env CAMINHO` | Arquivo de parâmetros; padrão `geonode-install.env` |
| `--check` | Valida entradas e resolução sem instalar |
| `--configure-updatelayers` | Configura somente a tarefa em projeto existente |
| `--uninstall-geonode` | Desinstala o projeto identificado |
| `--remove-docker` | Modificador de `--uninstall-geonode`; exige exclusividade |
| `--uninstall-geonode-completely` | Limpeza global local, incluindo recursos de outros projetos |
| `--preview` | Prévia dos modos de desinstalação; não se aplica à instalação |
| `--help` | Mostra as opções disponíveis |

```bash
python3 instalar.py --help
```

Não combine desinstalação com `--check` ou `--configure-updatelayers`. Não há opção para suprimir as confirmações destrutivas.

## 14. Solução de problemas

### Permission denied ao entrar em /opt/geonode

A pasta pertence ao usuário dedicado e pode não permitir acesso direto ao usuário administrativo. Use os caminhos explícitos da seção 9 com `sudo`. Não torne os arquivos de segredos públicos para resolver esse acesso.

### No configuration file provided

O Compose foi chamado fora da pasta da aplicação. Utilize `--project-directory`, `--env-file` e `-f` como na seção 9.

### Bloqueio de memória ou disco

Ajuste `MIN_RAM_GB` ou `MIN_DISK_GB`. Para RAM/disco de laboratório, também revise heap e workers. `0` desativa somente a checagem correspondente.

### Configuração mudou

Use os parâmetros originais da instalação. Não basta apontar um novo `.env` para o mesmo diretório. Alterações dos quatro campos opcionais da seção 11 são permitidas.

### Portal abre, mas instalador continua esperando

Veja a mensagem `Ainda aguardando`. O GeoServer pode estar `starting` enquanto a página inicial já responde. O script aguarda as condições da seção 7 até `WAIT_SECONDS`.

### Let’s Encrypt reiniciando em HTTP

Na versão atual, pode ocorrer porque o serviço permanece definido no Compose com a emissão desativada. Não é exigido na prontidão HTTP. Consulte seus logs para distinguir esse caso de um problema em HTTPS.

### Login retorna 403 CSRF em HTTP

Em novas instalações 0.1.9+, ambos os cookies seguros são ajustados para `False` no modo HTTP. Confira os valores efetivos:

```bash
sudo docker compose \
  --project-directory /opt/geonode/curso_geonode \
  --env-file /opt/geonode/curso_geonode/.env \
  -f /opt/geonode/curso_geonode/docker-compose.yml \
  exec -T django python3 manage.py shell -c \
  'from django.conf import settings; print("SITEURL:", settings.SITEURL); print("CSRF_COOKIE_SECURE:", settings.CSRF_COOKIE_SECURE); print("SESSION_COOKIE_SECURE:", settings.SESSION_COOKIE_SECURE)'
```

Se uma instância antiga exigir correção, faça backup do `.env` da aplicação e ajuste `CSRF_COOKIE_SECURE=False` e `SESSION_COOKIE_SECURE=False` **somente quando o acesso for HTTP**. Em HTTPS, mantenha `True`. Recrie os serviços para carregar mudanças de ambiente:

```bash
sudo docker compose \
  --project-directory /opt/geonode/curso_geonode \
  --env-file /opt/geonode/curso_geonode/.env \
  -f /opt/geonode/curso_geonode/docker-compose.yml \
  up -d --no-deps --force-recreate django celery
```

Reabra a página de login em janela anônima. Não desative o middleware CSRF nem habilite DEBUG para contornar a falha.

### Containerd possui outros namespaces

```bash
sudo ctr namespaces list
```

A versão 0.1.11 aceita `moby` e `moby_history`. Se aparecer um nome diferente, investigue qual aplicação o utiliza antes de remover Docker/containerd. Não apague namespaces manualmente como atalho.

### Diretório já existe sem identificação

A pasta não contém o registro esperado. Escolha um destino novo ou investigue a instalação existente. O instalador não assume que uma pasta sem registro pode ser reutilizada/apagada.

### Reinstalação muito mais rápida

Sem remoção completa, imagens e caches permanecem e podem ser reutilizados. Isso não comprova retenção do banco. Confira se os volumes foram recriados e se os dados anteriores foram de fato removidos.

## 15. Segredos, permissões e publicação

O instalador gera segredos aleatórios, protege o `.env` da aplicação com modo `600` e não coloca essas senhas diretamente nos argumentos do gerador.

Antes de publicar no GitHub:

- Mantenha somente domínios/IPs de exemplo no arquivo de parâmetros distribuído.
- Não envie `.env` da aplicação, backups desse arquivo, senhas, tokens, logs com dados privados ou volumes.
- Publique os scripts e o exemplo de configuração, não o projeto instalado com seus segredos.
- Preserve os arquivos já publicados de cada versão; distribua correções em novas versões.
- Se desejar usar tags/releases no GitHub, mantenha a identificação do pacote alinhada à versão do código.

Esta documentação não atribui uma licença ao instalador. Defina um arquivo `LICENSE` antes de anunciar a licença do repositório; não presuma que a licença de outro projeto da Geocursos se aplica a este.

## 16. Validação e limitações conhecidas

Na evolução da ferramenta, foram relatadas instalações reais do GeoNode 5.1.0 com HTTPS e com HTTP por IP na rede interna. O ajuste manual dos cookies em HTTP teve o login confirmado pelo usuário.

A versão 0.1.11 foi verificada com sintaxe, validação de parâmetros e testes simulados dos fluxos de prontidão, atualização e remoção. **Não há confirmação nesta documentação de uma remoção completa real bem-sucedida com a versão 0.1.11.** Cada release deve ser validada em VM descartável antes de uso em aula/produção.

Limitações relevantes:

- Sistema/arquitetura fixados em Ubuntu 24.04 x86_64.
- Versões GeoNode/template/Django não são livremente intercambiáveis; referências diferentes podem exigir adaptação.
- Imagens auxiliares e pacotes seguem o template/repositórios; o instalador não fixa todos os componentes por digest ou versão exata.
- Se Docker já existir, não instala/repara automaticamente plugins ausentes.
- Apenas um projeto por destino; não há suporte garantido a múltiplas instâncias concorrentes na mesma VM. O Compose define seus próprios nomes e portas; não confunda `PROJECT_NAME` com `COMPOSE_PROJECT_NAME`.
- Não há upgrade automático, mudança automática de hostname nem reaplicação das novas correções em uma instância antiga.
- Sem backup/restore automatizado pelo instalador e sem rollback de desinstalação.
- Não há arquivo de log persistente geral próprio do instalador; a saída é no terminal. A tarefa `updatelayers` tem log e rotação específicos.
- O sucesso final não testa autenticação, upload, mapas, dashboards, permissões ou acesso externo.

## 17. Histórico das versões

| Versão | Alteração principal |
| --- | --- |
| 0.1.0 | Instalação inicial configurável, GeoNode 5.1.0 e HTTPS opcional |
| 0.1.1 | Usuário dedicado `SYSTEM_USER` |
| 0.1.2 | Correção da leitura do commit com o proprietário do clone Git |
| 0.1.3 | Agendamento de `updatelayers` e configuração isolada da tarefa |
| 0.1.4 | Desinstalação do projeto e remoção opcional protegida do Docker |
| 0.1.5 | RAM mínima configurável |
| 0.1.6 | Disco mínimo configurável |
| 0.1.7 | Prontidão HTTP/HTTPS corrigida, diagnóstico de pendências e Ctrl+C tratado |
| 0.1.8 | Limpeza condicional da pasta pai vazia |
| 0.1.9 | Cookies de sessão/CSRF conforme HTTP/HTTPS |
| 0.1.10 | Desinstalação completa global para VM de laboratório |
| 0.1.11 | Reconhecimento do namespace `moby_history` na remoção Docker |

## 18. Contribuições, autoria e referências

**Geocursos — Fernando Quadro.**

Para relatar um problema no repositório, informe versão do instalador, sistema/arquitetura, recursos da VM, modo HTTP/HTTPS, comando executado e trecho relevante da saída. Remova credenciais e dados privados. Não anexe o `.env` da aplicação.

Ao contribuir, descreva o comportamento antes/depois e os testes realizados. Para mudanças de remoção, teste primeiro em simulação e depois em VM descartável. Para configuração web, valide HTTP e HTTPS e o login, além da página inicial.

Referências e origem do procedimento:

- [Geocursos](https://geocursos.com.br/)
- [Blog do Fernando Quadro](https://www.fernandoquadro.com.br/)
- [GeoNode Project — repositório oficial](https://github.com/GeoNode/geonode-project)
- [GeoNode — repositório oficial](https://github.com/GeoNode/geonode)
- [Instalação do GeoNode 5 no Ubuntu 24.04](https://www.fernandoquadro.com.br/html/2026/02/17/instalacao-do-geonode-5-no-ubuntu-24-04/)
- [Instalação do certificado SSL no GeoNode](https://www.fernandoquadro.com.br/html/2025/06/23/instalacao-do-certificado-ssl-no-geonode/)
- [Atualizar camadas do GeoServer para o GeoNode automaticamente](https://www.fernandoquadro.com.br/html/2025/09/03/atualizar-camadas-do-geoserver-para-o-geonode-automaticamente/)

A automação de camadas adapta a ideia do tutorial, que credita a contribuição de Diego Varela. Esta implementação usa checksum SHA-256 sem instalar uma dependência Python no container GeoServer.
