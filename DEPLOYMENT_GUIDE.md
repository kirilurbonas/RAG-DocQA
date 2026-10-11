# RAG-DocQA v2.0.0: Complete Deployment Guide

**Status:** ✅ Production Ready  
**Version:** 2.0.0  
**All 9 Phases Complete** with 218 passing tests

---

## Table of Contents

1. [Quick Start (Local)](#quick-start-local)
2. [Production Deployment](#production-deployment)
3. [Configuration](#configuration)
4. [Database Migrations](#database-migrations)
5. [Monitoring & Scaling](#monitoring--scaling)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start (Local)

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ & npm
- Python 3.11+

### Development Setup

```bash
# Clone and setup
git clone https://github.com/yourusername/RAG-DocQA.git
cd RAG-DocQA

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start dev server
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

**Access:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Production Deployment

### Option 1: Docker Compose (Recommended for Single Machine)

```bash
# Setup environment
cp backend/.env.example .env
# Edit .env with your settings:
# - DATABASE_URL=postgresql://user:pass@postgres:5432/rag_docqa
# - LLM_PROVIDER=openai
# - OPENAI_API_KEY=sk-...
# - JWT_SECRET=your-long-random-secret-key

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

**Services:**
- **Frontend:** http://localhost:80
- **API:** http://localhost:8000
- **PostgreSQL:** localhost:5432
- **Redis:** localhost:6379

### Option 2: Kubernetes (For Scaling)

```bash
# 1. Build and push images
docker build -t your-registry/rag-docqa-backend:v2.0.0 -f backend/Dockerfile.prod ./backend
docker build -t your-registry/rag-docqa-frontend:v2.0.0 -f frontend/Dockerfile.prod ./frontend

docker push your-registry/rag-docqa-backend:v2.0.0
docker push your-registry/rag-docqa-frontend:v2.0.0

# 2. Create K8s manifests (example structure)
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres-statefulset.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml

# 3. Check status
kubectl get pods -n rag-docqa
kubectl logs -f deployment/rag-docqa-backend -n rag-docqa
```

### Option 3: Cloud Platforms

**AWS ECS:**
```bash
# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com
docker tag rag-docqa-backend:v2.0.0 $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/rag-docqa-backend:v2.0.0
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/rag-docqa-backend:v2.0.0

# Create ECS task definition and service
# Configure RDS for PostgreSQL, ElastiCache for Redis
```

**Google Cloud Run:**
```bash
# Build and deploy backend
gcloud builds submit --tag gcr.io/$PROJECT_ID/rag-docqa-backend:v2.0.0 -f backend/Dockerfile.prod ./backend
gcloud run deploy rag-docqa-backend \
  --image gcr.io/$PROJECT_ID/rag-docqa-backend:v2.0.0 \
  --platform managed \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars DATABASE_URL=$DB_URL,REDIS_URL=$REDIS_URL
```

**Vercel (Frontend):**
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy frontend
cd frontend
vercel --prod
```

---

## Configuration

### Environment Variables

**Backend (.env):**
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/rag_docqa
SQLITE_DB=./rag_docqa.db  # Local development only

# Redis Cache
REDIS_URL=redis://localhost:6379

# LLM Configuration
LLM_PROVIDER=openai  # openai|anthropic|cohere|local
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
COHERE_API_KEY=...

# Security
JWT_SECRET=your-long-random-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# API Configuration
API_PORT=8000
WORKERS=4
ENV=production
ENABLE_API_DOCS=false
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_ASK=120/hour
RATE_LIMIT_UPLOAD=20/hour
RATE_LIMIT_READ=600/hour

# CORS
CORS_ALLOWED_ORIGINS=https://yourdomain.com

# Document Processing
MAX_UPLOAD_BYTES=10485760  # 10MB
MAX_DOCUMENT_SIZE_MB=100
CHUNK_SIZE=1024
```

**Frontend (.env):**
```bash
VITE_API_URL=https://api.yourdomain.com/api/v1
VITE_API_KEY=  # Optional, for public API access
```

### Docker Environment File

Create `.env.production`:
```bash
# Services
DB_USER=rag_user
DB_PASSWORD=secure_password_here
DB_NAME=rag_docqa

# Backend
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
JWT_SECRET=long-secret-key-here

# Compose
COMPOSE_PROJECT_NAME=rag-docqa
```

---

## Database Migrations

### Initial Setup

```bash
# The app automatically runs migrations on startup via Alembic
# This happens in the container entrypoint

# Manual migration (if needed)
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# View migration status
docker-compose -f docker-compose.prod.yml exec backend alembic current
```

### Creating New Migrations

```bash
# In development environment
cd backend
source .venv/bin/activate

# Auto-generate migration (SQLAlchemy detects changes)
alembic revision --autogenerate -m "add_new_table"

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Migration Structure

```
alembic/
├── versions/
│   ├── 001_initial_schema.py
│   ├── 002_add_feature_x.py
│   └── ...
├── env.py              # Environment setup
├── script.py.mako      # Migration template
└── alembic.ini         # Configuration
```

---

## Monitoring & Scaling

### Health Checks

```bash
# Backend health
curl http://localhost:8000/api/v1/health

# Example response
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "version": "2.0.0"
}
```

### Performance Monitoring

**Prometheus Metrics:**
```bash
# Metrics available at /metrics
curl http://localhost:8000/metrics
```

**Key Metrics:**
- `http_request_duration_seconds` - Request latency
- `http_requests_total` - Total requests by method/endpoint
- `rag_tokens_used_total` - LLM token usage
- `rag_documents_processed_total` - Documents uploaded

### Load Testing

```bash
# Using Locust (installed with requirements)
locust -f backend/scripts/load_test.py \
  --host=http://localhost:8000 \
  --users=100 \
  --spawn-rate=10 \
  --run-time=10m
```

### Scaling Configuration

**Horizontal Scaling:**
- **Backend:** Increase `WORKERS` in Gunicorn or add more replicas
- **Frontend:** Use CDN (CloudFront, Cloudflare) for static assets
- **Database:** PostgreSQL read replicas for read-heavy workloads
- **Cache:** Redis cluster for distributed caching

**Vertical Scaling:**
- Increase container memory: `--memory 4Gi`
- Increase CPU: `--cpu 4`
- Connection pool: `pool_size=20` in SQLAlchemy

---

## Troubleshooting

### Database Connection Issues

```bash
# Check database logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U rag_user -d rag_docqa -c "SELECT version();"

# Reset database (WARNING: destroys data)
docker-compose down -v
docker-compose up postgres -d
```

### Redis Connection Issues

```bash
# Check Redis
docker-compose exec redis redis-cli ping

# Clear cache if corrupted
docker-compose exec redis redis-cli FLUSHDB

# View connected clients
docker-compose exec redis redis-cli CLIENT LIST
```

### API Issues

```bash
# Check backend logs
docker-compose logs -f backend

# Test endpoints
curl -X GET http://localhost:8000/api/v1/health
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "SecurePass123"
  }'
```

### Migration Issues

```bash
# Check current migration status
docker-compose exec backend alembic current

# Downgrade to specific migration
docker-compose exec backend alembic downgrade 001_initial_schema

# View migration history
docker-compose exec backend alembic history
```

### Frontend Issues

```bash
# Check frontend logs
docker-compose logs -f frontend

# Clear cache
docker-compose exec frontend rm -rf /var/cache/nginx
docker-compose exec frontend nginx -s reload

# Verify API proxy
curl -v http://localhost/api/v1/health
```

---

## Performance Tuning

### Database Optimization

```sql
-- Enable query parallelization (PostgreSQL)
SET max_parallel_workers_per_gather = 4;
SET max_parallel_workers = 8;

-- Check query performance
EXPLAIN ANALYZE SELECT * FROM documents WHERE owner_id = '...';

-- Analyze table
ANALYZE documents;
```

### Redis Optimization

```bash
# Monitor Redis performance
docker-compose exec redis redis-cli --stat

# Check memory usage
docker-compose exec redis redis-cli INFO memory

# Adjust max memory policy
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Backend Optimization

```bash
# Increase worker processes (in docker-compose.prod.yml)
gunicorn app.main:app --workers 8 --worker-class uvicorn.workers.UvicornWorker

# Enable request compression
# Set in nginx.conf:
gzip on;
gzip_types application/json;
gzip_min_length 1024;
```

---

## Security Checklist

- [ ] Change default database password
- [ ] Generate strong JWT_SECRET (32+ characters)
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure CORS for your domain
- [ ] Set rate limiting appropriately
- [ ] Enable audit logging
- [ ] Regular database backups
- [ ] Monitor logs for suspicious activity
- [ ] Keep dependencies updated (`pip list --outdated`)
- [ ] Review API documentation and disable if not needed

---

## Backup & Recovery

### Database Backup

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U rag_user rag_docqa > backup.sql

# Restore from backup
docker-compose exec -T postgres psql -U rag_user rag_docqa < backup.sql
```

### Redis Backup

```bash
# Manual save
docker-compose exec redis redis-cli BGSAVE

# Copy backup file
docker-compose cp redis:/data/dump.rdb ./dump.rdb
```

### Restore from Backup

```bash
# Copy backup to container
docker-compose cp dump.rdb redis:/data/

# Restart Redis
docker-compose restart redis
```

---

## Support & Documentation

- **Issues:** https://github.com/yourusername/RAG-DocQA/issues
- **Documentation:** See README.md, PHASES_7_9_IMPLEMENTATION.md
- **API Reference:** http://localhost:8000/docs (Swagger UI)
- **Community:** Join Discord/Slack for discussions

---

**Last Updated:** 2026-10-11  
**Version:** 2.0.0  
**Status:** ✅ Production Ready
