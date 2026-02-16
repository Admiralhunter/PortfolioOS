# PortfolioOS — Dockerized Electron app
# Runs the Electron desktop app inside an isolated container with X11 forwarding.
#
# Build:  docker build -t portfolioos .
# Run:    docker compose up   (recommended, handles X11/volumes)
#
# Proxy / corporate CA:
#   If building behind a TLS-intercepting proxy, place CA certificates in
#   extra-ca-certs/ before building. They will be installed into every stage.
#   Example:
#     mkdir -p extra-ca-certs
#     cp /usr/local/share/ca-certificates/*.crt extra-ca-certs/
#     docker build --network=host \
#       --build-arg HTTP_PROXY="$HTTP_PROXY" \
#       --build-arg HTTPS_PROXY="$HTTPS_PROXY" \
#       -t portfolioos .
#
# Claude Code web:
#   Web sandbox containers route all traffic through an egress proxy and lack
#   iptables/nftables support. The Docker daemon must be started manually with
#   the vfs storage driver, and builds require host networking + proxy args.
#   See CLAUDE.md "Docker Build (Claude Code Web)" for step-by-step instructions.

# ---------------------------------------------------------------------------
# Stage 1: Install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS python-deps

# Optional extra CA certificates (for corporate proxy / MITM TLS).
# python:3.13-slim ships with ca-certificates, so update-ca-certificates works.
COPY extra-ca-cert[s]/ /usr/local/share/ca-certificates/extra/
RUN update-ca-certificates 2>/dev/null || true
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app/python
COPY python/pyproject.toml python/uv.lock python/.python-version python/README.md ./
RUN uv sync --frozen --no-dev --native-tls

WORKDIR /app/agents
COPY agents/pyproject.toml agents/uv.lock ./
RUN uv sync --frozen --no-dev --native-tls

# ---------------------------------------------------------------------------
# Stage 2: Install Node dependencies
# ---------------------------------------------------------------------------
FROM node:22-slim AS node-deps

# Optional extra CA certificates (for corporate proxy / MITM TLS).
# node:22-slim doesn't ship ca-certificates, so we manually create a PEM
# bundle from any extra certs and point Node to it.
COPY extra-ca-cert[s]/ /tmp/extra-certs/
RUN mkdir -p /usr/local/share/ca-certificates && \
    touch /usr/local/share/ca-certificates/custom-ca-bundle.pem && \
    for cert in /tmp/extra-certs/*.crt; do \
      [ -f "$cert" ] && { cat "$cert"; echo ""; } >> /usr/local/share/ca-certificates/custom-ca-bundle.pem || true; \
    done
ENV NODE_EXTRA_CA_CERTS=/usr/local/share/ca-certificates/custom-ca-bundle.pem

RUN corepack enable && corepack prepare pnpm@10.29.3 --activate

WORKDIR /app
COPY .npmrc package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# ---------------------------------------------------------------------------
# Stage 3: Final runtime image
# ---------------------------------------------------------------------------
FROM node:22-slim

LABEL maintainer="PortfolioOS"
LABEL description="PortfolioOS — local-first finance app (Docker-isolated)"

# Optional extra CA certificates (for corporate proxy / MITM TLS).
# node:22-slim (bookworm) defaults to HTTPS apt sources but does NOT ship with
# ca-certificates installed.  Behind a TLS-intercepting proxy this creates a
# chicken-and-egg problem: apt cannot verify HTTPS without ca-certificates, but
# cannot install ca-certificates without a working apt.
#
# Fix: switch apt sources to HTTP for the initial package install.  Package
# integrity is still protected by GPG signatures, so HTTP is safe here.
# After ca-certificates is installed we copy the proxy CAs and run
# update-ca-certificates so all subsequent HTTPS traffic works.
COPY extra-ca-cert[s]/ /usr/local/share/ca-certificates/extra/
RUN mkdir -p /etc/ssl/certs && \
    for cert in /usr/local/share/ca-certificates/extra/*.crt; do \
      [ -f "$cert" ] && cat "$cert" >> /etc/ssl/certs/ca-certificates.crt; \
    done; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i 's|https://deb.debian.org|http://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources; \
      sed -i 's|https://security.debian.org|http://security.debian.org|g' /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
      sed -i 's|https://deb.debian.org|http://deb.debian.org|g' /etc/apt/sources.list; \
      sed -i 's|https://security.debian.org|http://security.debian.org|g' /etc/apt/sources.list; \
    fi; \
    true

# System dependencies for Electron, Python, and native modules
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    # Electron / Chromium runtime deps
    libgtk-3-0 \
    libnotify4 \
    libnss3 \
    libxss1 \
    libxtst6 \
    libatspi2.0-0 \
    libdrm2 \
    libgbm1 \
    libasound2 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxshmfence1 \
    libdbus-1-3 \
    libpango-1.0-0 \
    libcairo2 \
    xdg-utils \
    # Python 3 runtime (required by node-gyp for native module rebuilds)
    python3 \
    python3-venv \
    # Build tools for node-gyp native module compilation (e.g. duckdb for Electron)
    make \
    g++ \
    # Misc
    procps \
    && (update-ca-certificates 2>/dev/null || true) \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Enable pnpm
ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt
RUN corepack enable && corepack prepare pnpm@10.29.3 --activate

# Create non-root user for security
RUN groupadd -r portfolioos && useradd -r -g portfolioos -m -s /bin/bash portfolioos

WORKDIR /app

# Copy dependency artifacts from build stages
COPY --from=node-deps /app/node_modules ./node_modules
COPY --from=python-deps /app/python/.venv ./python/.venv
COPY --from=python-deps /app/agents/.venv ./agents/.venv

# Copy application source
COPY .npmrc package.json pnpm-lock.yaml ./
COPY tsconfig.json vite.main.config.ts vite.preload.config.ts vite.renderer.config.ts ./
COPY forge.config.ts vitest.config.ts ./
COPY electron/ ./electron/
COPY src/ ./src/
COPY python/ ./python/
COPY agents/ ./agents/
COPY scripts/ ./scripts/

# Pre-rebuild native modules (duckdb, better-sqlite3) for Electron's Node ABI.
# The node-deps stage builds them for Node.js 22, but Electron uses a different
# ABI. Without this step, electron-forge attempts a runtime rebuild at startup
# which fails in Docker due to environment/PATH issues with python3.
RUN npx electron-rebuild 2>&1

# Copy entrypoint (strip Windows \r line endings to prevent "bash\r: not found")
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

# Create data directory for persistent storage
RUN mkdir -p /home/portfolioos/.portfolioos && \
    chown -R portfolioos:portfolioos /home/portfolioos/.portfolioos && \
    chown -R portfolioos:portfolioos /app

USER portfolioos

# Electron flags for running inside Docker
ENV ELECTRON_DISABLE_GPU=1
ENV ELECTRON_NO_ATTACH_CONSOLE=1

# Expose Vite dev server port (used in dev mode)
EXPOSE 5173

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["start"]
