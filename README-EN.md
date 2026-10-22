# GeoNode Installer

[Português](README.md) | **English**

Automated GeoNode installation with Docker, configuration through an `.env` file, optional HTTPS, and tools for maintaining training and test environments.

**Developed by Geocursos.** English documentation for installer version **0.1.11**, with default settings for **GeoNode 5.1.0**.

The goal is to reduce repetitive VM setup: fill in the parameters, validate the configuration, and run one command. The installer configures an existing machine; it does not provision servers, DNS records, or firewall rules at your provider.

> **Before you start:** use a fresh Ubuntu 24.04 x86_64 machine. Uninstall options permanently delete data. Complete cleanup also removes Docker resources belonging to other projects.

Script filenames, parameters, example paths, and commands retain their original names. Installer messages are currently in Portuguese. The complete-cleanup confirmation phrase must also be entered in Portuguese exactly as shown.

## Contents

1. [Features](#1-features)
2. [Requirements and limits](#2-requirements-and-limits)
3. [Project files](#3-project-files)
4. [Quick start](#4-quick-start)
5. [Parameter reference](#5-parameter-reference)
6. [Configuration scenarios](#6-configuration-scenarios)
7. [Installation stages](#7-installation-stages)
8. [First login](#8-first-login)
9. [Operation and diagnostics](#9-operation-and-diagnostics)
10. [Automatic layer updates](#10-automatic-layer-updates)
11. [Resuming installation and changing configuration](#11-resuming-installation-and-changing-configuration)
12. [Uninstallation](#12-uninstallation)
13. [Command reference](#13-command-reference)
14. [Troubleshooting](#14-troubleshooting)
15. [Secrets, permissions, and publishing](#15-secrets-permissions-and-publishing)
16. [Validation and known limitations](#16-validation-and-known-limitations)
17. [Version history](#17-version-history)
18. [Contributing, authorship, and references](#18-contributing-authorship-and-references)

## 1. Features

- Installs system dependencies and, if the Docker executable is missing, Docker CE and the Compose/Buildx plugins.
- Creates or reuses a compatible dedicated user for application files.
- Fetches a reference from the official `geonode-project` repository and generates the Django project.
- Generates random passwords and the application's `.env` file.
- Configures a domain, IP address, or `localhost`, using HTTP or HTTPS.
- Enables certificate issuance/renewal through the Docker project's Let’s Encrypt mechanism when requested.
- Adjusts the GeoServer heap, uWSGI processes, and Celery concurrency.
- Configures session and CSRF cookies for HTTP/HTTPS.
- Builds images, starts containers, and waits for services to become available.
- Configures an optional `updatelayers` task with an interval defined in the installer `.env` file.
- Provides an uninstall preview, project removal, and complete Docker cleanup for a dedicated VM.

It does not install GeoNode directly on the host, automatically upgrade the application, or create a VM on Hetzner or another provider.

## 2. Requirements and limits

| Item | Requirement or behavior |
| --- | --- |
| Operating system | Ubuntu **24.04**, **x86_64**, with systemd/APT |
| Administration | A user with `sudo`, or root |
| Initial Python installation | Python 3 available to run the installer |
| Default profile | A VM with approximately **16 GB of RAM** |
| Minimum RAM check | **14 GiB**, configurable through `MIN_RAM_GB` |
| Free disk space check | **30 GiB** on the destination filesystem, configurable through `MIN_DISK_GB` |
| Internet | Access to Ubuntu/Docker repositories, GitHub, PyPI, and image registries |
| HTTP | TCP port 80 reachable at the configured address |
| HTTPS | A domain pointing to the VM and TCP ports 80/443 reachable for certificate issuance and use |
| Directory | A subdirectory under `/opt`, such as `/opt/geonode/curso_geonode` |

The RAM/disk minimums are configurable checks, not a performance guarantee or the fixed size of the installation. Usage depends on images, build cache, data, logs, and concurrent users.

RAM is measured using the total reported in `/proc/meminfo`, not the currently free memory. Although parameter names use `GB`, calculations use **GiB**. `df -h` rounds values and may display `30G` when the exact free space is below 30 GiB.

The disk check uses the filesystem containing the parent of `INSTALL_DIR`. If Docker stores images on another filesystem, check that space separately. The installer does not automatically create swap.

For production, plan backups, monitoring, capacity, and workflow validation for the actual environment rather than relying on this automation alone.

## 3. Project files

| File | Purpose |
| --- | --- |
| `instalar-geonode.sh` | Bash entry point; requires root and calls the Python installer |
| `instalar.py` | Validation, project generation, deployment, and scheduled-task configuration |
| `desinstalar.py` | Uninstall implementation |
| `updatelayers.py` | Workspace comparison and execution of `manage.py updatelayers` |
| `geonode-install.env` | Input parameters; does not contain generated application passwords |
| `LEIA-ME.md` | Instructions included in earlier packages |
| `README.md` | Portuguese repository documentation |
| `README-EN.md` | This English documentation |

Keep the Python files together. The installer imports the uninstall module and copies the update helper from its own directory.

## 4. Quick start

### 4.1. Get the files

Download the desired release package, transfer it to the VM, and extract it:

```bash
sudo apt-get update
sudo apt-get install -y unzip
unzip geonode-installer-0.1.11.zip
cd geonode-installer-0.1.11
```

If using a repository checkout with the scripts at its root, enter that root directory. The remaining commands are the same. Prefer a published release rather than following unversioned changes during a training course.

### 4.2. Configure

```bash
nano geonode-install.env
```

Set `HOSTNAME`, the HTTPS mode, and the remaining parameters for your VM. See section 6 for examples.

### 4.3. Validate

```bash
python3 instalar.py --env geonode-install.env --check
```

Checks parameter names, formats, and address resolution. When provided, compares `SERVER_IPV4` with the resolved addresses.

**It does not install packages or test ports, external access, actual machine resources, login, or certificate issuance.** Operating-system checks and RAM/disk comparisons take place when running the installation.

### 4.4. Run

```bash
sudo bash instalar-geonode.sh --env geonode-install.env
```

Keep the session open and monitor the output. Alternatively, run inside a persistent terminal session that you have prepared beforehand.

The Bash entry point changes to its own directory before calling Python. If your configuration file is elsewhere, pass its absolute path through `--env`.

## 5. Parameter reference

Complete example using the package defaults:

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

Replace the example domains before running. Placeholders containing `seudominio` are rejected.

| Parameter | Description and accepted values |
| --- | --- |
| `GEONODE_PROJECT_REF` | Reference used to clone the template: a valid branch or tag. Default: `5.1.0`. This is not a generic field for any commit SHA; cloning uses `--branch`. |
| `GEONODE_VERSION` | Numeric version applied to the GeoNode dependency and base image. Default: `5.1.0`. |
| `DJANGO_BOOTSTRAP_VERSION` | Django installed in the temporary environment to generate the project. Default: `5.2`. It does not determine the Django version running inside the containers. |
| `SYSTEM_USER` | Host user for application files. Starts with a lowercase letter; allows lowercase letters, digits, `_`, and `-`; up to 31 characters. `root` is not accepted. |
| `PROJECT_NAME` | Name passed to project generation. Between 3 and 40 characters; starts with a lowercase letter; remaining characters may be lowercase letters, digits, and `_`. |
| `INSTALL_DIR` | Absolute directory below `/opt`, with at least one intermediate directory. Example: `/opt/geonode/curso_geonode`. |
| `HOSTNAME` | Domain, IPv4 address, or `localhost`, without a protocol, port, or slash. HTTPS requires a domain. The current validator does not accept literal IPv6 addresses. |
| `ENABLE_HTTPS` | Exactly `true` or `false`, in lowercase. |
| `LETSENCRYPT_EMAIL` | Certificate contact email; required for HTTPS. May be empty for HTTP. |
| `SERVER_IPV4` | Optional. An IPv4 address that must appear when resolving `HOSTNAME`. It does not set the application address; `HOSTNAME` does that. |
| `GEOSERVER_XMS` | Initial Java heap, such as `512M` or `2G`; a positive integer followed by uppercase `M` or `G`. |
| `GEOSERVER_XMX` | Maximum Java heap, such as `1G` or `4G`; must not be smaller than XMS. |
| `UWSGI_PROCESSES` | Positive integer; fixes the process count and removes the template's `cheaper` autoscaling configuration. |
| `CELERY_WORKERS` | Positive integer used for the main worker's concurrency/autoscaling. The installer separately sets harvester concurrency to 1. |
| `WAIT_SECONDS` | Positive integer; deadline for final checks after starting containers. Default: 1800 seconds. Does not limit build time. |
| `UPDATE_LAYERS_ENABLED` | `true` enables the task; `false` skips creating it or removes its schedule. Default: `true`. |
| `UPDATE_LAYERS_INTERVAL_HOURS` | One of: `1`, `2`, `3`, `4`, `6`, `8`, `12`, `24`. Default: 1. |
| `MIN_RAM_GB` | Nonnegative number; decimals use a period. Default: 14. `0` disables the check. |
| `MIN_DISK_GB` | Nonnegative number; decimals use a period. Default: 30. `0` disables the check. |

The last four parameters may be omitted from older configuration files; the installer supplies their defaults. All other keys are required, even when an empty value is allowed.

### File format

- Use one `KEY=value` line per parameter.
- Do not add arbitrary keys: unknown and duplicate names are rejected.
- Comments must occupy a line starting with `#`.
- Do not add a comment after a value on the same line.
- Do not use `export`, variable substitution, or shell commands: the file is read as text, not executed.
- Use a period, not a comma, for decimal values.

## 6. Configuration scenarios

### 6.1. Domain with HTTPS

```dotenv
HOSTNAME=geo.exemplo.com.br
ENABLE_HTTPS=true
LETSENCRYPT_EMAIL=administrador@exemplo.com.br
SERVER_IPV4=
```

Configure DNS beforehand and allow TCP 80/443. If using `SERVER_IPV4`, enter the correct public IPv4 address. If an IPv6 DNS record exists, it must also route correctly to the instance.

The Docker project provides the certificate mechanism; you do not need to install Certbot separately on the host. The resulting address in this example is `https://geo.exemplo.com.br/`.

### 6.2. Internal-network VM using an IP address without SSL

```dotenv
HOSTNAME=192.168.186.142
ENABLE_HTTPS=false
LETSENCRYPT_EMAIL=
SERVER_IPV4=
```

Address: `http://192.168.186.142/`. Use a fixed IP address or DHCP reservation and allow TCP 80 between the browser and the VM. Replace the example with your VM's actual address.

### 6.3. Localhost

```dotenv
HOSTNAME=localhost
ENABLE_HTTPS=false
LETSENCRYPT_EMAIL=
SERVER_IPV4=
```

Address: `http://localhost/`, from the machine itself. To access it from another computer, configure the VM's IP address or domain from the start.

### 6.4. Reduced profile for a lab

An initial example for a test VM with approximately 8 GB of RAM:

```dotenv
MIN_RAM_GB=7
MIN_DISK_GB=20
GEOSERVER_XMS=512M
GEOSERVER_XMX=1G
UWSGI_PROCESSES=2
CELERY_WORKERS=1
```

Suitability depends on the data and exercises. You can disable the minimum checks:

```dotenv
MIN_RAM_GB=0
MIN_DISK_GB=0
```

This does not reduce usage or prevent resource exhaustion. Other settings remain unchanged until you edit them.

### 6.5. Cookies and Let’s Encrypt over HTTP

When generating the application's `.env`:

| Mode | `CSRF_COOKIE_SECURE` | `SESSION_COOKIE_SECURE` |
| --- | --- | --- |
| HTTP | `False` | `False` |
| HTTPS | `True` | `True` |

CSRF protection remains enabled. These settings allow cookies over HTTP in the lab and require HTTPS when that mode is enabled.

With HTTP, Let’s Encrypt issuance is disabled and its container is excluded from final readiness checks. **The service remains defined in Compose and may appear to restart with exit code 0**; version 0.1.11 does not remove it or automatically place it in an inactive profile. The proxy also retains its Compose port mappings; disabling HTTPS does not create a firewall rule for port 443.

## 7. Installation stages

1. Reads and validates the parameter file and resolves the address.
2. Checks Ubuntu/architecture, permissions, existing installation identity, RAM, and disk.
3. Installs dependencies and, if needed, Docker CE/Compose/Buildx; enables the Docker service.
4. Creates/reuses the dedicated user and prepares directories.
5. Clones the template reference and records its commit.
6. Creates a temporary Python environment with the bootstrap Django version.
7. Generates the application, secrets, and configuration files.
8. Adjusts services, assigns files to the dedicated user, and writes `.installer-state.json`.
9. Validates Compose, builds images, and starts containers.
10. Waits for the web response and expected service states.
11. Configures the optional layer-update schedule.

### User and permissions

A new user is created without an enabled login password, without sudo privileges, and without membership in the Docker group. An existing user must have UID >= 1000, home `/home/NAME`, and shell `/bin/bash`. The installer does not reset that user's existing permissions, password, or group memberships.

Download and generation run as `SYSTEM_USER`; package management and Docker commands run as root. This does not determine the users of processes inside each image.

### Readiness checks

| Compose service | Required condition |
| --- | --- |
| `django`, `geoserver`, `db` | `running` and `healthy` |
| `celery`, `redis`, `geonode` (proxy) | `running` |
| `letsencrypt` | `running`, only when HTTPS is enabled |
| Web address | Successful `curl` return code; HTTPS checks do not bypass certificate validation |

The installer reports pending components on each attempt. Being able to open the home page does not mean GeoServer and all other components are ready.

The web check runs locally, directing the configured host to loopback and ignoring environment proxies. It does not replace external DNS/firewall testing.

## 8. First login

Initial username: **`admin`**. Retrieve its password as follows, adjusting the path if needed:

```bash
sudo awk -F= '/^ADMIN_PASSWORD=/{print $2}' \
  /opt/geonode/curso_geonode/.env
```

There are two different configuration files:

| File | Contents |
| --- | --- |
| `geonode-install.env` | Inputs for the automation |
| `/opt/geonode/curso_geonode/.env` | Effective application configuration and service passwords |

Do not publish the application's `.env`. Log in and validate uploads, layer viewing, maps, dashboards, and permissions before a class or delivery.

## 9. Operation and diagnostics

Use explicit paths if your terminal user cannot enter the application directory:

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

Resource and disk usage:

```bash
sudo docker stats
df -h
sudo docker system df
```

Actual container names may differ from `PROJECT_NAME`. These commands use **Compose service names**. In particular, `geonode` in this Compose file identifies the proxy; `django` identifies the application.

GeoServer is published on the host at `127.0.0.1:8080`, retaining internal access through the proxy. For browser access, use the configured public address and the route provided by the portal.

## 10. Automatic layer updates

### 10.1. When to use this feature

This task is mainly useful for layers published **directly in GeoServer**, including layers backed by an external PostGIS database, that need to be added to or have their information updated in the GeoNode catalog.

Layers uploaded and managed through GeoNode already follow its integrated publication workflow and do not depend on this additional task.

The automation does not update database records. GeoServer queries data from its configured source; `updatelayers` handles catalog integration. Review the results and permissions of imported layers as well.

### 10.2. Configuration and behavior

```dotenv
UPDATE_LAYERS_ENABLED=true
UPDATE_LAYERS_INTERVAL_HOURS=6
```

Cron runs at 00:00, 06:00, 12:00, and 18:00 in the server's timezone. This is a clock-based schedule, not a countdown starting when installation completes. A 24-hour interval runs daily at midnight.

The task:

1. Acquires a lock to prevent overlapping executions.
2. Reads file contents under `/geoserver_data/data/workspaces/geonode` inside GeoServer.
3. Computes a checksum of names/contents using `find`/`sha256sum` in the container and `hashlib` on the host.
4. Runs `python3 manage.py updatelayers` in the `django` service on its first execution or when the checksum changes.
5. Saves the checksum only after success; failures allow another attempt at the next scheduled time.

It does not install `checksumdir` inside the container. The helper and state are stored on the host and survive container recreation.

**Limits:** only this workspace is monitored. Changes confined to PostGIS rows, external data, or other workspaces do not trigger an update. An empty or missing workspace produces an error and preserves the previous checksum. `updatelayers` runs without an additional filter; this does not guarantee updates to every type of metadata or content.

### 10.3. Files and logs

For `PROJECT_NAME=curso_geonode`:

| Path | Purpose |
| --- | --- |
| `/etc/cron.d/geonode-updatelayers-curso_geonode` | Root cron schedule |
| `/usr/local/lib/geonode-updatelayers-curso_geonode/updatelayers.py` | Helper |
| `/usr/local/lib/geonode-updatelayers-curso_geonode/config.json` | Paths and Docker executable |
| `/var/lib/geonode-updatelayers-curso_geonode/checksum.sha256` | Last successfully processed checksum |
| `/var/lib/geonode-updatelayers-curso_geonode/lock` | Task lock |
| `/var/log/geonode-updatelayers-curso_geonode.log` | Execution output |
| `/etc/logrotate.d/geonode-updatelayers-curso_geonode` | Weekly rotation, keeping four previous log files |

Edit the schedule directly:

```bash
sudo nano /etc/cron.d/geonode-updatelayers-curso_geonode
```

Examples: `0 * * * *` for hourly checks; `0 */6 * * *` for checks every six hours. Keep `root` and the rest of the command on the line. Reconfiguring through the installer overwrites this schedule with the value from the installer `.env`.

Logs:

```bash
sudo tail -n 100 /var/log/geonode-updatelayers-curso_geonode.log
```

### 10.4. Configure an existing installation

From the package directory, using the instance's original parameters:

```bash
sudo python3 instalar.py --env geonode-install.env --configure-updatelayers
```

Does not rebuild images or restart the application. It still validates configuration/DNS, the system, and installation identity, but does not perform the deployment RAM/disk checks.

To disable, set `UPDATE_LAYERS_ENABLED=false` and repeat the command. Only the schedule is removed; the helper, state, and logs remain until uninstallation. A task already running is not canceled.

Run manually:

```bash
sudo python3 \
  /usr/local/lib/geonode-updatelayers-curso_geonode/updatelayers.py \
  /usr/local/lib/geonode-updatelayers-curso_geonode/config.json
```

## 11. Resuming installation and changing configuration

If execution fails or is interrupted, containers already started continue independently of the installer process. `Ctrl+C` exits with code 130 and does not remove volumes.

To retry, run the installation command with the same parameter file. If the project has already been generated, the installer recognizes it through `.installer-state.json` and does not generate new passwords. However, a normal run still installs/checks packages again, builds images, and runs `compose up`.

The state file stores a fingerprint of the parameters. Changing the version, name, hostname, user, directory, or service sizing invalidates a resume attempt. The following four fields are excluded from the fingerprint and may change:

- `MIN_RAM_GB`;
- `MIN_DISK_GB`;
- `UPDATE_LAYERS_ENABLED`;
- `UPDATE_LAYERS_INTERVAL_HOURS`.

Editing only `geonode-install.env` **does not reconfigure** an existing application. There is no automatic HTTP-to-HTTPS migration, hostname change, version upgrade, or application of fixes from newer installer releases to previously generated projects.

If interrupted before the final stage, the layer-update schedule may not have been created. Use the dedicated option after confirming that the instance is operational.

Do not edit the state file to bypass mismatches. Upgrading an instance that contains data requires a separate procedure with backups and testing.

## 12. Uninstallation

> **Permanent data loss:** no automatic backup or rollback is provided. Run from the installer directory, outside `INSTALL_DIR`, using the original parameters. Do not perform other Docker operations during removal.

### 12.1. Comparing the modes

| Mode | Project/data | Images/cache | Docker | Other projects |
| --- | --- | --- | --- | --- |
| `--uninstall-geonode` | Removes identified resources and application directory | Preserved | Preserved | Preserved; shared dependencies may block removal |
| `--uninstall-geonode --remove-docker` | Removed | Removes global data after checking exclusive use | Packages purged | Blocks if unrelated/external resources are detected |
| `--uninstall-geonode-completely` | Removes the identified installation and all local Docker resources | Removed globally | Packages purged | **Also deletes other projects' Docker resources** |

### 12.2. GeoNode only

Preview:

```bash
sudo python3 instalar.py --env geonode-install.env \
  --uninstall-geonode --preview
```

Run:

```bash
sudo python3 instalar.py --env geonode-install.env \
  --uninstall-geonode
```

Confirmation: enter the value of `PROJECT_NAME`.

Removes containers, networks, and volumes identified by Compose labels, the application directory, and its `updatelayers` cron/helper/checksum/logs/logrotate configuration. Waits for any running update task before removing containers.

External resources declared in Compose are not deleted in this mode. Bind-mounted files outside the application directory remain. Preserved images/cache can make reinstallation faster even when the database and data are recreated.

The immediate parent of `INSTALL_DIR` is removed only if empty; `/opt` is never removed. Other ancestors are not removed. An empty parent may be removed even if it existed before installation: earlier versions do not record its origin. Symbolic links and mount points are preserved.

### 12.3. Also remove Docker after checking exclusive use

```bash
sudo python3 instalar.py --env geonode-install.env \
  --uninstall-geonode --remove-docker
```

Blocks if other projects have containers (including stopped ones), volumes, custom networks, unrelated images, or external resources. Old/base images can cause a conservative block. Initial checks run before deleting the project.

### 12.4. Complete cleanup of a lab VM

Preview:

```bash
sudo python3 instalar.py --env geonode-install.env \
  --uninstall-geonode-completely --preview
```

Run:

```bash
sudo python3 instalar.py --env geonode-install.env \
  --uninstall-geonode-completely
```

Required confirmation, entered **exactly in Portuguese**:

```text
APAGAR TODO O DOCKER
```

The phrase means “DELETE ALL DOCKER.” Do not translate it when entering the confirmation.

Deletes all local Docker containers, volumes, custom networks, images, and caches, including resources unrelated to GeoNode. It then stops the services, purges installed Docker CE/containerd.io packages, and removes the default data directories and the APT repository/key used by the installer.

The inventory is checked again after confirmation. Do not combine this mode with `--uninstall-geonode` or `--remove-docker`.

If `INSTALL_DIR` no longer exists, complete mode can still clean Docker and the helpers identified by the `.env` file. If the directory exists, it requires the installer state file and compatible parameters; existing directories without identification are not deleted.

### 12.5. Protections that remain active

Docker removal targets the standard local Docker CE installation. It remains blocked for storage outside `/var/lib/docker`, active Swarm, and unknown containerd namespaces.

**`moby` and `moby_history`** are recognized. Other names are included in the error. Complete mode requires the socket `unix:///var/run/docker.sock`, rejects an explicit `DOCKER_CONTEXT`, and checks data paths. Active mounts after services stop interrupt cleanup of those directories.

This does not cover rootless Docker, Docker Desktop, Snap installations, or other runtimes. An intermediate failure may leave resources partially removed; there is no transaction or automatic restoration.

### 12.6. What remains

- The `SYSTEM_USER` account and its home directory.
- General dependencies, including Python, Git, cron, and logrotate.
- The package and parameter file outside `INSTALL_DIR`.
- Custom configuration in `/etc/docker` and credentials in `~/.docker`.
- Bind-mounted files outside the removed application directory.
- Older manually created crontabs and tasks belonging to other projects.
- Remote builder caches.

Cleanup does not restore the VM to its original operating-system state. Recreate the VM if you need that guarantee.

### 12.7. Reinstall

After removal completes:

```bash
sudo bash instalar-geonode.sh --env geonode-install.env
```

If Docker was removed, the installer installs it again. Generating a fresh project creates new passwords.

## 13. Command reference

| Option | Purpose |
| --- | --- |
| `--env PATH` | Parameter file; default: `geonode-install.env` |
| `--check` | Validates inputs and address resolution without installing |
| `--configure-updatelayers` | Configures only the task for an existing project |
| `--uninstall-geonode` | Uninstalls the identified project |
| `--remove-docker` | Modifier for `--uninstall-geonode`; requires exclusive use |
| `--uninstall-geonode-completely` | Global local cleanup, including other projects' resources |
| `--preview` | Previews uninstall modes; does not apply to installation |
| `--help` | Shows available options |

```bash
python3 instalar.py --help
```

Do not combine uninstallation with `--check` or `--configure-updatelayers`. There is no option to suppress destructive-operation confirmations.

## 14. Troubleshooting

### Permission denied when entering /opt/geonode

The directory belongs to the dedicated user and may not allow direct access by your administrative account. Use the explicit paths from section 9 with `sudo`. Do not make secret files publicly readable to solve this access issue.

### No configuration file provided

Compose was called outside the application directory. Use `--project-directory`, `--env-file`, and `-f` as shown in section 9.

### RAM or disk check blocks installation

Adjust `MIN_RAM_GB` or `MIN_DISK_GB`. For limited lab resources, also review the heap and workers. `0` disables only the corresponding check.

### Configuration changed

The Portuguese message is `Configuração mudou`. Use the original installation parameters. Pointing a new `.env` file at the same directory is not sufficient. Changes to the four optional fields listed in section 11 are allowed.

### Portal opens, but the installer keeps waiting

Check the `Ainda aguardando` (“Still waiting”) message. GeoServer may remain `starting` while the home page already responds. The script waits for the conditions in section 7 until `WAIT_SECONDS` expires.

### Let’s Encrypt restarts in HTTP mode

In the current version, this can happen because the service remains defined in Compose while certificate issuance is disabled. It is not required for HTTP readiness. Check its logs to distinguish this case from an HTTPS problem.

### Login returns a CSRF 403 over HTTP

For new installations generated by version 0.1.9 or later, both secure-cookie settings are set to `False` in HTTP mode. Check their effective values:

```bash
sudo docker compose \
  --project-directory /opt/geonode/curso_geonode \
  --env-file /opt/geonode/curso_geonode/.env \
  -f /opt/geonode/curso_geonode/docker-compose.yml \
  exec -T django python3 manage.py shell -c \
  'from django.conf import settings; print("SITEURL:", settings.SITEURL); print("CSRF_COOKIE_SECURE:", settings.CSRF_COOKIE_SECURE); print("SESSION_COOKIE_SECURE:", settings.SESSION_COOKIE_SECURE)'
```

If an older instance needs correction, back up the application's `.env` and set `CSRF_COOKIE_SECURE=False` and `SESSION_COOKIE_SECURE=False` **only when accessing over HTTP**. Keep `True` for HTTPS. Recreate the services to load environment changes:

```bash
sudo docker compose \
  --project-directory /opt/geonode/curso_geonode \
  --env-file /opt/geonode/curso_geonode/.env \
  -f /opt/geonode/curso_geonode/docker-compose.yml \
  up -d --no-deps --force-recreate django celery
```

Reopen the login page in a private/incognito window. Do not disable CSRF middleware or enable DEBUG to bypass the failure.

### Containerd has other namespaces

The Portuguese error refers to `Containerd` and `namespaces`.

```bash
sudo ctr namespaces list
```

Version 0.1.11 accepts `moby` and `moby_history`. If another name appears, investigate which application uses it before removing Docker/containerd. Do not manually delete namespaces as a shortcut.

### Directory already exists without identification

The directory does not contain the expected state file. Choose a new destination or investigate the existing installation. The installer does not assume that an unidentified directory can be reused or deleted.

### Reinstallation is much faster

Without complete cleanup, images and caches remain and can be reused. This does not prove the database was retained. Check whether volumes were recreated and whether previous data was actually removed.

## 15. Secrets, permissions, and publishing

The installer generates random secrets, protects the application's `.env` with mode `600`, and does not pass those passwords directly as generator command-line arguments.

Before publishing on GitHub:

- Keep only example domains/IP addresses in the distributed parameter file.
- Do not upload the application's `.env`, its backups, passwords, tokens, logs with private data, or volumes.
- Publish the scripts and example configuration, not the deployed project with its secrets.
- Preserve already published release files; distribute fixes as new versions.
- If using GitHub tags/releases, keep package identification aligned with the code version.

This documentation does not assign a license to the installer. Define a `LICENSE` file before announcing the repository's license; do not assume that a license from another Geocursos project applies here.

## 16. Validation and known limitations

During the tool's development, real GeoNode 5.1.0 installations were reported with HTTPS and with HTTP using an internal-network IP address. Login after the manual HTTP cookie correction was confirmed by the user.

Version 0.1.11 was checked for syntax and parameter validation, with simulated readiness, update, and removal flows. **This documentation does not confirm a successful real complete cleanup using version 0.1.11.** Each release should be validated on a disposable VM before classroom or production use.

Relevant limitations:

- Operating system/architecture fixed to Ubuntu 24.04 x86_64.
- GeoNode/template/Django versions are not freely interchangeable; different references may require adaptation.
- Auxiliary images and packages follow the template/repositories; not every component is pinned by digest or exact version.
- If Docker already exists, missing plugins are not automatically installed or repaired.
- One project per destination; multiple concurrent instances on the same VM are not guaranteed to work. Compose defines its own names and ports; do not confuse `PROJECT_NAME` with `COMPOSE_PROJECT_NAME`.
- No automatic upgrade, hostname change, or application of new fixes to an existing instance.
- No automated backup/restore provided by the installer and no uninstall rollback.
- No general persistent installer log file; output goes to the terminal. The `updatelayers` task has its own log and rotation configuration.
- Final success does not test authentication, uploads, maps, dashboards, permissions, or external access.

## 17. Version history

| Version | Main change |
| --- | --- |
| 0.1.0 | Initial configurable installation, GeoNode 5.1.0, and optional HTTPS |
| 0.1.1 | Dedicated `SYSTEM_USER` account |
| 0.1.2 | Git commit lookup executed as the clone's owner |
| 0.1.3 | `updatelayers` scheduling and task-only configuration |
| 0.1.4 | Project uninstall and optional protected Docker removal |
| 0.1.5 | Configurable minimum RAM |
| 0.1.6 | Configurable minimum free disk space |
| 0.1.7 | Corrected HTTP/HTTPS readiness, pending-service diagnostics, and handled Ctrl+C |
| 0.1.8 | Conditional cleanup of an empty parent directory |
| 0.1.9 | Session/CSRF cookies configured for HTTP/HTTPS |
| 0.1.10 | Complete global cleanup for lab VMs |
| 0.1.11 | Recognition of the `moby_history` namespace during Docker removal |

## 18. Contributing, authorship, and references

**Geocursos — Fernando Quadro.**

When reporting an issue in the repository, include the installer version, operating system/architecture, VM resources, HTTP/HTTPS mode, command executed, and relevant output. Remove credentials and private data. Do not attach the application's `.env`.

When contributing, describe the behavior before/after the change and the tests performed. For removal changes, test with simulation first, then on a disposable VM. For web configuration, validate HTTP, HTTPS, and login, not just the home page.

References and the original procedures (blog articles are in Portuguese):

- [Geocursos](https://geocursos.com.br/)
- [Fernando Quadro's Blog](https://www.fernandoquadro.com.br/)
- [GeoNode Project — official repository](https://github.com/GeoNode/geonode-project)
- [GeoNode — official repository](https://github.com/GeoNode/geonode)
- [Installing GeoNode 5 on Ubuntu 24.04](https://www.fernandoquadro.com.br/html/2026/02/17/instalacao-do-geonode-5-no-ubuntu-24-04/)
- [Installing an SSL certificate in GeoNode](https://www.fernandoquadro.com.br/html/2025/06/23/instalacao-do-certificado-ssl-no-geonode/)
- [Automatically updating layers from GeoServer to GeoNode](https://www.fernandoquadro.com.br/html/2025/09/03/atualizar-camadas-do-geoserver-para-o-geonode-automaticamente/)

The layer automation adapts the idea from the tutorial, which credits Diego Varela's contribution. This implementation uses a SHA-256 checksum without installing a Python dependency inside the GeoServer container.
