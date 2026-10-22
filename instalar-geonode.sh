#!/usr/bin/env bash
set -Eeuo pipefail
if [[ ${EUID} -ne 0 ]]; then echo 'Execute com sudo.' >&2; exit 1; fi
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
exec python3 instalar.py "$@"
