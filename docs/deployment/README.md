# Deployment

The [Deploy (Manual) workflow](../../.github/workflows/deploy-manual.yml) updates an
existing installation over SSH. It does **not** provision a new server or start
PostgreSQL. Follow the bootstrap instructions before using it on a fresh host.

## Prepare an Ubuntu LTS host

These instructions assume an x86-64 Ubuntu LTS server with systemd, the SSH user
`ubuntu`, and one ACC installation per host. Paths and container names are fixed
in Compose and the workflow; selecting Development or Production does not isolate
two installations on one host. ChargeFW2 currently contains x86-64-specific paths.

1. Install Git, OpenSSH server, `ca-certificates`, `curl`, `util-linux` (for `flock`),
   `logrotate`, and `certbot` using Ubuntu packages. Install Docker Engine and the
   Compose v2/Buildx plugins using the [official Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/).
2. Enable Docker, SSH, and `logrotate.timer`. Grant `ubuntu` Docker access and
   reconnect before testing `docker ps` and `docker compose version`. Docker access
   is effectively root access. The workflow also requires noninteractive `sudo`
   for its Git commands; verify this setup before deployment.
3. Configure SSH key access for GitHub Actions. Ensure the server can fetch the
   repository and submodule, including when Git is invoked through `sudo`.
4. Point the configured DNS names at the host. Permit SSH and TCP 80/443; do not
   run a host web server that occupies those ports.

**Network warning:** the current deployment Compose file also publishes database
port 5432, API port 8000, and frontend port 3000 on all interfaces. Restrict these
through the infrastructure firewall or appropriately reviewed Docker-aware rules.
Do not assume UFW alone blocks Docker-published ports.

Clone the repository to `/home/ubuntu/AtomicChargeCalculator`, then run from that
checkout (replace the clone URL with the repository URL if creating it):

```bash
git submodule update --init --recursive
sudo install -d -m 0755 /home/acc /var/log/acc /var/www/certbot
sudo install -d -m 0755 -o root -g adm /var/log/acc/nginx
sudo touch /var/log/acc/nginx/access.log /var/log/acc/nginx/error.log
sudo chgrp adm /var/log/acc/nginx/access.log /var/log/acc/nginx/error.log
sudo chmod 0640 /var/log/acc/nginx/access.log /var/log/acc/nginx/error.log
sudo install -m 0644 -o root -g root src/deployment/nginx/logrotate /etc/logrotate.d/acc-nginx
sudo systemctl enable --now logrotate.timer
sudo logrotate --debug /etc/logrotate.d/acc-nginx
```

Inspect existing directories before changing permissions on an established host.
The logrotate debug command does not change files or test the reopen hook.

## Environment and secrets

Configure GitHub environments named **Development** and **Production**, with the
appropriate deployment secrets:

| Secret | Purpose |
| --- | --- |
| `SSH_HOST` | Target server |
| `SSH_USERNAME` | Deployment user, normally `ubuntu` |
| `SSH_PRIVATE_KEY` | Key authorized on that server |
| `SSH_PORT` | Optional; defaults to 22 |
| `DB_PASSWORD` | PostgreSQL password |
| `OIDC_CLIENT_ID` | Registered Life Science client |
| `OIDC_CLIENT_SECRET` | Life Science client secret |

For manual bootstrap, securely export `DB_PASSWORD`, `OIDC_CLIENT_ID`, and
`OIDC_CLIENT_SECRET` in the shell as well. Do not commit credentials or include
them in shared terminal output. The workflow does not create a server `.env` file.
Current workflow exports interpolate secrets into shell commands, and the database
password is embedded in a connection URL. Shell-special characters and URL-reserved
characters are not safely supported by that implementation; review compatibility
before deployment rather than weakening credential strength.

For **Development**, also export:

```bash
export VITE_BASE_API_URL=https://acc-dev.biodata.ceitec.cz:443/api/v1
export OIDC_BASE_URL=https://acc-dev.biodata.ceitec.cz/
export OIDC_REDIRECT_URL=https://acc-dev.biodata.ceitec.cz/api/v1/auth/callback
export NGINX_CONFIG_FILE=nginx.dev.conf
```

For **Production**, use:

```bash
export VITE_BASE_API_URL=https://acc.biodata.ceitec.cz:443/api/v1
export OIDC_BASE_URL=https://acc.biodata.ceitec.cz/
export OIDC_REDIRECT_URL=https://acc.biodata.ceitec.cz/api/v1/auth/callback
export NGINX_CONFIG_FILE=nginx.prod.conf
```

Register the matching callback with Life Science. The frontend API URL is baked
into its image at build time. Both deployments use the database name `postgres_prod`
and user `prod_user` on their respective hosts. Changing `DB_PASSWORD` does not
change the password in an already initialized PostgreSQL volume.

## First deployment

Obtain [initial TLS certificates](./certificate-renewal.md) before starting Nginx.
The production configuration needs a certificate covering both public hostnames.

From the repository root, with the environment above set:

```bash
docker build -t chargefw2-base:acc -f ChargeFW2/Dockerfile ChargeFW2
cd src/deployment
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d db
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps db
```

Wait until PostgreSQL is healthy, then build and start the application:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build api web
docker logs --tail 100 acc-api
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm --no-deps --pull never nginx nginx -t
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --pull never nginx
```

Check API startup logs for successful database migrations and application startup;
a running container alone does not establish that migrations succeeded. Verify
HTTPS, API calls, example viewing, and login. Complete certificate renewal setup.

Use **both** Compose files on hosted dev and production. Bare `docker compose`
loads the local-development override. Nginx preflight needs existing certificates,
host log setup, a locally available Nginx image, and running/resolvable `api` and
`web` services. Consequently, selecting every GitHub deployment option on an empty
host is not a substitute for this bootstrap.

## Subsequent GitHub deployments

Open **Actions > Deploy (Manual) > Run workflow**. Select the target environment,
the workflow revision, the branch to deploy, and the required checkboxes:

- **Rebuild ChargeFW2:** builds the base image; also select **Deploy API** to use it.
- **Deploy API:** builds and recreates the API container.
- **Deploy Web:** builds and recreates the frontend container.
- **Deploy Nginx:** checks logging prerequisites and tests the candidate Nginx
  configuration before service updates, then recreates Nginx.

All checkboxes default to false. The [deployment logic](../../.github/workflows/deploy-logic.yml)
resets the server checkout to the selected branch; do not keep uncommitted work
there. A host lock rejects overlapping workflow deployments. Deployments are not
zero-downtime and API recreation can interrupt jobs. Use a maintenance window when
necessary. Nginx uses `--pull never`; explicitly pull a chosen image before deploying
an image update. Restarting a container does not apply changed Compose mounts.

## Logging maintenance

After deployment, verify that website requests appear as JSON in
`/var/log/acc/nginx/access.log`. Check that `logrotate.timer` remains active and
monitor available disk space. To test rotation, use the development server:

```bash
sudo logrotate --force /etc/logrotate.d/acc-nginx
```

Make another request and confirm it appears in the replacement `access.log`.
This exercises the log reopen hook without restarting Nginx. Normal rotation is
scheduled automatically; forced rotation is only a verification step.

## Persistence and retention

- Nginx access/error logs live in host `/var/log/acc/nginx`; monthly rotation keeps
  24 archives and compresses older files. Empty files are skipped. This is not a
  hard size limit; monitor disk space and copy historical logs off-server.
- Nginx stdout/stderr remains available through `docker logs`, bounded by Docker's
  configured rotation. These diagnostics are removed with the container;
  persistent access/error files are separate from Docker logs.
- API logs remain in host `/var/log/acc/logs.log`; the Nginx rotation rule does not
  rotate that file. Calculation data remains under host `/home/acc`.
- PostgreSQL uses named volume `deployment_db-data` with the default project name.
  Never use `docker compose down -v` or remove that volume to perform an update.

Host logs and volumes survive container recreation, not host loss. Arrange and test
off-server backups separately.

## Usage reports

Generate a local report over SSH; the tool does not change the server. Examples:

```bash
python3 utils/usage_stats.py --server prod --year 2026 --output /tmp/acc-2026
python3 utils/usage_stats.py --server prod --database --start-date 2026-07-01 --end-date 2026-10-01 --output /tmp/acc-q3
```

Use `--year` for a calendar year, or `--start-date` and exclusive `--end-date` for a
UTC interval. Add `--database` for method, molecules-per-submission, and molecule-size
summaries. The report is useful for checking web traffic, calculation activity, or the
mix of small and large inputs. Database dates mean record creation; method counts do
not distinguish cached results from new calculations. Large-input categories are not
chemical classifications, and actual computation runtimes are not recorded.
Nginx results distinguish all IPs from IPs on requests not flagged by the known-bot
heuristic; calculation submissions are shown separately. API logs lack user agents,
so bot-excluded API counts are unavailable.
New frontend requests carry a `web-app` marker; reports separate marked, unmarked,
and older requests with no marker. Unmarked does not necessarily mean scripted.

Reports contain `report.txt`, `report.json`, and `monthly.csv`; raw IP addresses are
never included. Choose a new output directory for each run. See `--help` for offline
log inputs and other options.
