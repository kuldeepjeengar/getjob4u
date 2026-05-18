# AWS Deployment Guide — getjob4u

Three deployment options, ranked by simplicity and cost. **All three fit comfortably in AWS Free Tier** for your first year.

---

## Option 1 — Elastic Beanstalk (Recommended for beginners)

**Why:** Easiest. AWS handles the server, load balancer, scaling. You just push code.

**Cost:** Free tier covers 750 hours/month of `t2.micro` + EBS storage for 12 months. After that ~$10-15/mo for a single instance.

### Step 1 — Prep the code

Create `Procfile` in project root:

```
web: uvicorn main:app --host 0.0.0.0 --port 8000
```

Export a `requirements.txt` from `uv`:

```bash
uv pip compile pyproject.toml -o requirements.txt
```

(Elastic Beanstalk's Python platform reads `requirements.txt`, not `pyproject.toml`.)

### Step 2 — Install EB CLI

```bash
pip install awsebcli
```

### Step 3 — Initialize and deploy

```bash
cd first_project
eb init -p python-3.11 getjob4u --region us-east-1
eb create getjob4u-env --instance-type t2.micro
```

This takes ~5 minutes. EB returns a URL like `getjob4u-env.eba-xxx.us-east-1.elasticbeanstalk.com`.

### Step 4 — Update later

```bash
eb deploy
```

### Step 5 — Custom domain (optional)

Buy a domain in Route 53 (~$12/year) and point a CNAME to the EB URL.

---

## Option 2 — EC2 + nginx + systemd (Most control)

**Why:** Cheaper long-term. Full control over the server. Good for learning Linux/devops.

**Cost:** Free tier covers 1 `t2.micro` instance for 12 months. After that ~$8/mo.

### Step 1 — Launch the instance

1. AWS Console → EC2 → Launch Instance.
2. AMI: **Ubuntu 22.04 LTS**.
3. Type: **t2.micro** (free tier).
4. Create key pair, download `.pem` file.
5. Security group: allow SSH (22), HTTP (80), HTTPS (443).
6. Launch.

### Step 2 — SSH in

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@<EC2-PUBLIC-IP>
```

### Step 3 — Install dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx git
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

### Step 4 — Clone and install

```bash
cd /home/ubuntu
git clone <your-repo-url> getjob4u   # or scp the folder
cd getjob4u
uv sync
```

### Step 5 — systemd service

`/etc/systemd/system/getjob4u.service`:

```ini
[Unit]
Description=getjob4u FastAPI app
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/getjob4u
ExecStart=/home/ubuntu/.local/bin/uv run uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable getjob4u
sudo systemctl start getjob4u
sudo systemctl status getjob4u
```

### Step 6 — nginx reverse proxy

`/etc/nginx/sites-available/getjob4u`:

```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 6M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/getjob4u /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### Step 7 — HTTPS (Let's Encrypt)

Once you have a domain pointing to the EC2 IP:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

Auto-renews via cron. Free forever.

---

## Option 3 — AWS App Runner (Zero ops, pay-per-use)

**Why:** Push container, get URL. No servers. Scales to zero when idle.

**Cost:** ~$5/mo idle + per-request charges. No free tier but very cheap for low traffic.

### Step 1 — Add a Dockerfile

`Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 2 — Push to ECR

```bash
aws ecr create-repository --repository-name getjob4u
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -t getjob4u .
docker tag getjob4u:latest <account>.dkr.ecr.us-east-1.amazonaws.com/getjob4u:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/getjob4u:latest
```

### Step 3 — Create App Runner service

AWS Console → App Runner → Create service → Container registry → pick the image. App Runner gives you an HTTPS URL automatically.

---

## Database considerations

SQLite is fine for **<1000 daily users**. The file lives on the instance disk.

### When to migrate to RDS

- Going multi-instance (load-balanced) — SQLite doesn't work across instances.
- Need durable backups.
- Heavy concurrent writes.

### Migration path

1. AWS RDS → Create database → **PostgreSQL** → free tier `db.t3.micro` (free for 12 months).
2. Change `DATABASE_URL` in `database.py`:
   ```python
   DATABASE_URL = "postgresql://user:pass@host:5432/getjob4u"
   ```
3. Install: `uv add psycopg2-binary`
4. Run migrations (SQLAlchemy will create tables on startup).

### Don't store uploads on disk

This app never persists uploaded resumes (it parses in memory and drops the bytes). If you change that, use **S3** — free tier 5GB.

---

## Environment variables

For production, move these out of code:

```bash
DATABASE_URL=postgresql://...
ALLOWED_HOSTS=yourdomain.com
DEBUG=false
```

EB: set via console → Configuration → Software → Environment properties.
EC2: add to `/etc/systemd/system/getjob4u.service` as `Environment="KEY=value"`.
App Runner: set via console → service → Configuration.

---

## Cost summary

| Option | Year 1 (free tier) | After free tier |
|---|---|---|
| Elastic Beanstalk (t2.micro) | $0 | ~$10-15/mo |
| EC2 (t2.micro) + nginx | $0 | ~$8/mo + $12/yr domain |
| App Runner | ~$5/mo idle + usage | Same |
| RDS PostgreSQL (db.t3.micro) | $0 (12 mo) | ~$15/mo — skip until needed |
| S3 (uploads) | 5GB free | $0.023/GB/mo — negligible |
| Route 53 (domain) | $12/year | $12/year |

**Cheapest path: EC2 free tier + SQLite + Let's Encrypt = $0 for year 1, ~$8/mo after.**

---

## Production checklist

- [ ] Switch `DATABASE_URL` to env var
- [ ] Set `DEBUG=false` (FastAPI doesn't expose stack traces by default, but disable `--reload`)
- [ ] Add rate limiting (e.g., `slowapi`)
- [ ] Set up CloudWatch logs (EB does this automatically)
- [ ] Configure a domain + HTTPS
- [ ] Add a `robots.txt` (currently absent)
- [ ] Set up daily backups of SQLite file (or use RDS automated backups)
- [ ] Add basic monitoring — uptime alert (UptimeRobot is free)
- [ ] Add Google Analytics or Plausible for traffic insights

---

## Troubleshooting

**App returns 502/504 in nginx:** Check `sudo systemctl status getjob4u`. The Python app might have crashed on startup. View logs: `sudo journalctl -u getjob4u -n 100`.

**`uv: command not found` when service starts:** systemd doesn't load your shell profile. Either hard-code the full path (`/home/ubuntu/.local/bin/uv`) in `ExecStart`, or install uv system-wide.

**Resume upload fails with "Request Entity Too Large":** Bump `client_max_body_size` in nginx (already set to 6M above).

**SQLite "database is locked":** You're running multiple instances. Switch to PostgreSQL.
