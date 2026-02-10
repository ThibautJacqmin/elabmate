# elabmate

Python helpers to work with eLabFTW from Python and (optionally) sync Labmate
acquisitions.

## Features
- `ElabClient`: high-level wrapper around the eLabFTW API client.
- `ElabExperiment`: convenience helpers for tags, steps, comments, and uploads.
- `ElabBridge`: optional Labmate backend to sync acquisitions with eLabFTW.

## Installation

Editable install for local development:

```bash
python -m pip install -e .
```

## Configuration

Create a configuration file (default: `elab_server.conf`) with one `KEY=VALUE`
per line:

```ini
API_HOST_URL=https://your_elab_server_address/api/v2
API_KEY=your_api_key
VERIFY_SSL=false
UNIQUE_EXPERIMENTS_TITLES=true
TEAM_ID=1
```

Notes:
- `TEAM_ID` is optional; when absent, the client tries to resolve it from the API.
- `VERIFY_SSL` accepts `true` or `false`, depending on how you configured the server

## Quickstart

```python
from elabmate import ElabClient

client = ElabClient("elab_server.conf")
exp = client.create_experiment(title="My experiment")

exp.main_text = "Experiment notes..."
exp.add_tag("demo")
exp.upload_file("path/to/file.dat")
```

## Labmate integration

`ElabBridge` implements a Labmate acquisition backend interface. You can
register it where Labmate expects a backend:

```python
from elabmate import ElabBridge

backend = ElabBridge(client)
# Attach `backend` to your Labmate acquisition manager.
```

## Tests

Run integration tests (requires a valid eLabFTW server/config):

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Optional environment variables for tests:
- `ELAB_TEST_CATEGORY`
- `ELAB_TEST_STATUS`

## References
- eLabFTW documentation: https://doc.elabftw.net/
- eLabFTW API docs: https://doc.elabftw.net/api/
- Labmate docs: https://kyrylo-gr.github.io/labmate/
- Labmate GitHub: https://github.com/kyrylo-gr/labmate
