# 🐳 Jarvis-MK42 Docker Deployment Guide

A comprehensive guide for deploying Jarvis-MK42 in a dockerized environment with full production capabilities.

## 📋 Quick Start

```bash
# 1. Clone and prepare
git clone <repository-url>
cd jarvis-mk42

# 2. Configure environment
cp .env.example .env
# Edit .env with your configuration (see below)

# 3. Deploy with Docker Compose
docker-compose up -d

# 4. Check deployment
docker-compose ps
docker-compose logs -f jarvis-app
```

## 🔧 Environment Configuration

### Required Environment Variables

Copy `.env.example` to `.env` and configure the following critical variables:

#### 🔐 Security Settings (REQUIRED)
```bash
# Generate a secure secret key
SECRET_KEY=your_32_character_secure_random_key

# Database passwords
POSTGRES_PASSWORD=your_secure_postgres_password_here
GRAFANA_PASSWORD=your_secure_grafana_password_here

# User authentication
ALLOWED_USERS=admin,your_username
ENFORCE_USERS=True

# Password hashes (generate with bcrypt)
admin=$2b$12$your_bcrypt_hash_here
your_username=$2b$12$your_bcrypt_hash_here
```

#### 🤖 AI Provider Keys (At least one required)
```bash
# LLM Providers - need at least one
OPENAI_API_KEY=sk-your_openai_key
DEEPSEEK_API_KEY=your_deepseek_key
GOOGLE_API_KEY=your_google_key
ANTHROPIC_API_KEY=your_anthropic_key

# Research APIs (optional)
SERPER_API_KEY=your_serper_key
PERPLEXITY_API_KEY=your_perplexity_key
```

#### 🗄️ Database Configuration
```bash
# Production database settings
DATABASE_URL=postgresql://jarvis:${POSTGRES_PASSWORD}@postgres:5432/jarvis_db
REDIS_URL=redis://redis:6379/0
```

### 🛠️ How to Generate Required Values

#### Secret Key Generation
```bash
# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Using OpenSSL
openssl rand -base64 32
```

#### Password Hash Generation
```bash
# Using Python/bcrypt
python -c "import bcrypt; print(bcrypt.hashpw(b'your_password', bcrypt.gensalt()).decode())"
```

## 🏗️ Architecture Overview

The Docker Compose setup includes:

| Service | Port | Purpose |
|---------|------|---------|
| `jarvis-app` | 8000 | Main Jarvis application |
| `jarvis-app` | 8001 | Health check endpoint |
| `postgres` | 5432 | PostgreSQL database |
| `redis` | 6379 | Cache and session storage |
| `prometheus` | 9090 | Metrics collection |
| `grafana` | 3000 | Monitoring dashboard |
| `nginx` | 80/443 | Reverse proxy & SSL |

## 🚀 Deployment Steps

### 1. Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 2GB RAM
- 10GB disk space

### 2. Environment Setup
```bash
# Create .env file
cp .env.example .env

# Edit with your favorite editor
nano .env
# or
code .env
```

### 3. SSL Configuration (Production)
```bash
# Create SSL directory
mkdir -p nginx/ssl

# Add your SSL certificates
cp your_cert.pem nginx/ssl/cert.pem
cp your_key.pem nginx/ssl/key.pem
```

### 4. Database Initialization
```bash
# The database will be automatically initialized on first run
# Custom SQL can be added to database/init.sql
```

### 5. Deploy Services
```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f jarvis-app
```

## 📊 Monitoring & Health Checks

### Built-in Health Checks
- **Application Health**: `http://localhost:8001/health`
- **Database Health**: Automatic PostgreSQL health monitoring
- **Redis Health**: Automatic Redis connectivity checks

### Monitoring Access
- **Grafana Dashboard**: `http://localhost:3000` (admin/`${GRAFANA_PASSWORD}`)
- **Prometheus Metrics**: `http://localhost:9090`
- **Application Logs**: `docker-compose logs -f jarvis-app`

### Health Check Commands
```bash
# Check all service health
docker-compose ps

# Detailed health status
curl http://localhost:8001/health

# Service-specific logs
docker-compose logs postgres
docker-compose logs redis
docker-compose logs jarvis-app
```

## 🔧 Common Operations

### Starting/Stopping Services
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart jarvis-app

# Update and restart
docker-compose pull
docker-compose up -d
```

### Database Operations
```bash
# Database backup
docker-compose exec postgres pg_dump -U jarvis jarvis_db > backup.sql

# Database restore
cat backup.sql | docker-compose exec -T postgres psql -U jarvis -d jarvis_db

# Connect to database
docker-compose exec postgres psql -U jarvis -d jarvis_db
```

### Log Management
```bash
# View real-time logs
docker-compose logs -f

# View specific service logs
docker-compose logs jarvis-app

# Log rotation (if needed)
docker-compose exec jarvis-app logrotate /etc/logrotate.d/jarvis
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Service Won't Start
```bash
# Check logs
docker-compose logs jarvis-app

# Check environment variables
docker-compose config

# Restart with fresh build
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### 2. Database Connection Issues
```bash
# Check database status
docker-compose exec postgres pg_isready -U jarvis

# Verify environment variables
echo $POSTGRES_PASSWORD

# Reset database
docker-compose down -v
docker-compose up -d
```

#### 3. Permission Issues
```bash
# Fix log directory permissions
sudo chown -R 1000:1000 logs/

# Fix data directory permissions  
sudo chown -R 1000:1000 data/
```

#### 4. SSL Certificate Issues
```bash
# Verify certificate files
ls -la nginx/ssl/

# Test certificate validity
openssl x509 -in nginx/ssl/cert.pem -text -noout
```

## 🔒 Security Considerations

### Production Security Checklist
- ✅ Change all default passwords
- ✅ Use strong SECRET_KEY
- ✅ Configure SSL certificates
- ✅ Set up firewall rules
- ✅ Enable log monitoring
- ✅ Regular security updates
- ✅ Backup encryption keys

### Network Security
```bash
# The docker-compose creates isolated network: jarvis-network (172.20.0.0/16)
# Only necessary ports are exposed to host
# Internal service communication is encrypted
```

## 📈 Performance Tuning

### Resource Limits
The default resource limits are:
- Memory: 512MB max, 256MB reserved
- CPU: 1.0 max, 0.5 reserved

Adjust in `docker-compose.yml` based on your needs:
```yaml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '2.0'
```

### Database Optimization
```bash
# Monitor database performance
docker-compose exec postgres psql -U jarvis -d jarvis_db -c "SELECT * FROM pg_stat_activity;"

# Adjust PostgreSQL settings in docker-compose.yml if needed
```

## 🔄 Updates & Maintenance

### Regular Maintenance
```bash
# Update containers
docker-compose pull
docker-compose up -d

# Clean up old images
docker image prune -f

# Database maintenance
docker-compose exec postgres vacuumdb -U jarvis -d jarvis_db --analyze
```

### Backup Strategy
```bash
# Automated backup script (add to cron)
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U jarvis jarvis_db | gzip > "backup_${DATE}.sql.gz"
find . -name "backup_*.sql.gz" -mtime +30 -delete
```

## 📞 Support

For issues and support:
1. Check logs: `docker-compose logs -f`
2. Review health checks: `curl http://localhost:8001/health`
3. Verify configuration: `docker-compose config`
4. Check resource usage: `docker stats`

---

**Note**: This guide assumes you have basic Docker knowledge. For production deployments, consider additional security hardening, monitoring, and backup strategies based on your specific requirements.
