# Financial Health API

A REST API that lets users submit monthly financial snapshots (income and expenses), calculates an affordability assessment, and returns the results for review. Each snapshot is classified as one of `DEFICIT`, `BREAK_EVEN`, `CRITICAL`, `MANAGEABLE`, or `HEALTHY`, with a factual explanation derived from the submitted figures.

## Technologies

- **FastAPI** — HTTP API and dependency injection
- **SQLAlchemy** — ORM and database access
- **PostgreSQL** — primary data store
- **Alembic** — schema migrations
- **pytest** — unit and integration tests

## Prerequisites

- Python 3.13
- PostgreSQL (local instance or container)
- Two databases created before first run:
  - `financial_assessment` (application / demo data)
  - `financial_assessment_test` (test suite)

Default connection URLs (override with env vars as needed):

| Purpose | Env var | Default |
| --- | --- | --- |
| App / migrations | `DATABASE_URL` | `postgresql+psycopg://admin@localhost:5432/financial_assessment` |
| Tests | `TEST_DATABASE_URL` | `postgresql+psycopg://admin@localhost:5432/financial_assessment_test` |

## Local setup

```bash
# Clone and enter the project
git clone <repo-url>
cd "ophelos-customer financial health feature"

# Create and activate a virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create databases (example with psql)
createdb financial_assessment
createdb financial_assessment_test

# Apply migrations
alembic upgrade head

# Start the API
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Interactive docs are at [`/docs`](http://127.0.0.1:8000/docs).

## Demo data

On startup, the app wipes and re-seeds the `financial_assessment` database so reviewers always see a known state.

Seeded content:

- A demo user: `demo@ophelos.com` with UUID `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
- Up to 11 months of historical snapshots (all months except the current month)
- Realistic income/expense items per month
- A monthly assessment for each snapshot, including the status and explanation produced by the same calculation logic used at submit time

The current month is left empty so you can manually submit a new snapshot during demos.

## API endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Health check; confirms the API is running |
| `POST` | `/snapshots` | Submit a monthly snapshot of income and expenses for a user |
| `GET` | `/snapshots/{user_id}/history` | Return recent snapshots for a user, newest first (`limit` query param, default `12`, max `12`) |
| `GET` | `/snapshots/{user_id}/{period}` | Return a single snapshot for a user and period (e.g. `2026-07-01`) |

Explore and try these endpoints interactively via Swagger UI at `/docs`.

## Running tests

Ensure the `financial_assessment_test` database exists, then from the project root:

```bash
pytest
```

The suite covers unit tests for the service layer and integration tests against the real Postgres test database. Failures exit non-zero.

## Continuous integration

GitHub Actions runs on pushes to `main` and on pull requests. The workflow:

1. Sets up Python 3.13
2. Installs dependencies from `requirements.txt`
3. Provisions a Postgres service container
4. Applies Alembic migrations
5. Runs the full pytest suite

The job fails if any test fails.

## Further reading

See [DECISIONS.md](DECISIONS.md) for architectural decisions and trade-offs.
