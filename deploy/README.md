# Deploy

Production deployment via Docker Compose. Runs Caddy (TLS + reverse proxy) and Postgres (pgvector).

## First-time setup on a new VPS

1. Install Docker: https://docs.docker.com/engine/install/
2. Clone this repo to `/opt/dynachat/` (owned by a dedicated `dynachat` user, `chmod 700`)
3. Copy `.env.example` to `.env`, fill in real values (`chmod 600`)
4. Point DNS A record for your subdomain at the VPS public IP
5. `cd deploy && docker compose up -d`
6. Caddy auto-provisions a Let's Encrypt cert on first request

## Files

- `docker-compose.yml` - Caddy + Postgres services
- `Caddyfile` - reverse-proxy config (TLS + subdomain routing)
- `.env.example` - secret template (committed); real `.env` is gitignored

## Ports

- `80` / `443` (public) - Caddy
- `127.0.0.1:5433` (loopback only) - Postgres

## Secret hygiene

The real `.env` lives ONLY on the deploy host, in a directory owned by a non-factory user with mode 600. It is never committed, never shared via chat, and never readable by the Dark Factory workflow user.
