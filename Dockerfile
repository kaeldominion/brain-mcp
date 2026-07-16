FROM python:3.12.11-slim-bookworm

# ripgrep backs search_notes; curl is not installed — healthcheck uses python
RUN apt-get update \
    && apt-get install -y --no-install-recommends ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 brain

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# vault template ships in the image so deploy repos can seed from it
COPY vault-template /opt/vault-template

USER brain

ENV BRAIN_CONFIG=/config/brain.config.yaml \
    BRAIN_HOST=0.0.0.0 \
    BRAIN_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status==200 else 1)"]

CMD ["python", "-m", "brain_mcp.server"]
