# Certificate Renewal
The following doc describes a way to automatically renew SSL certificates using `certbot` and `systemd`.

## Systemd Configuration
Certbot relies on `certbot.timer` and `certbot.service` services to automatically renew certificates. Verify that both are running on your system: 

```bash
$ sudo systemctl status certbot.timer
$ sudo systemctl status certbot.service

# List running certbot timers:
$ sudo systemctl list-timers | grep certbot
```

### Webroot Configuration
So that we don't have to stop the nginx container to free up the port 80 (used by certbot for certificate renewal), we can configure it to use `webroot` authenticator instead.

Use the configuration from [domain.conf](/deployment/certificates/renewal/domain.conf) in `/etc/letsencrypt/renewal/<your-domain>.conf` on your system.

This will use the already running nginx for verification, instead of spinning up a temporary HTTP server in the case of `standalone` authenticator.

## Reloading Nginx
Once the certificate is renewed (deployed) we need to reload Nginx configuration. This can be achieved with the `deploy` certbot hook. Add the [reload-nginx.sh](/deployment/certificates/renewal-hooks/deploy/reload-nginx.sh) script to the `renewal-hooks` directory on your system:
```bash
$ cp deployment/certificates/renewal-hooks/deploy/reload-nginx.sh /etc/letsencrypt/renewal-hooks/deploy
$ chmod +x /etc/letsencrypt/renewal-hooks/deploy
```

> _Note:_ Don't forget to adjust the path to the `docker-compose.yml` file on your system, if it differs.

## Testing 
To test if the setup works, you can force the certificate renewal:

```bash
$ sudo certbot renew --cert-name <your-domain> --force-renew
```

If everything worked as expected, you should see the new certificate (e.g. when navigating to the page).