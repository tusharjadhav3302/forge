# Forge Developer Tools

Local development stack for running Forge services on the host with Prometheus scraping both the API and worker.

## Usage

```bash
# Start Redis + Prometheus (scrapes host-local processes)
docker compose -f devtools/docker-compose.dev.yml up -d

# In separate terminals, start the local services:
uv run uvicorn forge.main:app --reload --port 8000
uv run forge worker
```

## Endpoints

| Service | URL |
|---------|-----|
| Forge API | http://localhost:8000 |
| API metrics | http://localhost:8000/metrics |
| Worker metrics | http://localhost:8001/metrics |
| Redis | redis://localhost:6380/0 |
| Prometheus | http://localhost:9092 |

## How it works

`prometheus.dev.yml` targets `host.docker.internal` which resolves to the host machine from inside the Prometheus container. The `extra_hosts: host.docker.internal:host-gateway` entry in `docker-compose.dev.yml` enables this on Linux/Fedora.

To reload Prometheus config without restarting:
```bash
curl -X POST http://localhost:9092/-/reload
```

## patch_checkpoint.py

Directly edit a workflow's Redis checkpoint — useful when a workflow gets stuck:

```bash
uv run python devtools/patch_checkpoint.py <ticket-key> <field=value> [field=value ...]

# Examples:
uv run python devtools/patch_checkpoint.py AISOS-376 \
  current_node=ci_evaluator is_paused=false ci_fix_attempts=0

uv run python devtools/patch_checkpoint.py AISOS-376 \
  'ci_skipped_checks=["e2e-openstack"]'
```

Values are parsed as JSON where possible (`true`/`false`/`null`/numbers/lists), otherwise as strings.
