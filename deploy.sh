#!/bin/bash
set -euo pipefail

docker compose up -d --build --wait
sudo cp Caddyfile /etc/caddy/sites/oberezhka.caddy
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
