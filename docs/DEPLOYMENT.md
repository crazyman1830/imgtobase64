# 배포 가이드

이 가이드는 이미지 Base64 변환기 애플리케이션의 다양한 배포 옵션을 다룹니다.

## 목차

1. [개발 환경 배포](#개발-환경-배포)
2. [프로덕션 배포](#프로덕션-배포)
3. [Docker 배포](#docker-배포)
4. [클라우드 배포](#클라우드-배포)
5. [설정 관리](#설정-관리)
6. [모니터링 및 로깅](#모니터링-및-로깅)
7. [보안 고려사항](#보안-고려사항)
8. [성능 최적화](#성능-최적화)

## v2.0 아키텍처 개선사항

- **의존성 주입 컨테이너**: 모든 배포 환경에서 일관된 서비스 관리
- **통합 설정 시스템**: 환경별 설정 파일과 환경변수 지원
- **구조화된 로깅**: 프로덕션 환경에서 향상된 모니터링
- **메모리 최적화**: 대용량 파일 처리를 위한 스트리밍 지원
- **에러 처리 개선**: 사용자 친화적인 에러 메시지와 로깅

## 개발 환경 배포

### 빠른 시작

```bash
# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
python run_web.py

# 또는 사용자 정의 설정으로 실행
python run_web.py --config config.json --debug
```

### 개발 환경 기능

- **핫 리로드**: 코드 변경 시 자동 재시작
- **디버그 모드**: 상세한 에러 메시지 및 디버깅 도구
- **파일 로깅**: `./logs/` 디렉토리에 로그 저장
- **로컬 캐시**: `./cache/` 디렉토리의 디스크 기반 캐싱

### v2.0 개발 환경 개선사항

- **의존성 주입**: 개발 중 서비스 모킹 및 테스트 용이성
- **설정 팩토리**: 개발 환경별 설정 자동 로드
- **통합 로깅**: 개발 중 구조화된 로그 출력
- **에러 핸들러**: 개발 친화적인 상세 에러 정보

## 프로덕션 배포

### 사전 요구사항

- Python 3.7+
- Redis (캐싱 및 세션 저장용)
- Nginx (리버스 프록시 권장)
- SSL 인증서 (HTTPS용)

### 설치

```bash
# 저장소 복제
git clone <repository-url>
cd image-base64-converter

# 가상 환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 프로덕션 의존성 설치
pip install -r requirements.txt
pip install gunicorn  # 프로덕션 WSGI 서버용

# 환경 설정 복사 및 구성
cp .env.example .env
# 프로덕션 설정으로 .env 편집

# 필요한 디렉토리 생성
mkdir -p logs cache data temp
```

### v2.0 프로덕션 배포 개선사항

```bash
# 의존성 주입 컨테이너로 프로덕션 서버 실행
CONFIG_FILE=config.production.json python run_web.py --production

# 또는 환경변수로 설정
export ENVIRONMENT=production
export LOG_LEVEL=WARNING
export CACHE_MAX_SIZE_MB=500
python run_web.py
```

### Configuration

Create a production configuration file:

```bash
cp config.json config.production.json
# Edit config.production.json with production settings
```

Key production settings:
- Set `environment: "production"`
- Use strong `secret_key`
- Configure Redis for caching
- Set appropriate file size limits
- Enable security features
- Configure logging levels

### Running Production Server

```bash
# With Gunicorn (recommended)
python run_web.py --production --workers 4 --config config.production.json

# Or directly with Gunicorn
gunicorn --bind 0.0.0.0:8080 --workers 4 --worker-class eventlet src.web.web_app:app

# With systemd service (recommended for Linux)
sudo systemctl start image-converter
sudo systemctl enable image-converter
```

### Systemd Service

Create `/etc/systemd/system/image-converter.service`:

```ini
[Unit]
Description=Image Base64 Converter
After=network.target redis.service

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/image-converter
Environment=PATH=/opt/image-converter/venv/bin
ExecStart=/opt/image-converter/venv/bin/python run_web.py --production --config config.production.json
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Docker Deployment

### Single Container

```bash
# Build image
docker build -t image-converter .

# Run container
docker run -d \
  --name image-converter \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/cache:/app/cache \
  -e ENVIRONMENT=production \
  -e SECRET_KEY=your-secret-key \
  image-converter
```

### Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# Start with monitoring
docker-compose --profile monitoring up -d

# Start with Nginx reverse proxy
docker-compose --profile with-nginx up -d

# View logs
docker-compose logs -f app

# Scale application
docker-compose up -d --scale app=3
```

### Docker Compose Services

- **app**: Main application container
- **redis**: Cache and session storage
- **nginx**: Reverse proxy and load balancer (optional)
- **prometheus**: Metrics collection (optional)
- **grafana**: Monitoring dashboard (optional)

## Cloud Deployment

### AWS Deployment

#### Using AWS ECS

1. **Create ECR Repository**:
```bash
aws ecr create-repository --repository-name image-converter
```

2. **Build and Push Image**:
```bash
# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -t image-converter .
docker tag image-converter:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/image-converter:latest

# Push
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/image-converter:latest
```

3. **Create ECS Task Definition**:
```json
{
  "family": "image-converter",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "image-converter",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/image-converter:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "REDIS_URL", "value": "redis://your-redis-cluster:6379/0"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/image-converter",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### Using AWS Lambda (Serverless)

For serverless deployment, use AWS Lambda with API Gateway:

```bash
# Install Zappa
pip install zappa

# Initialize Zappa
zappa init

# Deploy
zappa deploy production
```

### Google Cloud Platform

#### Using Cloud Run

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT-ID/image-converter

# Deploy to Cloud Run
gcloud run deploy image-converter \
  --image gcr.io/PROJECT-ID/image-converter \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --set-env-vars ENVIRONMENT=production
```

### Microsoft Azure

#### Using Container Instances

```bash
# Create resource group
az group create --name image-converter-rg --location eastus

# Create container instance
az container create \
  --resource-group image-converter-rg \
  --name image-converter \
  --image your-registry/image-converter:latest \
  --dns-name-label image-converter-app \
  --ports 8080 \
  --environment-variables ENVIRONMENT=production \
  --cpu 1 \
  --memory 1
```

## Configuration Management

### Environment Variables

Set these environment variables for production:

```bash
# Required
export ENVIRONMENT=production
export SECRET_KEY=your-very-secure-secret-key
export REDIS_URL=redis://your-redis-server:6379/0

# Optional but recommended
export MAX_FILE_SIZE_MB=10
export ENABLE_SECURITY_SCAN=true
export CACHE_MAX_SIZE_MB=500
export LOG_LEVEL=WARNING
```

### Configuration Files

Use different configuration files for different environments:

- `config.json` - Development
- `config.production.json` - Production
- `config.staging.json` - Staging
- `config.testing.json` - Testing

### Secrets Management

For production, use proper secrets management:

- **AWS**: AWS Secrets Manager or Parameter Store
- **GCP**: Secret Manager
- **Azure**: Key Vault
- **Kubernetes**: Secrets
- **Docker**: Docker Secrets

## Monitoring and Logging

### Application Monitoring

1. **Health Checks**:
```bash
# Application health
curl http://localhost:8080/health

# Detailed status
curl http://localhost:8080/api/status
```

2. **Metrics Collection**:
- Enable Prometheus metrics
- Use Grafana for visualization
- Set up alerts for critical metrics

3. **Log Aggregation**:
- Use ELK Stack (Elasticsearch, Logstash, Kibana)
- Or Fluentd + Elasticsearch + Kibana
- Cloud solutions: AWS CloudWatch, GCP Logging, Azure Monitor

### Performance Monitoring

Monitor these key metrics:
- Response time
- Throughput (requests/second)
- Error rate
- Memory usage
- CPU utilization
- Cache hit rate
- Queue length

## Security Considerations

### Production Security Checklist

- [ ] Use HTTPS with valid SSL certificates
- [ ] Set strong secret keys
- [ ] Enable security scanning
- [ ] Configure rate limiting
- [ ] Set appropriate CORS policies
- [ ] Use secure headers (HSTS, CSP, etc.)
- [ ] Regular security updates
- [ ] Monitor for suspicious activity
- [ ] Implement proper authentication/authorization
- [ ] Use secure session management

### Nginx Configuration

Example Nginx configuration for reverse proxy:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files
    location /static/ {
        alias /opt/image-converter/src/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## Performance Optimization

### Application Optimization

1. **Caching Strategy**:
   - Use Redis for distributed caching
   - Implement cache warming
   - Set appropriate TTL values

2. **Database Optimization**:
   - Use connection pooling
   - Implement query optimization
   - Use read replicas for scaling

3. **Resource Management**:
   - Configure memory limits
   - Use streaming for large files
   - Implement proper garbage collection

### Infrastructure Optimization

1. **Load Balancing**:
   - Use multiple application instances
   - Implement health checks
   - Configure session affinity if needed

2. **CDN Integration**:
   - Serve static assets via CDN
   - Cache API responses where appropriate
   - Use edge locations for global performance

3. **Auto Scaling**:
   - Configure horizontal pod autoscaling (Kubernetes)
   - Use AWS Auto Scaling Groups
   - Monitor and adjust scaling policies

### Monitoring Performance

```bash
# Application metrics
curl http://localhost:8080/metrics

# System metrics
htop
iostat
netstat -tulpn
```

## Troubleshooting

### Common Issues

1. **Memory Issues**:
   - Check memory usage: `docker stats`
   - Increase memory limits
   - Enable memory optimization

2. **Performance Issues**:
   - Check cache hit rates
   - Monitor database connections
   - Analyze slow queries

3. **Connection Issues**:
   - Verify network connectivity
   - Check firewall rules
   - Validate SSL certificates

### Debug Commands

```bash
# Check application logs
docker-compose logs -f app

# Check Redis connectivity
redis-cli -h redis ping

# Test API endpoints
curl -X POST -F "file=@test.jpg" http://localhost:8080/api/convert/to-base64

# Monitor resource usage
docker stats
```

## Backup and Recovery

### Data Backup

1. **Application Data**:
```bash
# Backup data directory
tar -czf backup-$(date +%Y%m%d).tar.gz data/ logs/ cache/
```

2. **Redis Backup**:
```bash
# Create Redis backup
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb backup/redis-$(date +%Y%m%d).rdb
```

### Disaster Recovery

1. **Application Recovery**:
   - Restore from backup
   - Verify configuration
   - Test functionality

2. **Database Recovery**:
   - Restore Redis data
   - Verify data integrity
   - Test cache functionality

This deployment guide provides comprehensive instructions for deploying the Image Base64 Converter in various environments. Choose the deployment method that best fits your infrastructure and requirements.