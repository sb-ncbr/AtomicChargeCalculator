# TLS Certificates

Certbot runs on the Ubuntu host. Nginx runs in Docker and mounts `/etc/letsencrypt`
and `/var/www/certbot`. Do not use `certbot --nginx` to configure this container.

## Initial issuance

Set DNS and allow inbound TCP 80 before issuance. On a fresh host, with port 80
free, use standalone validation. For development:

```bash
sudo certbot certonly --standalone --cert-name acc-dev.biodata.ceitec.cz -d acc-dev.biodata.ceitec.cz
```

For production:

```bash
sudo certbot certonly --standalone --cert-name acc2.ncbr.muni.cz -d acc2.ncbr.muni.cz -d acc.biodata.ceitec.cz
```

Production Nginx uses the `acc2.ncbr.muni.cz` certificate directory for both names;
the certificate must cover both. Supply the requested contact information and agree
to the CA terms. Do not rerun standalone issuance against an existing busy server
without arranging port availability. Existing valid certificates need no reissue.

Once certificates exist, finish the [first deployment](./README.md#first-deployment).

## Webroot renewal

After Nginx is serving HTTP, switch each certificate to webroot renewal so future
renewals do not stop the website. With a Certbot version supporting `reconfigure`:

```bash
sudo certbot reconfigure --cert-name acc-dev.biodata.ceitec.cz --authenticator webroot --webroot-path /var/www/certbot
```

Use `acc2.ncbr.muni.cz` instead on production. Check `certbot reconfigure --help`;
if the Ubuntu package lacks this command, follow the installed version's documented
renewal-parameter procedure or upgrade Certbot. The repository
[domain.conf](../../src/deployment/certificates/renewal/domain.conf) shows renewal
parameters only: **do not overwrite the entire generated renewal file with it**.

Nginx serves `/.well-known/acme-challenge/` from `/var/www/certbot` on HTTP port 80.
DNS and that port must remain reachable for renewal.

## Reload hook and scheduler

From the repository root:

```bash
sudo install -d /etc/letsencrypt/renewal-hooks/deploy
sudo install -m 0755 src/deployment/certificates/renewal-hooks/deploy/reload-nginx.sh /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
sudo systemctl enable --now certbot.timer
systemctl status certbot.timer
```

The hook discovers a running container whose name contains `nginx` and reloads its
configuration. It assumes one such container on the host. No Compose path needs
editing. `certbot.service` is a oneshot; it need not stay active between timer runs.

## Verification

```bash
sudo certbot renew --dry-run
```

A dry run checks renewal but does not normally execute deploy hooks. Separately,
after validating the running Nginx configuration, test the installed reload hook:

```bash
docker exec acc-nginx nginx -t
sudo /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

Inspect command output for successful renewal and reload. Do not routinely force
real certificate renewals just to test setup; that can consume CA rate limits.
