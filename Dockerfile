# PortfolioOS — Dockerized Electron app
# Runs the Electron desktop app inside an isolated container with X11 forwarding.
#
# Build:  docker build -t portfolioos .
# Run:    docker compose up   (recommended, handles X11/volumes)

# ---------------------------------------------------------------------------
# Stage 1: Install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS python-deps

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app/python
COPY python/pyproject.toml python/uv.lock python/.python-version python/README.md ./
RUN uv sync --frozen --no-dev

WORKDIR /app/agents
COPY agents/pyproject.toml agents/uv.lock ./
RUN uv sync --frozen --no-dev

# ---------------------------------------------------------------------------
# Stage 2: Install Node dependencies
# ---------------------------------------------------------------------------
FROM node:22-slim AS node-deps

RUN corepack enable && corepack prepare pnpm@10 --activate

WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# ---------------------------------------------------------------------------
# Stage 3: Final runtime image
# ---------------------------------------------------------------------------
FROM node:22-slim

LABEL maintainer="PortfolioOS"
LABEL description="PortfolioOS — local-first finance app (Docker-isolated)"

# System dependencies for Electron, Python, and native modules
RUN apt-get update && apt-get install -y --no-install-recommends \
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
    # Python 3.13 runtime
    python3 \
    python3-venv \
    # Misc
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Enable pnpm
RUN corepack enable && corepack prepare pnpm@10 --activate

# Create non-root user for security
RUN groupadd -r portfolioos && useradd -r -g portfolioos -m -s /bin/bash portfolioos

WORKDIR /app

# Copy dependency artifacts from build stages
COPY --from=node-deps /app/node_modules ./node_modules
COPY --from=python-deps /app/python/.venv ./python/.venv
COPY --from=python-deps /app/agents/.venv ./agents/.venv

# Copy application source
COPY package.json pnpm-lock.yaml ./
COPY tsconfig.json vite.main.config.ts vite.preload.config.ts vite.renderer.config.ts ./
COPY forge.config.ts vitest.config.ts ./
COPY electron/ ./electron/
COPY src/ ./src/
COPY python/ ./python/
COPY agents/ ./agents/
COPY scripts/ ./scripts/

# Copy entrypoint
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

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
