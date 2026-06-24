# Single-image stack: Python poller + restic + supercronic scheduler.
# Build context is the repo root (see release/compose.yaml).
FROM python:3.13-slim

# Pinned third-party binaries (checksums verified at build time).
ARG RESTIC_VERSION=0.19.0
ARG RESTIC_SHA256=13176fe6d89d4357947a2cd107218ab2873a5f9d8e1ac2d4cd1c8e07e6839c21
ARG SUPERCRONIC_VERSION=v0.2.46
ARG SUPERCRONIC_SHA1=5bcefed628e32adc08e32634db2d10e9230dbca0

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl bzip2 tini; \
    rm -rf /var/lib/apt/lists/*; \
    # restic
    curl -fsSL -o /tmp/restic.bz2 \
        "https://github.com/restic/restic/releases/download/v${RESTIC_VERSION}/restic_${RESTIC_VERSION}_linux_amd64.bz2"; \
    echo "${RESTIC_SHA256}  /tmp/restic.bz2" | sha256sum -c -; \
    bunzip2 /tmp/restic.bz2; \
    install -m 0755 /tmp/restic /usr/local/bin/restic; \
    rm -f /tmp/restic; \
    # supercronic
    curl -fsSL -o /usr/local/bin/supercronic \
        "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64"; \
    echo "${SUPERCRONIC_SHA1}  /usr/local/bin/supercronic" | sha1sum -c -; \
    chmod 0755 /usr/local/bin/supercronic

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY release/crontab /app/crontab

ENV FGB_STAGING_DIR=/staging
RUN mkdir -p /staging
VOLUME ["/staging"]

# tini reaps zombies and forwards signals to supercronic.
ENTRYPOINT ["tini", "--"]
CMD ["supercronic", "/app/crontab"]
