# Deployment

For hosted development or production, follow the
[Ubuntu host setup, bootstrap, and GitHub Actions guide](../../docs/deployment/README.md).
The deployment workflow updates an existing installation; it does not provision it.

## Local Docker setup

Run from the repository root:

```bash
git submodule update --init --recursive
docker build -t chargefw2-base:acc -f ChargeFW2/Dockerfile ChargeFW2
cd src/deployment
docker compose up -d --build
```

This starts four services: PostgreSQL, API, frontend, and Nginx. Access the UI through
`http://localhost:8080`. Local OIDC credentials and callback settings are placeholders;
working Life Science login needs a registered client and appropriate configuration.

To stop the local stack without deleting database volumes:

```bash
docker compose down
```

On Windows, an API startup error such as `exec /acc/entrypoint.sh: no such file or
directory` can result from CRLF line endings. Ensure `src/backend/entrypoint.sh`
uses Unix line endings.

## Configuration files

- `docker-compose.yml`: base services and PostgreSQL volume.
- `docker-compose.override.yml`: automatically loaded local-development settings.
- `docker-compose.prod.yml`: explicitly selected for both hosted dev and production;
  requires host directories, credentials, and certificates described in the guide.
- `nginx/nginx.local.conf`, `nginx/nginx.dev.conf`, `nginx/nginx.prod.conf`: Nginx
  configurations with shared declarations under `nginx/snippets/`.
- `nginx/logrotate`: host rotation rule, installed as `/etc/logrotate.d/acc-nginx`.

For hosted deployments always specify `-f docker-compose.yml -f docker-compose.prod.yml`.
Do not use the host Certbot Nginx plugin to configure the container; follow the
[initial certificate and renewal instructions](../../docs/deployment/certificate-renewal.md).
