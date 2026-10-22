# Instalador GeoNode 0.1.6

Automatiza GeoNode 5.1.0 em VM nova Ubuntu 24.04 x86_64 com Docker Compose v2. Perfil inicial: 16 GB RAM, GeoServer 2–4 GB de heap, uWSGI 4 processos fixos, Celery principal até 2 processos e harvesting até 1. Não cria a VM.

## Preparação

1. Crie um registro DNS A para o IPv4 público da VM. Se houver AAAA, ele também deve apontar para esta VM com IPv6 funcional; remova registros incorretos.
2. Libere TCP 80 e 443 no firewall da Hetzner e no sistema. Mantenha SSH acessível. O script não modifica firewalls. Saída para internet deve permitir DNS, GitHub, repositórios Ubuntu/Docker, PyPI, registries de imagens e Let's Encrypt.
3. Descompacte o ZIP na VM. Edite `geonode-install.env`: HOSTNAME, LETSENCRYPT_EMAIL e opcionalmente SERVER_IPV4. Não use https:// nem barra no hostname.

```bash
unzip geonode-installer-0.1.6.zip
cd geonode-installer-0.1.6
nano geonode-install.env
python3 instalar.py --env geonode-install.env --check
sudo bash instalar-geonode.sh --env geonode-install.env
```

O shell wrapper procura os arquivos na própria pasta. O modo `--check` valida parâmetros e resolução DNS, sem instalar pacotes; não comprova acesso externo às portas.

## HTTPS

Usa o container Let's Encrypt do projeto oficial, com `LETSENCRYPT_MODE=production` e as URLs HTTPS geradas pelo create-envfile.py. Não instala outro Certbot no host e não copia manualmente certificados. Os certificados ficam no volume persistente compartilhado entre Nginx e Let's Encrypt. Mantenha o serviço Let's Encrypt ativo e a porta 80 acessível para renovação. A checagem final exige certificado confiável, não usa curl -k. A verificação local não substitui abrir o endereço a partir de outro computador.

## Senhas e reexecução

O instalador gera senhas criptograficamente aleatórias e as grava em `/opt/geonode/curso_geonode/.env` (ou INSTALL_DIR), com modo 600 e pertencente a SYSTEM_USER (root também pode ler). Para obter a senha inicial:

```bash
sudo awk -F= '/^ADMIN_PASSWORD=/{print $2}' /opt/geonode/curso_geonode/.env
```

A conta inicial é admin. Não compartilhe o `.env` da aplicação nem logs com segredos. O arquivo de parâmetros entregue não contém senhas. Nenhum usuário é adicionado ao grupo Docker; administre Docker a partir de uma conta administrativa com sudo.

Pode reexecutar com o mesmo arquivo de parâmetros para retomar build/start/verificação. Diretório preexistente sem marcador é recusado. Parâmetros diferentes são recusados após geração do projeto. Não há upgrade automático, exclusão de volumes, reset de banco ou regeneração de senhas. Falha antes da publicação do diretório remove apenas o staging temporário; falha posterior preserva o projeto.

Não execute em uma VM que já hospede outro sistema ou use as mesmas portas. O Compose precisa estar disponível quando Docker já estiver instalado; o script para se não estiver. A instalação foi desenhada para VM nova.

## Diagnóstico

```bash
cd /opt/geonode/curso_geonode
sudo docker compose ps -a
sudo docker compose logs --tail=100 django geoserver celery geonode letsencrypt
sudo docker stats
```

O prazo de espera padrão é 1800 segundos após build/start. O build pode levar mais tempo e não está incluído nesse prazo. Uma falha na dependência saudável pode fazer `up -d` parar antes da verificação; consulte os logs e reexecute com o mesmo env. Não remova volumes para tentar corrigir.

Antes da aula, faça login externo, upload de vetor e raster representativos, abertura de camada, criação/salvamento de mapa e dashboard, download e teste concorrente. O teste final automático verifica HTTP/TLS, saúde de Django/GeoServer/PostGIS e presença dos serviços auxiliares; não valida todos os fluxos funcionais.

## Versões e limites

`GEONODE_PROJECT_REF` seleciona a referência no Git; `GEONODE_VERSION` fixa o pacote Python e a identificação da imagem local. Recomenda-se manter os dois iguais. `DJANGO_BOOTSTRAP_VERSION` serve somente para gerar o projeto, não controla o Django interno dos containers. Outras combinações exigem validação; esta entrega tem como alvo 5.1.0.

O commit do template é registrado em `.installer-state.json`. O projeto upstream ainda usa algumas imagens com tags mutáveis (`latest`/`alpine`): esta entrega não é um lock completo por digest. Dependências transitivas também podem variar. Reexecuções fazem build com cache, sem atualizar explicitamente as imagens-base. Alterações futuras no template podem exigir revisão dos ajustes de uWSGI/Compose.

Mantém o HTTPS e o agendamento de renovação do stack oficial. A porta publicada 8080 do GeoServer é limitada a 127.0.0.1; PostgreSQL permanece sem porta pública. Não cria swap, não configura SMTP nem backups. Para retenção após o curso, planeje backup dos dados e volumes.

## Validação desta entrega

Conferidos os arquivos reais da referência oficial 5.1.0 e o gerador de ambiente. Verificados sintaxe Bash/Python, geração do projeto e os ajustes aplicados. Não executado um deploy Docker completo nem emissão real de certificado neste ambiente. A primeira execução na VM é um teste de implantação.

Referências:
- https://github.com/GeoNode/geonode-project/tree/5.1.0
- https://www.fernandoquadro.com.br/html/2026/02/17/instalacao-do-geonode-5-no-ubuntu-24-04/
- https://www.fernandoquadro.com.br/html/2025/06/23/instalacao-do-certificado-ssl-no-geonode/


## Usuário dedicado (0.1.6)

`SYSTEM_USER=geonode` cria uma conta local com home /home/geonode e shell Bash, sem senha habilitada. Se a conta já existir, exige UID >=1000, home e shell correspondentes; preserva senha e grupos existentes. Não concede sudo e não adiciona ao grupo docker. Pode entrar a partir de uma conta administrativa com `sudo -iu geonode`; isso não habilita SSH.

O instalador continua sendo iniciado com sudo/root. Instalação de pacotes, preparação e comandos Docker são privilegiados. Clone, virtualenv, pip e geração do projeto são executados como SYSTEM_USER, e os arquivos finais pertencem a esse usuário. Alguns ajustes de configuração são aplicados pelo instalador root antes da atribuição final. Isso não altera o usuário interno das imagens Docker. Os volumes continuam sob gestão do Docker; não é aplicado chown nos dados dos containers.

Para esta versão use uma instalação nova e seu env anterior acrescido de SYSTEM_USER. O marcador da 0.1.0 não é migrado automaticamente. Se já começou a instalação com 0.1.0, não remova seus dados: solicite revisão antes de trocar. Apenas `--check` não criou instalação e não impede usar 0.1.6.

Alteração validada por sintaxe e testes isolados com comandos simulados da criação/reutilização de conta e delegação ao usuário. O ambiente de desenvolvimento não permitiu testar chown/runuser de ponta a ponta. Deploy Docker/SSL completo permanece pendente na VM de destino.


## Correção 0.1.6

A leitura do commit (`git rev-parse HEAD`) agora usa SYSTEM_USER, assim como o clone. Corrige a falha dubious ownership sem alterar safe.directory. Não modifica a configuração de acesso do Git.

Se aplicou manualmente essa mesma correção na 0.1.1, o comportamento é equivalente. Para nova execução, copie os valores do seu env para este pacote.


## Novidade 0.1.6: atualização automática de camadas

Base: https://www.fernandoquadro.com.br/html/2025/09/03/atualizar-camadas-do-geoserver-para-o-geonode-automaticamente/

No geonode-install.env:

```dotenv
UPDATE_LAYERS_ENABLED=true
UPDATE_LAYERS_INTERVAL_HOURS=6
```

O cron verifica o workspace a cada 6 horas: 00h, 06h, 12h e 18h,
no fuso do servidor. Valores aceitos: 1, 2, 3, 4, 6, 8, 12 e 24.
O agendamento usa horas do relógio, não tempo decorrido desde a instalação.
Com false, nenhuma tarefa é criada. A primeira execução atualiza as camadas;
as seguintes só executam updatelayers se o checksum mudar.

A implementação usa find/sha256sum do GeoServer e hashlib do host,
sem instalar checksumdir no container (sobrevive à recriação dos containers).
Descobre os containers pelos serviços Compose, sem fixar seus nomes.
O checksum só é gravado após sucesso, e um lock impede sobreposição.
Logs têm rotação semanal, com quatro arquivos anteriores.

Após instalar, edite diretamente:

```bash
sudo nano /etc/cron.d/geonode-updatelayers-curso_geonode
```

Exemplos de expressão: `0 * * * *` (1h), `0 */6 * * *` (6h).
Mantenha o usuário root e o restante da linha. Não precisa reiniciar o cron.
Root executa Docker; SYSTEM_USER permanece fora do grupo docker e sem sudo.

Logs:

```bash
sudo tail -n 100 /var/log/geonode-updatelayers-curso_geonode.log
```

Para adicionar a tarefa a uma instalação 0.1.2 já existente, copie seus
parâmetros anteriores, acrescente os dois novos campos e execute da pasta 0.1.6:

```bash
sudo python3 instalar.py --env geonode-install.env --configure-updatelayers
```

Essa opção não reconstrói imagens nem reinicia a aplicação. Exige os mesmos
parâmetros originais da instalação. Também permite remover o agendamento com
UPDATE_LAYERS_ENABLED=false. Não remova os campos originais do env.

Para executar manualmente (ajuste o nome se PROJECT_NAME for diferente):

```bash
sudo python3 /usr/local/lib/geonode-updatelayers-curso_geonode/updatelayers.py /usr/local/lib/geonode-updatelayers-curso_geonode/config.json
```

Limite: detecta arquivos de configuração no workspace geonode, como no post;
não detecta alterações somente em registros PostGIS ou em dados externos.
Uma execução de updatelayers pode importar camadas publicadas no GeoServer;
confira as permissões e o resultado antes de usar dados restritos.

Validação do pacote: sintaxe, configuração e fluxo do agendador com Docker
simulado. A integração real e a execução periódica precisam ser validadas na VM.


## Novidade 0.1.6: desinstalação para ambientes de laboratório

Use o env original da instalação. Compatível com instalações identificadas
pelas versões 0.1.2 e 0.1.3. Não depende de DNS, RAM ou espaço livre para remover.
Execute o pacote a partir de /tmp ou de outro diretório fora de INSTALL_DIR.

Primeiro veja o plano, sem modificar nada:

```bash
sudo python3 instalar.py --env geonode-install.env --uninstall-geonode --preview
```

Remova o projeto e todos os seus dados:

```bash
sudo python3 instalar.py --env geonode-install.env --uninstall-geonode
```

Para remover também Docker em VM dedicada:

```bash
sudo python3 instalar.py --env geonode-install.env --uninstall-geonode --remove-docker
```

Antes de modificar o host, mostra diretório e recursos e pede o nome do projeto.
Não há opção para suprimir essa confirmação. --preview pode ser combinado com
--remove-docker para verificar bloqueios sem apagar nada.

Remove containers e redes/volumes identificados pelas labels do Compose,
cron /etc/cron.d/geonode-updatelayers-PROJECT_NAME, auxiliar em /usr/local/lib,
checksum em /var/lib, logs e logrotate. Aguarda uma execução updatelayers em curso.
Apaga o diretório da aplicação. Volumes externos e bind mounts fora desse
diretório são preservados. Sem --remove-docker, imagens e cache são preservados.
Não remove tarefas manuais antigas em /etc/crontab ou crontabs de usuários.

--remove-docker bloqueia se detectar outros containers (mesmo parados), volumes,
redes personalizadas, imagens não associadas ao projeto ou recursos externos.
Bloqueia também armazenamento Docker personalizado, Swarm e outros namespaces
containerd. Purga pacotes Docker CE/containerd.io e remove /var/lib/docker e
/var/lib/containerd; não usa prune global nem apt autoremove. Recomendado apenas
para a VM dedicada criada para este instalador. Não execute outras operações
Docker durante a remoção. Configurações Docker personalizadas exigem limpeza
manual; essa opção não é um desinstalador universal de instalações Docker.

Usuário SYSTEM_USER, seu home, Python, Git, cron, logrotate e demais dependências
gerais permanecem. O zip/env do instalador fora do projeto também permanece.
A remoção é definitiva e não cria backup. Em caso de falha, interrompe e mostra
o erro; não há rollback automático. O projeto não pode conter pontos de montagem.

Validação 0.1.6: sintaxe e testes simulados de identificação de recursos,
bloqueio de recursos alheios, prévia e cancelamento. Remoção efetiva de Docker e
volumes ainda deve ser testada em VM descartável.


## Novidade 0.1.6: RAM mínima configurável

O bloqueio fixo de RAM foi substituído por MIN_RAM_GB no geonode-install.env.
O parâmetro é opcional (padrão 14 GiB), aceita decimais com ponto e pode ser
alterado em reexecuções sem invalidar a identificação da instalação.

```dotenv
# Teste: aceitar a partir de 4 GiB
MIN_RAM_GB=4
# Ou 0 para não bloquear por RAM
```

A medição usa a memória total disponível ao Linux (/proc/meminfo), não a RAM
livre no momento. Um limite de 4 pode bloquear uma VM nominal de 4 GB que
reporte menos de 4 GiB; nesse caso escolha, por exemplo, 3.5 ou 0.
--check valida o valor; a comparação com a RAM ocorre na instalação.

MIN_RAM_GB controla apenas a validação: não reduz o consumo dos containers.
Para testes com pouca RAM, revise GEOSERVER_XMS, GEOSERVER_XMX,
UWSGI_PROCESSES e CELERY_WORKERS antes da primeira instalação.
Exemplo inicial mais econômico (não é garantia de capacidade):

```dotenv
MIN_RAM_GB=0
GEOSERVER_XMS=512M
GEOSERVER_XMX=1G
UWSGI_PROCESSES=2
CELERY_WORKERS=1
```

O perfil padrão do pacote continua dimensionado para VM de 16 GB.
Instalações antigas preservam seu fingerprint: MIN_RAM_GB também é excluído
da comparação na desinstalação. Todos os outros parâmetros originais devem
ser mantidos ao administrar uma instalação existente.

Validação 0.1.6: sintaxe, valores inválidos, limites abaixo/igual/acima do
mínimo, checagem desativada, --check com env antigo e compatibilidade de
fingerprint. Deploy Docker completo não executado neste ambiente.


## Novidade 0.1.6: espaço livre mínimo configurável

```dotenv
MIN_DISK_GB=20
```

O padrão é 30 GiB, mas pode ser reduzido. Aceita decimais com ponto;
MIN_DISK_GB=0 desativa o bloqueio. Não reserva nem libera espaço no disco.
O instalador exibe o espaço detectado com três casas decimais; df -h arredonda,
então pode mostrar 30G mesmo quando o valor exato está abaixo de 30 GiB.

30 GiB é uma margem de planejamento para build, imagens e dados, não um tamanho
fixo do GeoNode. Reduzir a checagem não reduz o consumo. A necessidade real
depende das imagens, cache de build, volumes, logs e dados usados no ambiente.
A checagem continua no filesystem do diretório de instalação; se Docker usar
outro filesystem, confira também o espaço desse destino.

O campo é opcional para envs antigos e pode mudar entre reexecuções, sem
invalidar a identificação da instalação. --check valida seu formato;
a medição do espaço livre ocorre ao iniciar a instalação.

Validação 0.1.6: sintaxe, parâmetros antigos/novos, limite abaixo/igual/acima,
valor zero e preservação do fingerprint. Build e deploy completos não foram
executados neste ambiente.


## Novidade 0.1.7: espera final em HTTP/HTTPS

ENABLE_HTTPS=false dispensa o estado do container letsencrypt na espera final.
A mensagem indica HTTP e não anuncia validação de certificado nesse modo.
Com HTTPS, mantém a verificação TLS pelo curl, sem -k, e o estado do letsencrypt.
Django, GeoServer e banco ainda precisam estar running/healthy; Celery, Redis e
proxy geonode precisam estar running. A abertura da página inicial, isoladamente,
não substitui essas verificações. A cada tentativa, mostra os serviços pendentes
com estado e saúde e informa o código de retorno do curl quando o acesso falha.
A consulta local ignora proxies do ambiente para testar diretamente a instância.

Ctrl+C encerra com mensagem explicativa e código 130, sem traceback.
O cron do updatelayers é configurado após o sucesso da validação final.
Não é necessário desinstalar para aplicar apenas a tarefa: use a opção
--configure-updatelayers com o env original se a instância já está operacional.
Para testar a instalação do zero, desinstale com o env original e depois execute
este pacote com os parâmetros escolhidos. Não execute desinstalação sem antes
conferir o plano --preview.

Validação 0.1.7: testes simulados HTTP com letsencrypt parado/ausente,
HTTPS exigindo letsencrypt, falha de HTTP/TLS, serviços ausentes, unhealthy e
starting; JSON Compose em lista e por linha. Sintaxe Python/Bash e --check.
Nenhum container real foi instalado ou removido durante esses testes.


## Novidade 0.1.8: remover pasta pai vazia na desinstalação

Ao concluir a desinstalação, tenta remover também o pai imediato de INSTALL_DIR
usando rmdir. Exemplo: /opt/geonode/curso_geonode -> remove /opt/geonode se vazia.
Nunca remove /opt e não percorre outros ancestrais. Pastas com arquivos, outra
instância, links simbólicos ou pontos de montagem são preservadas. Se a limpeza
da pasta pai não for permitida, informa a preservação sem invalidar a remoção
do projeto. --preview apenas informa essa limpeza condicional.

Aplica-se também a instalações identificadas das versões anteriores: não exige
novo parâmetro nem reinstalação. Como os pacotes anteriores não registravam os
pais criados, essa versão remove o pai imediato vazio mesmo se já existisse
antes da instalação. Não altera a confirmação exigida para desinstalar.
Se a aplicação já foi desinstalada, remova o pai vazio manualmente com rmdir;
o comando de desinstalação continua exigindo o registro original do projeto.

Validação 0.1.8: remoção efetiva de pasta temporária vazia, preservação de pasta
com arquivos, proteção de /opt, links e pontos de montagem, sintaxe e --check.
Desinstalação completa de uma VM não executada neste ambiente.


## Novidade 0.1.9: cookies compatíveis com HTTP e HTTPS

Na geração de novas instalações, ENABLE_HTTPS=false grava no .env da aplicação:

```dotenv
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False
```

Com ENABLE_HTTPS=true, ambos são True. Mantém a proteção CSRF ativa; apenas
ajusta a exigência de transporte HTTPS para os cookies de CSRF e sessão.
Corrige o erro 403 no login por HTTP/IP causado pelos padrões seguros do GeoNode.
Não é necessário acrescentar parâmetros ao geonode-install.env.

A configuração é aplicada antes do build e da criação dos containers. Reexecutar
sobre uma instalação antiga não reconfigura automaticamente o .env existente.
Se a instalação já recebeu a correção manual e o login funciona, não precisa
reinstalar. Este pacote mantém todas as funcionalidades e ajustes anteriores.

Validação 0.1.9: geração de configuração HTTP/HTTPS, substituição de campos
existentes e inclusão de campos ausentes, sintaxe e --check. A correção manual
foi confirmada pelo usuário na VM; um novo deploy completo deste pacote ainda
precisa ser validado na VM.


## Novidade 0.1.10: limpeza completa da VM de laboratório

Prévia (sem alteração):

```bash
sudo python3 instalar.py --env geonode-install.env --uninstall-geonode-completely --preview
```

Executar:

```bash
sudo python3 instalar.py --env geonode-install.env --uninstall-geonode-completely
```

Exige digitar exatamente APAGAR TODO O DOCKER. Este modo apaga TODOS os containers
(inclusive parados), volumes, redes personalizadas, imagens e caches do Docker
local, mesmo que pertençam a outros projetos. Remove também os componentes do
updatelayers associados a PROJECT_NAME, a instalação identificada em INSTALL_DIR,
os pacotes Docker CE/containerd.io, os dados em /var/lib/docker e /var/lib/containerd,
o repositório/chave APT criados pelo instalador e a pasta pai se vazia.
Não há backup nem rollback. Execute somente em VM descartável dedicada.

Não combine com --uninstall-geonode ou --remove-docker. Os modos antigos mantêm
seus bloqueios de proteção de outros projetos. MIN_RAM_GB e MIN_DISK_GB não
impedem a desinstalação.

Se a pasta do projeto já foi removida por uma desinstalação anterior, este modo
continua disponível para limpar Docker; usa INSTALL_DIR/PROJECT_NAME do env para
a limpeza remanescente. Se a pasta ainda existe, exige o registro do instalador
e o env original. Não apaga pastas existentes sem identificação.

Limites: destinado ao Docker CE local padrão em /var/run/docker.sock com dados
em /var/lib/docker. Continua bloqueando contextos remotos, armazenamento
personalizado, Swarm e namespaces containerd de outras aplicações. Não desinstala
Docker rootless, Docker Desktop, instalações Snap ou outros runtimes. Bind mounts
fora de INSTALL_DIR, configurações personalizadas em /etc/docker, credenciais em
~/.docker, usuários e dependências gerais permanecem. Caches de builders remotos
não são apagados. Não é uma restauração do sistema operacional.

Pare outras operações Docker antes da confirmação. O inventário é revalidado
antes da remoção. Se houver montagens ativas após parar os serviços, interrompe
a limpeza dos diretórios de dados. Tarefas cron de outros projetos não são
removidas; este modo limpa apenas o updatelayers do PROJECT_NAME informado.

Validação 0.1.10: testes simulados do inventário global, confirmação, execução
com recursos alheios e projeto já ausente, limites de contexto e compatibilidade
dos modos anteriores. Sintaxe Python/Bash e --check. Nenhuma remoção real de
Docker ou deploy completo foi executado durante a validação.


## Novidade 0.1.11: reconhecer moby_history

A verificação de containerd agora aceita moby e moby_history. A versão 0.1.10
bloqueava incorretamente o namespace moby_history presente no ambiente Docker.
O ajuste vale tanto para --remove-docker quanto para o modo completo. Outros
namespaces continuam bloqueados, com seus nomes mostrados na mensagem de erro.
O modo completo e a confirmação APAGAR TODO O DOCKER permanecem iguais.

Validação 0.1.11: testes dos namespaces moby/moby_history e bloqueio de default,
k8s.io e nomes desconhecidos; fluxo simulado de remoção completa e --check.
Nenhuma remoção real de Docker foi executada durante os testes.
