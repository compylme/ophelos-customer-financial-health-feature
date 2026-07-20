# Service integration tests
_Exported on 7/20/2026 at 00:19:04 GMT+1 from Cursor (3.12.10)_

---

**User**

Implement service integration tests that validate the workflows between the service layer and the database:

The tests should only cover the most important paths
- valid submission perists the snapshot, child items and assessment data
- returned result from the service should match what was stored in the db
- failure during db commit rolls back the entire transaction(no partial states are stored in db)
- snapshot retrieval returns the complete aggregate
- data requested via the service layer fetches the data for the correct user and is ordered correctly

Notes:
- as we are tring to simulate the flow between the service and db, there should be no mocking of either. We already have a test db @conftest.py (31-33)  that could be used for the tests
- Fixtures and configurable factories already exist in @tests/conftest.py , they should be utilised where necessary
- Ask questions about decisions you are unsure of

---

**Cursor**

Let me explore the codebase to understand the architecture before planning.

Let me also check the exceptions file to complete the picture.

I now have a complete understanding of the codebase. I have one question before presenting the plan.

**Rollback test approach**

> **For the rollback test, we need to cause a real DB error during commit (no mocking). The cleanest approach is submitting a snapshot with a user_id that doesn't exist in the users table, triggering a FK constraint violation during commit. The service's try/except catches it, rolls back, and re-raises. We then verify no partial data was persisted.

An alternative would be to inject a fault via a SQLAlchemy session event listener, but that's closer to mocking the DB.

Which approach do you prefer?**
> - FK violation with non-existent user_id (Recommended) ✔
> - SQLAlchemy session event listener to inject a fault

---

**User**

I think for TestGetHistory, we should use a fixture with December/Jan boundaries to check that when returning in descending order, it takes the boundary into account

---

**Cursor**

Good call — using a year boundary makes the ordering assertion more meaningful since it catches naive sorting that might not handle the Dec/Jan crossover. Let me update the plan.

Updated the plan. Test 5 now uses Nov 2025, Dec 2025, and Jan 2026 periods for user A, which directly validates that descending ordering handles the year boundary correctly (Jan 2026 > Dec 2025 > Nov 2025) rather than being tripped up by month numbers alone.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll implement the service integration tests per the plan, starting with the test file.

Creating the integration test file with all five cases from the plan.

Postgres isn't running — I'll start it and re-run the tests.

All 5 service integration tests are in place and passing.

Created [`tests/integration/test_service_integration.py`](tests/integration/test_service_integration.py) with:

- **Local `service` fixture** — real `FinancialHealthService(db_session)`, no mocks
- **`TestSubmitSnapshot`**
  - persists snapshot + financial items + assessment, verified via direct DB queries
  - returned result matches data reloaded through `get_snapshot`
  - FK violation on missing user rolls back with no partial rows
- **`TestGetSnapshot`** — returns the full aggregate (assessment + items)
- **`TestGetHistory`** — user scoping plus descending order across the Nov/Dec/Jan year boundary

```
5 passed in 0.46s
```

---

**User**

now that we have a integration and unit tests, let us start implementing the foundations of a ci/cd pipeline, 

Create a github actions workflow that runs on every pull request and push to main. It should run the automated test suite as part of the ci process

- install dependencies
- set up the py version used in the project
- provision a psql service for the test suite
- run any db migrations
- run all tests
- fail the workflow if any tests fail
- keep the workflow simple and well documented
- linting,formatting,type checking etc should not be part of the quality gate

Notes:
- ask questions about decisions/assumptions you are unsure of

---

**Cursor**

I'll check the project's Python version, dependencies, and migration setup so the CI plan matches how tests actually run.

Two decisions need clarifying before I draft the CI plan — they affect how we wire the workflow to the DB.

Two decisions before I draft the plan:

**1. Database URL config**  
Tests hardcode `postgresql+psycopg://admin@localhost:5432/financial_assessment_test`, and Alembic points at the dev DB (`financial_assessment`). For CI we need a Postgres service and migrations against the test DB. Prefer which?

- **A)** Make URLs env-configurable (`TEST_DATABASE_URL` in conftest + `DATABASE_URL` override in alembic `env.py`), set them in the workflow; local defaults stay the same  
- **B)** Keep hardcoded URLs; configure the Actions Postgres service as user `admin` with trust auth / matching DB names, and override `alembic.ini` in the workflow only (e.g. sed) to target the test DB  

**2. Python version**  
Local venv is 3.13.7 and there’s no `.python-version`. Pin CI to **3.13**, **3.12**, or something else?

---

**User**

A) Make URLs env-configurable (TEST_DATABASE_URL in conftest + DATABASE_URL override in alembic env.py), set them in the workflow; local defaults stay the same
2) Pin to 3.13 and add a python version to requirements

---

**Cursor**

Incorporating your choices into a concrete CI plan.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll implement the CI foundation per the plan, starting with the Python pin in requirements.

CI foundation is in place. All 69 tests still pass locally.

**Changes:**
- [`requirements.txt`](requirements.txt) — `# Requires Python 3.13`
- [`tests/conftest.py`](tests/conftest.py) — `TEST_DATABASE_URL` env override with local default fallback
- [`migrations/env.py`](migrations/env.py) — `DATABASE_URL` overrides Alembic’s URL when set
- [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — on PR / push to `main`: Python 3.13, Postgres 16, `alembic upgrade head`, `pytest`

---

**User**

I've made a change to a column name in monthlyAssessment where 'assessment'  is now 'status', update any affected code and tests

---

**Cursor**

I'll find every reference to the old `assessment` column and update the code and tests to use `status`.

The model column is already `status`. Updating the service, schemas, factories, and tests that still reference the old field name.

Updated all references to the renamed `MonthlyAssessment` column (`assessment` → `status`).

**App code**
- [`app/services/financial_health_service.py`](app/services/financial_health_service.py) — persist `status=`
- [`app/schemas/financial_health.py`](app/schemas/financial_health.py) — `AssessmentResponse.status`

**Tests / fixtures**
- [`tests/conftest.py`](tests/conftest.py) — `assessment_factory` param/field
- Unit + integration assertions that checked `.assessment.assessment`

Left unchanged: the `MonthlySnapshot.assessment` relationship (still points at the related `MonthlyAssessment` row).

All 69 tests passed.

---

**User**

We want to implement a simple dependencies layer that connects fastAPI to the session,repo and service

- it should be able to create a session
- This should enable routers to recieve a ready made service without having to construct sessions/repos
- Ask questions regarding decisions/assumptions

---

**Cursor**

Let me check the existing dependency setup and how FastAPI/sessions are configured before asking questions.

I have a clear picture. Two questions before I draft the plan:

**Dependency layer decisions**

> **The database URL is currently only in alembic.ini and tests/conftest.py. For the FastAPI dependency layer, where should the production/dev DB URL come from?**
> - Environment variable DATABASE_URL, with the alembic.ini default as fallback (Recommended) ✔
> - A Pydantic Settings class (pydantic-settings is already in requirements.txt)

> **Where should the dependency layer code live? The existing app/db/__init__.py is currently empty.**
> - Put engine creation in app/db/__init__.py and dependencies in a new app/dependencies.py (Recommended)
> - Put everything (engine, session factory, FastAPI dependencies) in app/dependencies.py
> - Split into app/db/session.py (engine + session factory) and app/db/dependencies.py (FastAPI Depends functions)
>
> Answer: create a db session config file in /db

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll implement the dependency layer per the plan, starting with the session config.

Dependency layer is in place. All 69 tests still pass.

**Added:**
- [`app/db/session.py`](app/db/session.py) — engine + `SessionFactory` from `DATABASE_URL` (local fallback)
- [`app/dependencies.py`](app/dependencies.py) — `get_db_session`, `get_repository`, `get_financial_health_service`

Routers can inject a ready-made service with:

```python
service: FinancialHealthService = Depends(get_financial_health_service)
```

---

**User**

why did you add @financial_health_service.py (61-64)  the service already constructs the repository @financial_health_service.py (61-64) 

---

**Cursor**

I didn’t change [`financial_health_service.py`](app/services/financial_health_service.py). Those lines were already there:

```61:64:app/services/financial_health_service.py
class FinancialHealthService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = SnapshotRepository(session)
```

The dependency layer only does this:

```25:28:app/dependencies.py
def get_financial_health_service(
    session: Session = Depends(get_db_session),
) -> FinancialHealthService:
    return FinancialHealthService(session)
```

It passes the session; the service still builds its own repository inside `__init__`. That matches the plan (“no service changes”).

What *was* added is `get_repository` in [`app/dependencies.py`](app/dependencies.py) — an optional FastAPI dependency for routers that might want the repo directly. `get_financial_health_service` does **not** use it.

If you don’t want that optional helper, it can be removed without affecting the service wiring. I’m in Ask mode, so switch to Agent mode if you want that cleanup done.

---

**User**

that was my question. this @dependencies.py (19-22)  seems redundant

---

**Cursor**

Yes — for how this app is wired today, `get_repository` is redundant.

Routers are meant to take `FinancialHealthService` via `get_financial_health_service`, and that service already builds `SnapshotRepository` in `__init__`. Nothing currently needs a standalone repo dependency.

It was only included as a convenience for possible future direct repo access. Safe to delete if you want the dependency layer to stay minimal (session + service only). Switch to Agent mode if you want that removed.

---

**User**

can you review the first route created in @app/api/routes.py ?

---

**Cursor**

There’s one hard bug; the rest is polish and API hygiene.

### Bug: wrong service call signature

The route calls:

```27:30:app/api/routes.py
    snapshot = service.submit_snapshot(
        user_id=request.user_id,
        items=request.items,
    )
```

But the service expects a single `SubmitSnapshotRequest`:

```66:66:app/services/financial_health_service.py
    def submit_snapshot(self, request: SubmitSnapshotRequest) -> MonthlySnapshot:
```

That will raise `TypeError` at runtime. Pass the request through as-is:

```python
snapshot = service.submit_snapshot(request)
```

### Missing domain exception mapping

`submit_snapshot` raises `SnapshotAlreadyExists` when a period already exists. There’s no handler here (or app-level exception handler), so clients get a **500** instead of something like **409 Conflict**. Given your idempotency decision in `DECISIONS.md`, mapping that to 409 is worth doing either on this route or via a shared exception handler.

### What’s good

- Dependency injection via `Depends(get_financial_health_service)` is correct.
- `201` + `response_model=SnapshotResponse` is appropriate for create.
- `SnapshotResponse.model_validate(snapshot)` works with `from_attributes=True` on the response schemas.
- Thin router: validate in → call service → map out.

### Minor cleanup

- Unused imports: `date`, `HTTPException`, `Query`.
- Decorator formatting is a bit awkward (`@router.post("",` then kwargs on following lines); style-only.

### Not blockers, but worth knowing

- `user_id` still comes from the body, which matches your current “no auth” decision; you already noted that will change later.
- There’s no FastAPI app wiring visible under `app/api/` yet (only `routes.py` + `dependencies.py`), so this router still needs to be included on an `app` instance before it’s reachable.

**Bottom line:** fix the `submit_snapshot(request)` call first; then map `SnapshotAlreadyExists` → 409 and drop unused imports.

---

**User**

Write a small mapping for the exceptions in @app/exceptions.py to HTTP status codes and add a function that converts the exceptions 

- create a new app/api/errors file
- open to questions/suggestions

---

**Cursor**

One question before I draft the plan:

**Error handler registration**

> **How should routes use the error mapping? Two common approaches:**
> - Register a FastAPI exception_handler for DomainError on the app, so all routes get automatic mapping with no extra code (Recommended) ✔
> - Provide a helper function that routes call explicitly in a try/except block

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll implement the domain error HTTP mapping per the plan.

Updating the 422 constant to the non-deprecated Starlette name.

Domain error HTTP mapping is in place. All 69 tests still pass.

**Added** [`app/api/errors.py`](app/api/errors.py):
- `DOMAIN_STATUS_CODES` — `SnapshotAlreadyExists` → 409, `SnapshotNotFound` → 404, validation errors → 422 (fallback 400)
- `domain_error_handler` — returns `{"detail": ...}` JSON
- `register_error_handlers(app)` — registers the handler on a FastAPI app

When you create the app entry point, call `register_error_handlers(app)` so routes get automatic mapping.

---

**User**

I've mapped the exceptions to http statuses.
Follow suite and implement the following routes using the appropriate service methods

- get snapshot for a period
- get all history with the limit query optional but defaulted to the max 12

- What are your thoughts?

---

**Cursor**

Let me check the current state of the routes and service methods to make sure I'm aligned with what's already there.

The picture is clear. A couple of thoughts before the plan:

**On the GET snapshot route** — `get_snapshot` needs `user_id` and `period`. Since your URL prefix is `/snapshots`, the natural REST shape is `GET /snapshots/{user_id}/{period}` with `period` as a `date` path param (e.g. `2026-07-01`). FastAPI parses ISO dates from path segments natively. The alternative would be `GET /snapshots/{user_id}?period=2026-07-01` with period as a query param. Given a snapshot is uniquely identified by user+period, both work — but the path version reads more like a resource address.

**On the GET history route** — `GET /snapshots/{user_id}/history?limit=12` keeps it under the same prefix and clearly separates it from the single-snapshot retrieval. The service already validates limit (1-12) and raises `InvalidHistoryLimit`, which your error handler maps to 422.

**On the response type for history** — the service returns `list[MonthlySnapshot]`. The route can reuse `SnapshotResponse` as `list[SnapshotResponse]`.

**On the unused imports in routes.py** — `HTTPException`, `Query` (currently unused), and `date` can be cleaned up. `Query` will become useful again for the limit param, and `date` for the period path param.

**Route design**

> **For get-snapshot, should `period` be a path parameter or a query parameter?**
> - Path: GET /snapshots/{user_id}/{period} — e.g. /snapshots/abc/2026-07-01 (Recommended) ✔
> - Query: GET /snapshots/{user_id}?period=2026-07-01

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll add the GET snapshot and history routes per the plan.

Both GET routes are in [`app/api/routes.py`](app/api/routes.py). All 69 tests still pass.

**Added:**
- `GET /snapshots/{user_id}/history?limit=12` — optional `limit` (1–12, default 12)
- `GET /snapshots/{user_id}/{period}` — ISO date path param (e.g. `2026-07-01`)

History is declared before the `{period}` route so `/history` isn’t treated as a date. Unused `HTTPException` import removed.

---

**User**

Implement a data seeding function on startup so that when the app starts up there is a user with historical monthly snapshots all except the current month so that we can manually test the flow of the application for demo purposes

- User must have an email and uuid
- User must have upto 11 historic snapshots
- Each snapshot must have realistic financial items, monthly assessment which includes the correct explanation mapped as a value
- Data should be seeded in    "postgresql+psycopg://admin@localhost:5432/financial_assessment"
- The db should be wiped and reseeded on every startup to preserve the db state

- Ask questions/suggestions if unsure


---

**Cursor**

Let me check the current state of the app to understand the startup flow and models before asking questions.

I have a clear picture. One question:

**Seed data approach**

> **The service has calculate_assessment() which contains all the assessment logic and explanation templates. Should the seeder reuse it to generate the assessment for each month's items (guarantees correctness), or hardcode assessment values in the seed data?**
> - Reuse FinancialHealthService.calculate_assessment() to compute assessments from the seed items (Recommended) ✔
> - Hardcode assessment values directly in the seed data

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll implement the seed module and wire it into app startup per the plan.

Tweaking a couple of months so the history has a clearer healthy → manageable → critical → recovery arc.

Demo seeding is wired up. All 69 tests still pass.

**Added**
- [`app/db/seed.py`](app/db/seed.py) — wipes + reseeds on call; demo user + 11 prior months; assessments via `calculate_assessment()`
- [`app/main.py`](app/main.py) — `lifespan` runs `seed_database()` on startup

**Demo user**
- UUID: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
- Email: `demo@ophelos.com`

**History arc** (current month excluded so you can submit it manually):  
healthy stretch → manageable → critical → recovery

Try history with:
`GET /snapshots/a1b2c3d4-e5f6-7890-abcd-ef1234567890/history`

---

**User**

We need to refactor the statuses and mapped explanation, we need some nuance where the user is negative, break even and above zero but under 10%. Currently critical covers a broad range of possible situations

We either need new enums or a check in the service layer if critical, check the actual percentage and map new explanations that reflect them. What are your thoughts (either change will also require a refactor of the 'calculate_assessment' method

We need additional unit  and service integration tests to cover the new statuses/explanation

---

**Cursor**

Good observation — lumping "spending more than you earn" and "8% disposable ratio" under the same CRITICAL label loses important context for the user. Let me check the current thresholds, templates, and test coverage before suggesting an approach.

Now let me also check the rest of the unit tests and the seed data to understand the full scope of impact.

Here's my recommendation:

**Add new enum values** rather than sub-checking within CRITICAL. Three new statuses give each scenario a distinct label and explanation:

| Scenario | Current | Proposed |
|---|---|---|
| Expenditure > income (negative disposable) | CRITICAL | **DEFICIT** |
| Income = expenditure (zero disposable) | CRITICAL | **BREAK_EVEN** |
| Positive but < 10% ratio | CRITICAL | **CRITICAL** (stays) |

This is cleaner than an if-chain inside CRITICAL because:
- Each status maps to exactly one explanation template (no conditional text within a template)
- The `AffordabilityStatus` enum becomes the single source of truth — API consumers, frontend, and DB all see the distinct value
- The threshold logic stays a clean cascade: deficit → break even → critical → manageable → healthy

The thresholds become:

```
disposable < 0         → DEFICIT
disposable == 0        → BREAK_EVEN  
ratio < 0.10           → CRITICAL
ratio < 0.25           → MANAGEABLE
ratio >= 0.25          → HEALTHY
```

**Status enum design**

> **Do you agree with adding DEFICIT and BREAK_EVEN as new enum values (splitting what was CRITICAL into 3 distinct statuses)? Or would you prefer a different breakdown?**
> - Add DEFICIT and BREAK_EVEN enums with distinct explanations (Recommended) ✔
> - Keep 3 enums but add sub-status explanations within CRITICAL via conditional logic
> - Something else — I'll describe what I want

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll implement the status split per the plan, starting with the enum and service refactor.

Status split is complete. All **74** tests passed.

**Cascade**
- `disposable < 0` → **DEFICIT**
- `disposable == 0` → **BREAK_EVEN**
- `0 < ratio < 10%` → **CRITICAL**
- `10% ≤ ratio < 25%` → **MANAGEABLE**
- `ratio ≥ 25%` → **HEALTHY**

**Updated**
- [`app/schemas/financial_health.py`](app/schemas/financial_health.py) — new enum values
- [`app/services/financial_health_service.py`](app/services/financial_health_service.py) — templates + cascade
- [`app/db/seed.py`](app/db/seed.py) — BREAK_EVEN and DEFICIT months
- Unit + service integration tests for the new statuses/explanations

---

**User**

@financial_health_service.py (34-39) this explanation is not user friendly and should not attempt to advise the user
@financial_health_service.py (41-47) 
we dont know if expenses are essentials or not and should not assume so

---

**Cursor**

Good points. Let me update both explanation templates.

Now update the tests that assert against the old wording.

The substring `"exceeds your income"` still appears in the new DEFICIT text (`"Your total expenditure currently exceeds your total income."`), and `"no surplus"` still appears in the new BREAK_EVEN text (`"no surplus for the month."`). So all assertions remain valid. Let me confirm by running the tests.

The test output is confusing — it shows `AssertionError` with the substring present in the text. Let me look at the actual explanation value more closely.

The new text says "exceeds your total income" not "exceeds your income". The tests assert `"exceeds your income"` which doesn't match because of the extra "total". Let me update the test assertions.

All 74 tests pass. Here's a summary of the changes:

**DEFICIT** — removed the advisory language ("not sustainable and may require immediate changes to restore balance") and replaced it with a factual statement:

> "Your total expenditure currently exceeds your total income."

**BREAK_EVEN** — removed the assumption about "essentials" and replaced it with a neutral observation:

> "Your income and expenditure are currently equal, leaving no surplus for the month."

Both templates now stick to reporting what the data shows without advising the user or making assumptions about the nature of their expenses.

---

**User**

I've made some changes to the service where we now calculate a shortfall_percentage @financial_health_service.py (132-181)  and be explicit in the wording for a deficit
@financial_health_service.py (33-39) 
we need to update the tests accordingly


---

**Cursor**

Let me check the current state of the service and the tests.

Let me first run the tests to see exactly what's failing with your changes.

There are 6 failures in two categories:

1. **Assertion mismatches** (4 tests) — old wording like `"exceeds your total income"` and `"healthy balance"` no longer matches the updated templates
2. **`DivisionByZero`** (2 tests) — the new `shortfall_percentage` calculation on line 163 divides by `total_income` without guarding against zero, exactly like `disposable_income_ratio` does above it

I'll fix the zero-income guard in the service first, then update all the test assertions.

Now update the test assertions. I also need to check whether the CRITICAL, MANAGEABLE, and HEALTHY template assertions in `test_explanation_maps_to_status` still match, since those templates were also changed.

All 74 tests pass. Here's what was done:

**Service fix** — `shortfall_percentage` on line 163 was dividing by `total_income` without a zero guard, causing `DivisionByZero` in the zero-income edge cases. Added the same `if total_income > 0` guard that `disposable_income_ratio` already uses.

**Test assertion updates** (4 files, 6 assertions):

| Test | Old assertion | New assertion |
|---|---|---|
| `test_deficit_status` | `"exceeds your total income"` | `"exceeding your income by"` |
| `test_explanation_maps_to_status` (deficit) | `"exceeds your total income"` | `"exceeding your income by"` |
| `test_explanation_maps_to_status` (critical) | `"immediate attention"` | `"small portion"` |
| `test_explanation_maps_to_status` (manageable) | `"some room for flexibility"` | `"moderate portion"` |
| `test_explanation_maps_to_status` (healthy) | `"healthy balance"` | `"substantial portion"` |
| `test_builds_assessment_from_calculation` | `"healthy balance"` | `"substantial portion"` |
| `test_deficit_assessment_persists_correctly` (integration) | `"exceeds your total income"` | `"exceeding your income by"` |

---

**User**

Write a brief README.md for this project.

Include:
- A brief explanation of what the financial health application does.
- The main technologies used: FastAPI, SQLAlchemy, PostgreSQL, Alembic and pytest.
Prerequisites, including Python 3.13 and PostgreSQL.
- Local setup instructions
- Explain how demo users and historical snapshot data are seeded for manual testing.
- List the available API endpoints and briefly explain each one.
- Include the Swagger UI endpoint, /docs, so reviewers can test the API interactively.
- Explain how to run the full test suite with pytest.
- Mention that GitHub Actions runs the tests on pushes and pull requests.
- Reference DECISIONS.md for architectural decisions and trade-offs.

---

**Cursor**

Let me gather the necessary details from the codebase to write an accurate README.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

Created [README.md](README.md) with:

- Project overview and affordability statuses
- Tech stack (FastAPI, SQLAlchemy, PostgreSQL, Alembic, pytest)
- Prerequisites (Python 3.13, PostgreSQL, both databases)
- Local setup (venv, deps, migrations, `uvicorn`)
- Demo seeding details (user UUID/email, 11 historic months, current month left open)
- API endpoints table plus Swagger UI at `/docs`
- How to run `pytest`
- GitHub Actions CI summary
- Link to [DECISIONS.md](DECISIONS.md)

