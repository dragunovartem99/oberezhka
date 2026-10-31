# Обережка

A small Russian-language showcase for handmade dolls. Django 5.2 LTS, SQLite,
server-rendered HTML, plain CSS, and a Russian Django admin. No Node build step.

## Local development

Requires Python 3.13+ and uv.

```sh
uv sync --frozen
make migrate
DJANGO_DEBUG=1 uv run python manage.py import_photos /path/to/обережка --publish
DJANGO_DEBUG=1 uv run python manage.py createsuperuser
make run
```

Open http://127.0.0.1:8000 and http://127.0.0.1:8000/admin/.
The import command adds 12 items and 17 photographs, converts images to WebP,
and leaves existing items unchanged. Omit `--publish` to import as drafts.
It uses only the filenames, not invented biographies, prices, or historical descriptions.
The combined master/apprentice PNG is not imported because both have separate photographs.
Imported availability defaults to "На заказ" as a preview value: confirm availability
with the maker before going live.

Create an editor with access only to workshop content:

```sh
DJANGO_DEBUG=1 uv run python manage.py create_editor editor
```

Passwords are entered interactively. No default password is shipped. The editor can
manage dolls, photos, and workshop settings, but cannot manage users or permissions.
Keep the superuser account for yourself. In Settings, add the maker's own introduction,
ordering details, and actual contact link/email. No contact details are fabricated.

## Editing

- New items are drafts. Tick "Опубликовано" when ready; "На главной" selects homepage items.
- Add photographs inside the item form. The lowest position is the cover.
- JPEG, PNG, and WebP uploads are limited to 12 MB and 24 megapixels each; stored images
  are resized to at most 1800 px, converted to WebP, and stripped of EXIF metadata.
- Public pages hide drafts. Photos remain accessible through direct URLs, including draft
  and unpublished photos, and browsers can cache them for a year.
- Optional prices are in rubles. Stock state, materials, dimensions, and descriptions are editable.
- Images removed from records stay on disk deliberately; automatic deletion can break rollback.
  Reclaim orphaned files manually only after a backup.

## Checks

```sh
make check
DJANGO_DEBUG=1 uv run python manage.py makemigrations --check --dry-run
```

Tests cover draft page visibility, direct image access and caching, filtering, pagination, uploads,
contact escaping, admin editing, and editor permissions. CI also checks production settings.

## VPS deployment

Pushes to `main` and manual runs of `deploy.yaml` run CI, then deploy through
`pipes/deploy-vps` using the checkout strategy. First add the `oberezhka` DNS A
record pointing to your VPS.
This matches the Caddy + Docker approach in `infra`; port 50004 must be unused.

```sh
cp .env.example .env
# Replace DJANGO_SECRET_KEY with a unique random secret; never commit .env.
docker compose up -d --build --wait
docker compose exec oberezhka python manage.py createsuperuser
docker compose exec oberezhka python manage.py create_editor editor
bash deploy.sh
```

Run `python -c 'import secrets; print(secrets.token_urlsafe(64))'` locally to generate
a secret, then put it in `.env`. Caddy proxies to the loopback-only app port and
provides HTTPS. WhiteNoise serves collected static assets; Django streams the normalized
photos with a one-year public cache lifetime. Each upload gets a new UUID URL, so replacing
a photo does not reuse a cached image. For a small catalogue this is sufficient; consider a separate image service
or object storage if image traffic grows.

Photo sources must be copied to the VPS explicitly before import, for example to a
private temporary directory, then mounted read-only into a one-off container:

```sh
docker compose run --rm -v /absolute/path/to/photos:/import:ro oberezhka python manage.py import_photos /import
```

Review drafts, availability, content, and contacts before publishing.
Run `docker compose exec oberezhka python manage.py check --deploy --fail-level WARNING`
after configuration. The `infra` checkout inventory provisions the repository deploy key and the four
`VPS_*` GitHub secrets used by `pipes`. The project `.env` must exist on the server
before its first deployment.

## Backups and moving domains

`oberezhka-data` stores both `db.sqlite3` and `media/`. Back up the entire volume
while the app is stopped, or use a SQLite-consistent snapshot plus matching media.
The existing `infra` backup pauses containers and archives named volumes, so it can
include this one after deployment. Test restoration before depending on the backup.
Keep `.env` backed up privately too. Never use `docker compose down -v` on live data.

To move domains, change the Caddy hostname, `DJANGO_ALLOWED_HOSTS`,
`DJANGO_CSRF_TRUSTED_ORIGINS`, and the healthcheck Host; redirect the old hostname.
Content remains in the same volume.

## License

Application code is MIT licensed. The maker's photographs, doll designs, and personal
content are not licensed by this repository's software license. Production media and
database files are ignored by Git; obtain permission before redistributing photographs.
