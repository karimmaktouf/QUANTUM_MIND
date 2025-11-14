# 🚀 Guide de Déploiement - QUANTUM MIND v1.0

## Déploiement en Production

Ce guide couvre le déploiement de QUANTUM MIND sur un serveur Linux sécurisé.

### Table des matières
1. [Prérequis](#prérequis)
2. [Préparation du Serveur](#préparation-du-serveur)
3. [Configuration du Projet](#configuration-du-projet)
4. [Serveur Web (Nginx)](#serveur-web-nginx)
5. [Application WSGI (Gunicorn)](#application-wsgi-gunicorn)
6. [Superviseur (Systemd)](#superviseur-systemd)
7. [Base de Données](#base-de-données)
8. [Sécurité](#sécurité)
9. [Monitoring](#monitoring)
10. [Rollback](#rollback)

---

## Prérequis

- Serveur Linux (Ubuntu 22.04+ recommandé)
- Python 3.11+
- Accès root ou sudo
- Domaine configuré
- Certificat SSL/TLS (Let's Encrypt gratuit)

---

## Préparation du Serveur

### 1. Mise à jour système
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Installation des dépendances système
```bash
sudo apt install -y \
    python3-pip \
    python3-venv \
    nginx \
    supervisor \
    git \
    curl \
    wget \
    build-essential \
    python3-dev
```

### 3. Créer un utilisateur de service
```bash
sudo useradd -r -s /bin/bash quantum
sudo mkdir -p /home/quantum
sudo chown -R quantum:quantum /home/quantum
```

### 4. Cloner le projet
```bash
cd /home/quantum
sudo -u quantum git clone https://github.com/votre-username/QUANTUM_MIND.git
cd QUANTUM_MIND
```

---

## Configuration du Projet

### 1. Créer l'environnement virtuel
```bash
sudo -u quantum python3 -m venv venv
sudo -u quantum venv/bin/pip install --upgrade pip
sudo -u quantum venv/bin/pip install -r requirements.txt
```

### 2. Configuration .env (PRODUCTION)
```bash
sudo -u quantum cp .env.example .env
sudo -u quantum nano .env
```

**Contenu .env pour production** :
```env
# Gemini API
GOOGLE_API_KEY=your_gemini_api_key
SERPAPI_API_KEY=your_serpapi_key
HUGGINGFACE_API_TOKEN=your_hf_token

# Flask
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Secret Key (générer avec: python3 -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=your_generated_secret_key_here

# Database
DATABASE_PATH=/home/quantum/QUANTUM_MIND/data/quantum_mind.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=/home/quantum/QUANTUM_MIND/logs/quantum_mind.log

# Sécurité
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
```

### 3. Initialiser la base de données
```bash
sudo -u quantum venv/bin/python main.py  # Stop après initialisation (Ctrl+C)
```

---

## Serveur Web (Nginx)

### Configuration Nginx
Créer `/etc/nginx/sites-available/quantum-mind`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirection HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL/TLS
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Logs
    access_log /var/log/nginx/quantum-mind-access.log;
    error_log /var/log/nginx/quantum-mind-error.log;
    
    # Limits
    client_max_body_size 100M;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
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
        alias /home/quantum/QUANTUM_MIND/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### Activer la configuration
```bash
sudo ln -s /etc/nginx/sites-available/quantum-mind /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot certonly --nginx -d your-domain.com
```

---

## Application WSGI (Gunicorn)

### Installation
```bash
sudo -u quantum venv/bin/pip install gunicorn
```

### Fichier wsgi.py
Créer `/home/quantum/QUANTUM_MIND/wsgi.py`:

```python
import os
from app import create_app
from config.config import get_config

app = create_app(get_config(os.getenv('FLASK_ENV', 'production')))

if __name__ == "__main__":
    app.run()
```

### Configuration Gunicorn
Créer `/home/quantum/QUANTUM_MIND/gunicorn_config.py`:

```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 60
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

accesslog = "/home/quantum/QUANTUM_MIND/logs/access.log"
errorlog = "/home/quantum/QUANTUM_MIND/logs/error.log"
loglevel = "info"
```

---

## Superviseur (Systemd)

### Service Systemd
Créer `/etc/systemd/system/quantum-mind.service`:

```ini
[Unit]
Description=QUANTUM MIND
After=network.target

[Service]
Type=notify
User=quantum
WorkingDirectory=/home/quantum/QUANTUM_MIND
Environment="PATH=/home/quantum/QUANTUM_MIND/venv/bin"
ExecStart=/home/quantum/QUANTUM_MIND/venv/bin/gunicorn \
    --config gunicorn_config.py \
    --chdir /home/quantum/QUANTUM_MIND \
    wsgi:app

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Activation
```bash
sudo systemctl daemon-reload
sudo systemctl enable quantum-mind
sudo systemctl start quantum-mind
sudo systemctl status quantum-mind
```

### Logs
```bash
sudo journalctl -u quantum-mind -f
```

---

## Base de Données

### Backup quotidien
Créer `/home/quantum/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/quantum/backups"
DB_PATH="/home/quantum/QUANTUM_MIND/data/quantum_mind.db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp $DB_PATH $BACKUP_DIR/quantum_mind_$DATE.db
gzip $BACKUP_DIR/quantum_mind_$DATE.db

# Keep only last 7 days of backups
find $BACKUP_DIR -name "quantum_mind_*.db.gz" -mtime +7 -delete
```

### Cron job
```bash
sudo -u quantum crontab -e
```

Ajouter :
```
0 2 * * * /home/quantum/backup.sh
```

---

## Sécurité

### 1. Permissions
```bash
sudo chown -R quantum:quantum /home/quantum/quantum-mind
sudo chmod 750 /home/quantum/quantum-mind
sudo chmod 600 /home/quantum/quantum-mind/.env
```

### 2. Firewall
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 3. Fail2Ban
```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
```

### 4. Monitoring
```bash
sudo apt install htop iotop -y
```

---

## Monitoring

### Health Check
```bash
curl -I https://your-domain.com/
```

### Alertes
```bash
# Monitor disk usage
df -h

# Monitor memory
free -h

# Monitor logs
tail -100f /var/log/nginx/quantum-mind-error.log
```

---

## Rollback

### Revenir à une version précédente
```bash
cd /home/quantum/QUANTUM_MIND
git log --oneline
git checkout <commit-hash>
sudo systemctl restart quantum-mind
```

---

## Production Checklist

- [ ] `.env` configuré (SECRET_KEY, GOOGLE_API_KEY, SERPAPI, HF)
- [ ] SSL/TLS activé
- [ ] Database backup configuré
- [ ] Logs configurés
- [ ] Monitoring en place
- [ ] Firewall configuré
- [ ] Gunicorn en production (workers >= 2)
- [ ] Nginx configuré
- [ ] Systemd service actif
- [ ] Health checks en place
- [ ] Rate limiting configuré
- [ ] CORS approprié

---

**Version** : 1.0.0  
**Dernière mise à jour** : Novembre 2025

---

**Version** : 4.0.0  
**Dernière mise à jour** : Novembre 2025
