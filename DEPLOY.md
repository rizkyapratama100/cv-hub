# Deployment Guide

This project uses a split hosting model:
- **Frontend** → Cloudflare Pages (free, global CDN)
- **Backend** → AWS Lightsail $3.50/month instance (always-on, no cold starts)

---

## Prerequisites

- AWS account
- Cloudflare account (free)
- GitHub repository with this code pushed to it
- Git installed on your local machine

---

## Part 1 — AWS Lightsail (Backend)

### 1.1 Create the instance

1. Go to [AWS Lightsail](https://lightsail.aws.amazon.com)
2. Click **Create instance**
3. Choose:
   - **Platform:** Linux/Unix
   - **Blueprint:** OS Only → **Ubuntu 22.04 LTS**
   - **Bundle:** $3.50/month (512 MB RAM, 2 vCPUs, 20 GB SSD) — IPv6 only
   - **Instance name:** `cv-showcase`
4. Click **Create instance**

> **Note:** The $3.50 plan uses IPv6 only. If a recruiter's network doesn't support IPv6, upgrade to the $5 plan (1 GB RAM, IPv4+IPv6). The $5 plan also gets 3 months free.

### 1.2 Configure networking

1. On the instance page, click **Networking**
2. Under **IPv6 Firewall**, ensure **HTTP (port 80)** is open
3. Note your instance's **Public IPv6 address** for DNS setup later

### 1.3 Connect and set up the instance

Click **Connect using SSH** in the Lightsail console, or use your own SSH client.

```bash
# 1. Update system
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install Docker
curl -fsSL https://get.docker.com | sudo bash
sudo usermod -aG docker ubuntu
newgrp docker

# 3. Install Git
sudo apt-get install -y git

# 4. Enable swap (critical for 512MB RAM)
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 5. Clone the repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git ~/cv-showcase
cd ~/cv-showcase

# 6. Set up environment
cp .env.example .env
nano .env
# → Set ALLOWED_ORIGINS to your Cloudflare Pages URL (get this in Part 2)
# → Save with Ctrl+X, Y, Enter
```

### 1.4 Deploy the backend

```bash
cd ~/cv-showcase
bash deploy.sh
```

You should see: `✓ Backend healthy (HTTP 200)`

### 1.5 Test the backend

```bash
curl http://localhost/health
# → {"status":"ok","service":"cv-showcase-backend"}

curl http://localhost/processors
# → {"processors":[...]}
```

---

## Part 1.6 — Cloudflare Tunnel (Required for HTTPS)

Cloudflare Pages serves over HTTPS. Browsers block HTTP requests from HTTPS pages
(mixed content policy). You need HTTPS on the backend.

The free solution is a **Cloudflare Tunnel** — it gives your backend a public
`https://*.trycloudflare.com` URL with no domain or certificate needed.

SSH into your Lightsail instance and run:

```bash
# 1. Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
sudo dpkg -i cloudflared.deb

# 2. Start a persistent tunnel pointing at your local backend on port 80
# This prints a https://*.trycloudflare.com URL — copy it
cloudflared tunnel --url http://localhost:80 --no-autoupdate &

# The URL printed looks like: https://something-random.trycloudflare.com
# Copy that URL
```

> **Note:** The free `trycloudflare.com` URL changes every time cloudflared restarts.
> For a stable URL, see Part 1.7 (named tunnel with a free Cloudflare account).

Once you have the tunnel URL:
1. Go back to Cloudflare Pages → your project → **Settings → Environment Variables**
2. Update `VITE_API_URL` to the tunnel URL, e.g. `https://something-random.trycloudflare.com`
3. Update `ALLOWED_ORIGINS` on the Lightsail instance to your Pages URL, restart container
4. Retrigger a Pages deployment

---

## Part 1.7 — Named Tunnel (Stable URL, Recommended)

A named tunnel gives you a permanent `https://backend.yourdomain.com` URL.
Requires a domain added to Cloudflare (free plan works).

```bash
# On the Lightsail instance:

# 1. Authenticate cloudflared with your Cloudflare account
cloudflared tunnel login
# → Opens a browser URL — open it on your machine and authorize

# 2. Create a named tunnel
cloudflared tunnel create cv-showcase-backend

# 3. Note the tunnel ID printed (looks like: a1b2c3d4-...)
TUNNEL_ID="YOUR_TUNNEL_ID_HERE"

# 4. Create tunnel config
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << EOF
tunnel: $TUNNEL_ID
credentials-file: /home/ubuntu/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: backend.yourdomain.com
    service: http://localhost:80
  - service: http_status:404
EOF

# 5. Add DNS record (creates backend.yourdomain.com → tunnel)
cloudflared tunnel route dns cv-showcase-backend backend.yourdomain.com

# 6. Install as a system service (auto-starts on reboot)
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

Then:
1. Set `VITE_API_URL=https://backend.yourdomain.com` in Cloudflare Pages env vars
2. Set `ALLOWED_ORIGINS=https://your-pages-project.pages.dev` on Lightsail
3. Redeploy Pages



### 2.1 Create the Pages project

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages**
2. Click **Create** → **Pages** → **Connect to Git**
3. Connect your GitHub account and select your repository
4. Configure the build:
   - **Framework preset:** None (or Vite)
   - **Build command:** `npm run build`
   - **Build output directory:** `dist`
   - **Root directory:** `frontend`
5. Under **Environment variables**, add:
   ```
   VITE_API_URL = http://[YOUR_LIGHTSAIL_IPV6_ADDRESS]
   ```
   Format the IPv6 address with brackets, e.g.: `http://[2600:1f18:abc:def::1]`
6. Click **Save and Deploy**

> Cloudflare will give you a URL like `https://cv-showcase-abc.pages.dev`. Copy it.

### 2.2 Update CORS on the backend

Back on your Lightsail instance:

```bash
cd ~/cv-showcase
nano .env
# → Set ALLOWED_ORIGINS=https://cv-showcase-abc.pages.dev
# → Save

docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

### 2.3 Verify end-to-end

Open your Cloudflare Pages URL in a browser, upload an image or video, and confirm processing works.

---

## Part 3 — Optional: Custom Domain

If you have a domain managed on Cloudflare:

1. In Cloudflare Pages → your project → **Custom domains**
2. Add your domain (e.g. `cv.yourdomain.com`)
3. Cloudflare handles DNS and TLS automatically
4. Add the custom domain to `ALLOWED_ORIGINS` in your `.env` on Lightsail and redeploy

---

## Updating the Backend

Whenever you push new code, SSH into your Lightsail instance and run:

```bash
cd ~/cv-showcase && bash deploy.sh
```

Cloudflare Pages redeploys automatically on every push to your main branch.

---

## Monitoring

Check container health:
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=50
```

Check memory usage (important for 512MB instance):
```bash
free -h
docker stats --no-stream
```

If memory is consistently above 400MB, upgrade to the $5/month plan (1GB RAM) in Lightsail.

---

## Upgrading the Lightsail Plan

If you need more RAM later (e.g. for heavier CV models):

1. Lightsail console → your instance → **Snapshots** → **Create snapshot**
2. Once snapshot is complete → **Create new instance from snapshot**
3. Choose the $5 or $10 plan
4. Update DNS to point to the new instance IP
5. Delete the old instance once verified

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Frontend can't reach backend | Wrong IPv6 in `VITE_API_URL` | Check Lightsail IP, update Cloudflare env var, redeploy Pages |
| CORS error in browser | `ALLOWED_ORIGINS` doesn't match Pages URL | Update `.env` on Lightsail, restart container |
| Backend OOM crash | Too much video processing | Enable swap (Part 1.3), or upgrade plan |
| 502 on backend routes | Container not running | SSH in, run `bash deploy.sh` |
