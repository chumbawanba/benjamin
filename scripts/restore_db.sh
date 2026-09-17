#!/usr/bin/env bash
# restore_db.sh — restaura um dump cifrado gerado por backup_db.sh.
#
# ATENÇÃO: isto SUBSTITUI a base de dados 'benjamin' atual pelo conteúdo do
# backup. Usa isto para testar que os backups funcionam (idealmente contra uma
# BD de teste/staging, não a de produção às cegas) ou numa recuperação real.
#
# Uso:
#   ./scripts/restore_db.sh backups/benjamin-20260917T030000Z.sql.gz.enc

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a; source .env; set +a
fi

if [ -z "${BACKUP_PASSPHRASE:-}" ]; then
  echo "[restore_db] ERRO: BACKUP_PASSPHRASE não está definida no .env" >&2
  exit 1
fi

ENCRYPTED_DUMP="${1:-}"
if [ -z "$ENCRYPTED_DUMP" ] || [ ! -f "$ENCRYPTED_DUMP" ]; then
  echo "Uso: $0 <caminho-para-backup.sql.gz.enc>" >&2
  exit 1
fi

read -r -p "Isto vai APAGAR e substituir a base de dados 'benjamin' atual. Continuar? (escreve 'sim'): " CONFIRM
if [ "$CONFIRM" != "sim" ]; then
  echo "Cancelado."
  exit 1
fi

echo "[restore_db] A decifrar e restaurar $ENCRYPTED_DUMP ..."
openssl enc -d -aes-256-cbc -pbkdf2 -pass env:BACKUP_PASSPHRASE -in "$ENCRYPTED_DUMP" \
  | gunzip \
  | docker compose -f docker-compose.prod.yml exec -T db \
      psql -U app -d benjamin -v ON_ERROR_STOP=1

echo "[restore_db] Concluído."
