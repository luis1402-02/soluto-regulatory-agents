#!/bin/bash

# Backup Script - Faz backup do sistema e dados

set -e

# Configurações
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="soluto_backup_${TIMESTAMP}"

echo "🔄 Iniciando Backup do Sistema Soluto Regulatory Agents"
echo "======================================================="
echo "Backup: ${BACKUP_NAME}"
echo ""

# Criar diretório de backup
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# 1. Backup do banco de dados PostgreSQL
echo "📊 Fazendo backup do PostgreSQL..."
docker exec soluto-postgres pg_dump -U soluto soluto_regulatory | gzip > "${BACKUP_DIR}/${BACKUP_NAME}/postgres_backup.sql.gz"
echo "✅ Backup do PostgreSQL concluído"

# 2. Backup do Redis
echo "📦 Fazendo backup do Redis..."
docker exec soluto-redis redis-cli BGSAVE
sleep 2
docker cp soluto-redis:/data/dump.rdb "${BACKUP_DIR}/${BACKUP_NAME}/redis_backup.rdb"
echo "✅ Backup do Redis concluído"

# 3. Backup dos logs
echo "📝 Fazendo backup dos logs..."
cp -r logs "${BACKUP_DIR}/${BACKUP_NAME}/" 2>/dev/null || echo "⚠️  Sem logs para backup"

# 4. Backup das configurações
echo "⚙️  Fazendo backup das configurações..."
cp .env "${BACKUP_DIR}/${BACKUP_NAME}/.env.backup"
cp docker-compose.prod.yml "${BACKUP_DIR}/${BACKUP_NAME}/"
cp -r config "${BACKUP_DIR}/${BACKUP_NAME}/" 2>/dev/null || true

# 5. Criar arquivo de metadados
echo "📋 Criando metadados..."
cat > "${BACKUP_DIR}/${BACKUP_NAME}/backup_info.json" << EOF
{
  "timestamp": "${TIMESTAMP}",
  "date": "$(date)",
  "system_version": "$(git describe --tags --always 2>/dev/null || echo 'unknown')",
  "docker_version": "$(docker --version)",
  "containers": $(docker-compose -f docker-compose.prod.yml ps --format json)
}
EOF

# 6. Comprimir backup
echo "🗜️  Comprimindo backup..."
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"
cd ..

# 7. Limpar backups antigos (manter últimos 7)
echo "🧹 Limpando backups antigos..."
ls -t "${BACKUP_DIR}"/*.tar.gz 2>/dev/null | tail -n +8 | xargs -r rm

echo ""
echo "======================================================="
echo "✅ Backup concluído!"
echo "📁 Localização: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "📏 Tamanho: $(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)"
echo ""
echo "Para restaurar este backup, use:"
echo "  ./scripts/restore.sh ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"