#!/bin/bash
# ============================================================
#  EMI Framework – Database Backup Script
#  Uploads compressed SQL dump to AWS S3
# ============================================================
set -euo pipefail

# Load environment variables
if [ -f /opt/emi-framework/.env ]; then
    export $(grep -v '^#' /opt/emi-framework/.env | xargs)
fi

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/tmp/emi_backup_${DATE}.sql.gz"
S3_PATH="s3://${S3_BACKUP_BUCKET:-emi-framework-backups}/backups/emi_backup_${DATE}.sql.gz"

echo "[$(date)] Starting database backup..."

# Dump and compress
mysqldump \
    -h "${DB_HOST:-localhost}" \
    -P "${DB_PORT:-3306}" \
    -u "${DB_USER:-emi_user}" \
    -p"${DB_PASSWORD}" \
    --single-transaction \
    --routines \
    --events \
    "${DB_NAME:-emi_framework}" | gzip > "$BACKUP_FILE"

echo "[$(date)] Backup created: $BACKUP_FILE ($(du -sh $BACKUP_FILE | cut -f1))"

# Upload to S3
aws s3 cp "$BACKUP_FILE" "$S3_PATH"
echo "[$(date)] Backup uploaded to $S3_PATH"

# Remove local temp file
rm -f "$BACKUP_FILE"

# Keep only last 30 backups in S3
aws s3 ls "s3://${S3_BACKUP_BUCKET:-emi-framework-backups}/backups/" \
    | sort \
    | head -n -30 \
    | awk '{print $4}' \
    | xargs -I {} aws s3 rm "s3://${S3_BACKUP_BUCKET:-emi-framework-backups}/backups/{}" || true

echo "[$(date)] Backup complete!"
