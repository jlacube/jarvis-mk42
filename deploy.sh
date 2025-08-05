#!/bin/bash

# JARVIS-MK42 Production Deployment Script
# This script handles automated deployment with rollback capabilities

set -e

# Configuration
CONTAINER_NAME="jarvis-mk42-app"
IMAGE_NAME="jarvis-mk42:latest"
BACKUP_DIR="/opt/jarvis/backups"
LOG_FILE="/var/log/jarvis-deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Pre-deployment checks
pre_deploy_checks() {
    log "Starting pre-deployment checks..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running. Please start Docker and try again."
    fi
    
    # Check if required files exist
    if [[ ! -f "docker-compose.yml" ]]; then
        error "docker-compose.yml not found in current directory"
    fi
    
    if [[ ! -f ".env" ]]; then
        warning ".env file not found. Using .env.example as template..."
        cp .env.example .env
        error "Please configure .env file with your settings and run again"
    fi
    
    # Check disk space (need at least 2GB)
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 2097152 ]]; then
        error "Insufficient disk space. Need at least 2GB free."
    fi
    
    success "Pre-deployment checks passed"
}

# Create backup of current deployment
create_backup() {
    log "Creating backup of current deployment..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Create timestamped backup directory
    BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    CURRENT_BACKUP_DIR="$BACKUP_DIR/backup_$BACKUP_TIMESTAMP"
    mkdir -p "$CURRENT_BACKUP_DIR"
    
    # Backup database
    if docker ps | grep -q "jarvis-postgres"; then
        log "Backing up database..."
        docker exec jarvis-postgres pg_dump -U jarvis jarvis_db > "$CURRENT_BACKUP_DIR/database_backup.sql"
    fi
    
    # Backup application data
    if [[ -d "data" ]]; then
        log "Backing up application data..."
        cp -r data "$CURRENT_BACKUP_DIR/"
    fi
    
    # Backup logs
    if [[ -d "logs" ]]; then
        log "Backing up logs..."
        cp -r logs "$CURRENT_BACKUP_DIR/"
    fi
    
    # Save current image for rollback
    if docker images | grep -q "$IMAGE_NAME"; then
        log "Saving current image for rollback..."
        docker save "$IMAGE_NAME" | gzip > "$CURRENT_BACKUP_DIR/current_image.tar.gz"
    fi
    
    echo "$CURRENT_BACKUP_DIR" > "$BACKUP_DIR/latest_backup_path"
    success "Backup created at $CURRENT_BACKUP_DIR"
}

# Deploy new version
deploy() {
    log "Starting deployment..."
    
    # Build new image
    log "Building new Docker image..."
    docker-compose build --no-cache jarvis-app
    
    # Test the new image
    log "Testing new image..."
    docker-compose run --rm jarvis-app python -c "import app; print('Application imports successfully')"
    
    # Stop current containers gracefully
    log "Stopping current containers..."
    docker-compose down --timeout 30
    
    # Start new containers
    log "Starting new containers..."
    docker-compose up -d
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 30
    
    # Health check
    max_attempts=10
    attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        log "Health check attempt $attempt/$max_attempts..."
        
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            success "Application is healthy!"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            error "Health check failed after $max_attempts attempts"
        fi
        
        sleep 10
        ((attempt++))
    done
    
    success "Deployment completed successfully"
}

# Rollback to previous version
rollback() {
    log "Starting rollback process..."
    
    if [[ ! -f "$BACKUP_DIR/latest_backup_path" ]]; then
        error "No backup found for rollback"
    fi
    
    ROLLBACK_DIR=$(cat "$BACKUP_DIR/latest_backup_path")
    
    if [[ ! -d "$ROLLBACK_DIR" ]]; then
        error "Backup directory not found: $ROLLBACK_DIR"
    fi
    
    # Stop current containers
    log "Stopping current containers..."
    docker-compose down --timeout 30
    
    # Restore previous image
    if [[ -f "$ROLLBACK_DIR/current_image.tar.gz" ]]; then
        log "Restoring previous image..."
        docker load < "$ROLLBACK_DIR/current_image.tar.gz"
    fi
    
    # Restore database
    if [[ -f "$ROLLBACK_DIR/database_backup.sql" ]]; then
        log "Restoring database..."
        docker-compose up -d postgres
        sleep 10
        docker exec -i jarvis-postgres psql -U jarvis -d jarvis_db < "$ROLLBACK_DIR/database_backup.sql"
    fi
    
    # Restore data
    if [[ -d "$ROLLBACK_DIR/data" ]]; then
        log "Restoring application data..."
        rm -rf data
        cp -r "$ROLLBACK_DIR/data" ./
    fi
    
    # Start containers
    log "Starting containers..."
    docker-compose up -d
    
    success "Rollback completed successfully"
}

# Cleanup old backups
cleanup_backups() {
    log "Cleaning up old backups..."
    
    # Keep only last 5 backups
    if [[ -d "$BACKUP_DIR" ]]; then
        cd "$BACKUP_DIR"
        ls -t backup_* 2>/dev/null | tail -n +6 | xargs -r rm -rf
        success "Old backups cleaned up"
    fi
}

# Main deployment process
main() {
    case "${1:-deploy}" in
        "deploy")
            log "Starting JARVIS-MK42 deployment process..."
            pre_deploy_checks
            create_backup
            deploy
            cleanup_backups
            success "Deployment process completed!"
            ;;
        "rollback")
            log "Starting rollback process..."
            rollback
            success "Rollback process completed!"
            ;;
        "backup")
            log "Creating manual backup..."
            create_backup
            success "Manual backup completed!"
            ;;
        "health")
            log "Performing health check..."
            if curl -f http://localhost:8000/health >/dev/null 2>&1; then
                success "Application is healthy!"
            else
                error "Application health check failed!"
            fi
            ;;
        *)
            echo "Usage: $0 {deploy|rollback|backup|health}"
            echo ""
            echo "Commands:"
            echo "  deploy   - Deploy new version (default)"
            echo "  rollback - Rollback to previous version"
            echo "  backup   - Create manual backup"
            echo "  health   - Check application health"
            exit 1
            ;;
    esac
}

# Trap for cleanup on exit
trap 'log "Deployment script interrupted"' INT TERM

# Run main function
main "$@"
