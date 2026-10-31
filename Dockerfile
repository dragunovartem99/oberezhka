FROM python:3.13-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.13-slim
RUN useradd --system --uid 10001 app && mkdir /data && chown app /data
WORKDIR /app
COPY --from=build /app/.venv .venv
COPY config config
COPY catalog catalog
COPY templates templates
COPY static static
COPY manage.py ./
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 DATA_DIR=/data
RUN DJANGO_DEBUG=1 python manage.py collectstatic --noinput
USER app
EXPOSE 50004
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:50004 --workers 1 --threads 4 --access-logfile - --error-logfile -"]
