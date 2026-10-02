FROM chargefw2-base:acc

USER root

COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /usr/local/bin/uv

ENV UV_PYTHON_DOWNLOADS=never
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    gcc \
    python3-dev \
    libpq-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /acc
COPY uv.lock pyproject.toml ./
RUN uv sync --locked --no-cache --python /usr/bin/python3

COPY ./app /acc/app
COPY ./entrypoint.sh /acc/
RUN chmod +x /acc/entrypoint.sh

ENTRYPOINT ["/acc/entrypoint.sh"]
