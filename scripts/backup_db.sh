#!/usr/bin/env bash
# backup_db.sh — dump diário do Postgres de produção, comprimido e cifrado.
#
# Contexto: revisão legal pedida pelo Edgar (2026-09-17) sobre "guardar toda a
# informação de forma encriptada" - ao investigar isto encontrámos que não
# havia NENHUM backup configurado (risco maior do que a falta de encriptação
# em si: um problema no VPS perdia tudo, sem hipótese de recuperar). Este
# script cobre isso, cifrando o dump para que uma cópia fora do VPS (ex: outro
# provedor de armazenamento) não fique legível se for comprometida.
#
# Uso (a partir da raiz do repositório, no VPS de produção):
#   ./scripts/backup_db.sh
#
# Requer no .env (raiz do repositório, o mesmo usado pelo docker-compose.prod.yml):
#   BACKUP_PASSPHRASE=<frase-secreta longa, gerada com ex: openssl rand -base64 32>
#   BACKUP_DIR=/caminho/para/backups   (opcional - default: ./backups, FORA do
#                                        volume do Postgres, mas ainda no mesmo
#                                        disco do VPS por omissão - ver nota
#                                        "fora do VPS" no fim deste ficheiro)
#
# Cron sugerido (crontab -e no VPS), diário às 03:00 UTC:
#   0 3 * * * cd /caminho/para/benjamin && ./scripts/backup_db.sh >> /var/log/benjamin-backup.log 2>&1
#
# Retenção: mantém os últimos 14 dumps cifrados, apaga os mais antigos.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a; source .env; set +a
fi

if [ -z "${BACKUP_PASSPHRASE:-}" ]; then
  echo "[backup_db] ERRO: BACKUP_PASSPHRASE não está definida no .env — sem isto o dump" >&2
  echo "[backup_db] ficaria em texto simples. Gera uma com: openssl rand -base64 32" >&2
  exit 1
fi

BACKUP_DIR="${BACKUP_DIR:-$REPO_DIR/backups}"
mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RAW_DUMP="$BACKUP_DIR/benjamin-${TIMESTAMP}.sql.gz"
ENCRYPTED_DUMP="${RAW_DUMP}.enc"

echo "[backup_db] A gerar dump da base de dados (${TIMESTAMP})..."

# Corre pg_dump DENTRO do container 'db' (mesmo nome de serviço do
# docker-compose.prod.yml) e cifra diretamente em stream - o dump em texto
# simples nunca fica gravado em disco, só o ficheiro final cifrado.
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U app -d benjamin --format=plain \
  | gzip \
  | openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_PASSPHRASE -out "$ENCRYPTED_DUMP"

SIZE="$(du -h "$ENCRYPTED_DUMP" | cut -f1)"
echo "[backup_db] OK: $ENCRYPTED_DUMP ($SIZE)"

# Retenção: mantém só os últimos 14 (2 semanas de dumps diários).
KEEP=14
COUNT=$(find "$BACKUP_DIR" -maxdepth 1 -name 'benjamin-*.sql.gz.enc' | wc -l)
if [ "$COUNT" -gt "$KEEP" ]; then
  find "$BACKUP_DIR" -maxdepth 1 -name 'benjamin-*.sql.gz.enc' -printf '%T@ %p\n' \
    | sort -n | head -n "$((COUNT - KEEP))" | cut -d' ' -f2- \
    | while read -r old; do
        echo "[backup_db] a remover backup antigo: $old"
        rm -f "$old"
      done
fi

echo "[backup_db] Concluído."
echo "[backup_db] LEMBRETE: isto guarda os backups no próprio VPS ($BACKUP_DIR)."
echo "[backup_db] Cifrados, mas ainda no mesmo disco - se o VPS morrer por completo,"
echo "[backup_db] perdem-se também. Para proteção real contra perda do VPS, copia"
echo "[backup_db] periodicamente este diretório para fora (ex: rclone/rsync para"
echo "[backup_db] outro provedor) - deixado como próximo passo, não feito aqui"
echo "[backup_db] por não haver ainda uma conta de armazenamento externo definida."
