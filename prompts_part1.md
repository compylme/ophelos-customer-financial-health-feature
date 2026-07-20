# PostgreSQL database models
_Exported on 7/17/2026 at 20:14:53 GMT+1 from Cursor (3.12.10)_

---

**User**

I want to build the following postgresql database models using  sqlalchemy

Use:
Python 3.12
sqlalmeny using mapepd, mapped_column and relationship
postgressql
UUID primary keys
timezone aware timestamps
python decimal and postgres numeric for monetary values
python enums as postgres enums
fk constraints and relationship definitions

Table name: users

Fields:
Id UUID pk
Name required string
Email required string, and unique

A user can have many monthly snapshots

Table name: 'Monthly Snapshots':

Fields:
id: UUID pk
user_id (FK Id on user table)
period(month_year)
submitted_at(tz timestamp)

A user can have only one snapshot for a given period
unique constraint across user_id and period

Monthly snapshot belongs to one user
Monthly snapshot can have may financial items
Monthly snapshot can have only one monthly assessment

Table name: 'Financial Item'

id: UUID pk
snapshot_id: (FK id on monthly snapshot)
direction: (enum with these two vals: 'INCOME'|'EXPENSE')
description: required string
Amount: required monetary value

amount must be greater than zero

A financial item belongs to one snapshot

Table name: 'Monthly Assessment'

id: UUID pk
snapshot_id (required FK id on monthly snapshot)
total_income: required monetary value
total_expenditure: required monetary value
disposable_income: required monetary value
assessment: required string containing the outcome
explanation: required human readable text explanation

A monthly assessment belongs to one monthly snapshot

Use created at and updated fields where needed
Use db level constraints
Ask any questions on decisions you are unsure of

---

**Cursor**

I've reviewed the project structure. You have a FastAPI project with SQLAlchemy 2.0.51, psycopg, and an empty `app/db/models.py` ready to go. I have a few design questions before I put together the plan.

**Database Model Design Decisions**

> **How should the `period` (month/year) field on Monthly Snapshot be represented in PostgreSQL?**
> - DATE column storing the first day of the month, e.g. 2026-07-01 (Recommended) ✔
> - VARCHAR string like '2026-07'
> - Two integer columns: year and month

> **Should deleting a parent row cascade-delete its children? (e.g. deleting a user removes their snapshots; deleting a snapshot removes its financial items and assessment)**
> - Yes, cascade deletes through all parent-child relationships (Recommended) ✔
> - No, restrict deletes if children exist (raise an error)
> - No, set the FK to NULL on children (keep orphan rows)

> **What precision/scale should monetary values use? (Postgres NUMERIC(precision, scale))**
> - NUMERIC(12, 2) - up to 9,999,999,999.99 (Recommended) ✔
> - NUMERIC(10, 2) - up to 99,999,999.99
> - NUMERIC(19, 4) - high precision for financial calculations

All clear. Let me put together the plan.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

All clean -- ruff, mypy, and the IDE linter all report zero issues.

Both tasks are done. Here's a summary of what was written to `app/db/models.py`:

**Base infrastructure:**
- `Base` -- `DeclarativeBase` subclass for all models
- `TimestampMixin` -- provides `created_at` and `updated_at` (timezone-aware, server-defaulted) to every model
- `Direction` enum -- `INCOME` / `EXPENSE`, mapped to a native Postgres enum

**Four models with all requested constraints:**

| Model | Table | Key constraints |
|---|---|---|
| `User` | `users` | UUID PK, unique email |
| `MonthlySnapshot` | `monthly_snapshots` | UUID PK, FK to `users.id` ON DELETE CASCADE, `UniqueConstraint(user_id, period)` |
| `FinancialItem` | `financial_items` | UUID PK, FK to `monthly_snapshots.id` ON DELETE CASCADE, `CheckConstraint(amount > 0)` |
| `MonthlyAssessment` | `monthly_assessments` | UUID PK, FK to `monthly_snapshots.id` ON DELETE CASCADE, unique `snapshot_id` (enforces one-to-one) |

**Relationships:**
- `User.snapshots` <-> `MonthlySnapshot.user` (one-to-many, cascade all/delete-orphan)
- `MonthlySnapshot.financial_items` <-> `FinancialItem.snapshot` (one-to-many, cascade all/delete-orphan)
- `MonthlySnapshot.assessment` <-> `MonthlyAssessment.snapshot` (one-to-one via `uselist=False`, cascade all/delete-orphan)

---

**User**

I want to build a repository layer that abstracts data persistence away from the service layer

It should be a class with the following functions
- check if a snapshot already exists for the current period
- add function that persists all data in one atomic action
- function to get monthly snapshot by period
- function to get a history of snapshots with an optional argument of how many snapshots to be fetched, limited to a max of 12 

Notes:
- The repository layer should not own the session commit
- Assume the service layer is responsible for validation, transaction commit/rollback

Ask questions about decisions you are unsure of

---

**Cursor**

Let me read the current files to understand the codebase state before planning.

I have a good understanding of the models and the existing file. A couple of decisions will shape the implementation significantly.

**Repository Layer Design Decisions**

> **After `session.add()` in the add method, should the repository call `session.flush()` to push changes to the DB (detects constraint violations early, assigns server-generated IDs) -- or just add to the session and leave everything to the service layer?**
> - Flush after add -- detect DB errors early, IDs are available immediately (Recommended)
> - Only session.add() -- service layer decides when to flush/commit ✔

> **Should the 'get by period' and 'get history' methods eagerly load related data (financial_items, assessment) or leave them lazy-loaded?**
> - Eager load financial_items and assessment via joinedload/selectinload (Recommended) ✔
> - Lazy load -- caller triggers loading when accessing the attributes

> **How should the SQLAlchemy Session be provided to the repository?**
> - Injected via constructor: SnapshotRepository(session) (Recommended) ✔
> - Passed as an argument to each method: repo.add(session, snapshot)

---

**User**

Eager loading: get_by_period and get_history use selectinload to eagerly load financial_items and assessment relationships, avoiding N+1 queries.

We should not be eagerly loading fiancial_items

---

**Cursor**

Understood -- I'll update the plan to only eagerly load `assessment` on both `get_by_period` and `get_history`, and leave `financial_items` as lazy-loaded.

Plan updated. The three changes are:

- **Design decision**: Eager loading now applies only to `assessment`, not `financial_items`.
- **`get_by_period`**: Removed `selectinload(MonthlySnapshot.financial_items)`.
- **`get_history`**: Removed `selectinload(MonthlySnapshot.financial_items)`.

`financial_items` will remain lazy-loaded and only fetched if/when the caller accesses the attribute.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

All clean -- ruff, mypy, and the IDE linter report zero issues.

Both tasks are done. Here's what was written to `app/repositories/snapshot_repository.py`:

**`SnapshotRepository`** -- session injected via constructor, never commits or rolls back.

| Method | Signature | Behaviour |
|---|---|---|
| `exists_for_period` | `(user_id, period) -> bool` | Efficient `SELECT EXISTS(...)` check |
| `add` | `(snapshot) -> None` | `session.add()` only; cascades to children |
| `get_by_period` | `(user_id, period) -> MonthlySnapshot \| None` | Single snapshot with `assessment` eagerly loaded |
| `get_history` | `(user_id, limit=12) -> list[MonthlySnapshot]` | Up to 12 snapshots, most recent first, `assessment` eagerly loaded |

---

**User**

For the code present, we get this error:
```
Import "app.db.models" could not be resolved
```
@migrations/env.py:6-9 

---

**Cursor**

The models were moved from `app/db/models.py` to `app/models/models.py`, but the Alembic migration env still references the old path. Let me fix that and then check the repository implementation status.

The repository is already fully implemented from the previous turn. Just need to fix the stale import in `migrations/env.py`.

Fixed -- the import in `migrations/env.py` now points to `app.models.models` where `Base` actually lives. The repository was already fully implemented from the prior turn, so both plan todos are already complete.

---

**User**

Implement the service layer - FinancialHealthService.py that owns 
- business rules
- validation 
- snapshot submission workflow
- transaction commit and rollback

Methods

submit_snapshot 
- Detemines the current monthly period
- this will check if snapshot already exists for the period (refer to @app/repositories/snapshot_repository.py )
- raise an exception if the snapshot already exists
- validate submitted items
- calls calculate_assessment() before creating the assessment entity
- create snapshot including the storing of financial items and monthly assesssments
- rolls back the transaction and raises the exception if persistence fails
- returns the created snapshot

calculate_assessment

calculate the following
- total_income
- total_expenditure
- disposable_income = total_income - total_expenditure
- disposable_income_ratio = disposable_income/total_income

- define AffordabilityStatus enum with the following

CRITICAL
MANAGEABLE
HEALTHY

- Use the following rules
if disposable income is 0 or < 10% return the enum CRITICAL
if disposable income is < 25% return the enum MANAGEABLE
else return the enum HEALTHY 

- calculate assessment should also map the status to a clear user firendly explanation, the language must be clear and it shouldexplains how the result was reached
- the rseult should include: total_income
total_expenditure
disposable_income
disposable_income_ratio
status
explanation

No method should fail silenlty

Use clear domain exceptions such as
SnapshotAlreadyExists
SnapshotNotFound
InvalidFinancialItems
InvalidHistoryLimit

Do not raise HTTPExceptions from the service layer

Validate that 
at least one financial item is provided
amonts are greater than 0
each item has a valid direction

Ask any questions about decisions you might be unsure of

---

**Cursor**

Let me read the current files to understand the full context before asking questions.

I have a clear picture of the models, repository, and your decisions document. Two questions before I plan.

**Service Layer Design Decisions**

> **What input format should `submit_snapshot` accept for the financial items? This determines the method signature and how validation works.**
> - Pydantic input schemas (e.g. SubmitSnapshotRequest with a list of FinancialItemInput) -- service validates the schema then builds ORM models (Recommended) ✔
> - Raw dicts/lists -- service validates and converts to ORM models
> - Pre-built ORM model instances -- caller constructs them, service just validates

> **The `MonthlyAssessment` model currently has no `disposable_income_ratio` column. `calculate_assessment` computes this ratio to determine the status. Should it be persisted or just computed on the fly?**
> - Do not persist -- it can always be recalculated from total_income and total_expenditure (Recommended) ✔
> - Add a disposable_income_ratio column to the MonthlyAssessment model

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

Mypy needs `__init__.py` files for the new packages. Let me check what exists and add the missing ones.

No `__init__.py` files exist anywhere. Let me create them for all packages.

All clean now.

All five tasks are done. Here's a summary of what was created:

**`app/exceptions.py`** -- Four domain exceptions extending `DomainError`:
- `SnapshotAlreadyExists`, `SnapshotNotFound`, `InvalidFinancialItems`, `InvalidHistoryLimit`

**`app/schemas/financial_health.py`** -- Pydantic schemas and enum:
- `AffordabilityStatus` enum: `CRITICAL`, `MANAGEABLE`, `HEALTHY`
- `FinancialItemInput`: validates direction, non-empty description, amount > 0
- `SubmitSnapshotRequest`: validates user_id + at least one item
- `AssessmentResult`: typed result from `calculate_assessment`

**`app/services/financial_health_service.py`** -- `FinancialHealthService` with four methods:

| Method | Purpose |
|--------|---------|
| `submit_snapshot` | Determines period, checks for duplicates, validates, calculates assessment, persists atomically, rolls back on failure |
| `calculate_assessment` | Pure calculation: sums income/expenses, computes ratio, determines status, generates explanation |
| `get_snapshot` | Fetches by period or raises `SnapshotNotFound` |
| `get_history` | Validates limit (1-12), delegates to repository |

Also added `__init__.py` files to all packages (`app`, `db`, `models`, `repositories`, `schemas`, `services`) to fix mypy module resolution, and deleted the empty `FinancialHealthService.py` placeholder.

---

**User**

Implement pytest test fixtures for repository integration tests that validate the repo functions against an isolated test database

Do not write the tests yet, this should be a reference for the type of fixtures needed

- Use the existing sqlAlchemy models, db config, schemas and repo functions to determine fixtures that are required

Requirements
Test db:
- raise an isolated db for repo tests
- test db must be isolated and not modify dev dbs
- db config should mimic production db

Model fixtures:
- Valid users
- Monthly financial snapshot
- Financial items related to a snapshot
- Related monthly assessment
- Monthly snapshots belonging to the sam user across a range of monthly periods
- Snapshots for different users
- Uncommited model fixtures for persistence tests
- Persisted model fixtures for tests that require existing records

Create fixtures keeping these potential tests in mind
- Validate of happy paths inline with the repo functions
- Prevention of duplicate records
- Retrieval tests that validate max limits
- Handling of a snapshot that does not exist
- Ensuring one user cannot get another's snapshots
- Snapshots around year boundaries, i.e December followed by Jan
- Handling of zero financial value inputs

Notes:
- Do not write any tests yet
- Where needed, factory fixtures should be configurable to support tests that use a variation of the same fixtures
- Ask questions of technical decisions you are unsure of


---

**Cursor**

Let me read the existing codebase to understand the full picture before planning.

I have a complete picture of the codebase. One key design decision before I plan.

**Test Database Strategy**

> **How should the isolated test database be provisioned? The dev DB is postgresql+psycopg://admin@localhost:5432/financial_assessment.**
> - Separate test database on the same Postgres instance (e.g. financial_assessment_test) -- simple, no extra dependencies (Recommended) ✔
> - Testcontainers -- spin up a fresh Postgres Docker container per test session (fully isolated, requires testcontainers-python dependency)

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll implement the repository test fixtures as specified in the plan, starting with the directory structure.

I used SQLAlchemy 2.0's `join_transaction_mode="create_savepoint"` (the modern equivalent of the nested-transaction pattern from the plan). Running linters next.

All three tasks are done. Here's what was created:

**Structure**
```
tests/
  __init__.py
  repositories/
    __init__.py
    conftest.py
```

**[`tests/repositories/conftest.py`](tests/repositories/conftest.py)** includes:

| Category | Fixtures |
|----------|----------|
| Infrastructure | `test_engine` (session), `db_session` (per-test rollback), `repository` |
| Factories | `user_factory`, `snapshot_factory`, `financial_item_factory`, `assessment_factory` |
| Pre-built | `persisted_user`, `second_user`, `persisted_snapshot`, `year_boundary_snapshots`, `snapshot_history` (12 months), `multi_user_snapshots`, `zero_amount_items`, `uncommitted_snapshot` |

**Isolation:** Uses `financial_assessment_test` (not the dev DB). Each test runs inside a transaction that is rolled back via `join_transaction_mode="create_savepoint"`.

**Prerequisite** (run once):
```sql
CREATE DATABASE financial_assessment_test;
```

---

**User**

I've written an initial repo integration test in @tests/integration/test_snapshot_repository.py 

Add further tests for the following
- Validate of happy paths inline with the repo functions
- Prevention of duplicate records
- Retrieval tests that validate max limits
- Handling of a snapshot that does not exist
- Ensuring one user cannot get another's snapshots
- Snapshots around year boundaries, i.e December followed by Jan
- Handling of zero financial value inputs

- These tests should only validate the functionality of the repository
- You should only write tests for the snapshot repository
- Use the fixtures and configurable factories when writing the tests
- Give me ideas for edge cases i might not have considered
- Ask any questions about decisions you are unsure of

---

**Cursor**

Let me read the current state of all relevant files before planning.

I have a complete picture of the repository, models, fixtures, and the existing test. No questions needed -- the scope is clear. Let me create the plan.

---

**User**

I think this test
returns_none_for_different_user is redundant as
allows_same_period_for_different_users and returns_none_when_no_snapshot_exists already cover that scenario

thoughts?

---

**Cursor**

You're right. If `allows_same_period_for_different_users` confirms two users can share a period, and `returns_none_when_no_snapshot_exists` confirms `None` is returned when no data matches, then `returns_none_for_different_user` doesn't prove anything new -- it's just a combination of those two already-covered behaviours.

The only nuance it could add is proving that `get_by_period` filters on `user_id` correctly when data for *another* user exists at the same period. But `returns_only_requesting_users_snapshots` in the `get_history` section already validates that user-scoped filtering works, and `exists_for_period` has its own `returns_false_for_different_user` test with `multi_user_snapshots` covering the same filter logic.

I'll remove it. Let me update the plan.

Done. Removed `returns_none_for_different_user` from the `get_by_period` section -- bringing it from 7 to 6 tests, and 31 to 30 total. The cross-user filtering behaviour is already covered by:

- `allows_same_period_for_different_users` (proves both rows exist)
- `returns_none_when_no_snapshot_exists` (proves `None` when no match)
- `returns_only_requesting_users_snapshots` in `get_history` (proves user-scoped filtering)
- `returns_false_for_different_user` in `exists_for_period` (proves the filter clause works)

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll implement the full suite of repository integration tests per the plan, starting by fixing the existing test.

I'll tighten `returns_false_for_different_user` — the current version is unclear because both users share the same period in `multi_user_snapshots`.

All 30 tests passed. Here's what was added to [`tests/integration/test_snapshot_repository.py`](tests/integration/test_snapshot_repository.py):

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestExistsForPeriod` | 5 | Happy path, missing data, cross-user, wrong period, year boundary |
| `TestAdd` | 6 | Persist + cascade, unique constraint, multi-user same period, min amounts, zero-amount rejection |
| `TestGetByPeriod` | 6 | Happy path, missing, eager assessment, Dec/Jan retrieval, decimal precision |
| `TestGetHistory` | 8 | Ordering, full 12, explicit limit, clamp to 12, empty, cross-user isolation, year boundary order, eager load |
| `TestEdgeCases` | 5 | Income-only, expense-only, limit=1, mid-month exact match, large Numeric(12,2) values |

Also fixed the original test to use `persisted_snapshot` instead of `persisted_user` alone (which had no snapshot and would have asserted `True` incorrectly).

---

**User**

test_rejects_zero_amount_via_check_constraint this is not a repository test, this is validating db constraints.

In fact I think most of these tests are validating db constraints and not pure repository functions. I think whilst these tests are valid, they should be separated from repository tests. 

What are your thoughts?

---

**Cursor**

You're right to draw that line.

**Repository tests** should ask: given this session and these inputs, does `SnapshotRepository` behave as specified? That means return values, filtering (`user_id` / `period`), ordering, limit clamping, eager-loading of `assessment`, and that `add` puts the graph on the session so it can be flushed/queried.

**Constraint / schema tests** ask: does Postgres enforce the model’s rules? Zero amounts (`CHECK`), duplicate `(user_id, period)`, unique `snapshot_id` on assessments, cascade deletes, enum values, etc. Those fail with `IntegrityError` whether or not you call the repository — `session.flush()` after building ORM objects is enough. Putting them under “repository” muddies the signal when a test fails.

So I’d separate them:

| File | Owns |
|------|------|
| `tests/integration/test_snapshot_repository.py` | Pure repo behaviour |
| `tests/integration/test_model_constraints.py` (or similar) | DB/schema constraints |

**Keep in repository tests:** happy-path `exists` / `get_by_period` / `get_history`, cross-user filtering, year-boundary ordering, limit clamp, empty results, `add` + flush so children are queryable via the repo, assessment eager load, decimal round-trip *through* `get_by_period` (that’s persistence shape the repo exposes, not a CHECK).

**Move out:** `rejects_duplicate_user_period`, `rejects_zero_amount_via_check_constraint`, and arguably “allows same period for different users” if framed as proving the unique constraint is composite — that’s schema semantics, even if you exercise it via `snapshot_factory`.

`persists_with_minimal_amounts` (`0.01`) is borderline: it’s a repo happy path with edge data, not a constraint assertion. Fine either as a thin repo test or next to constraint tests as “smallest allowed value still persists.”

One caveat: some teams keep one “add duplicate → IntegrityError” case in repo tests to document that the repo does not catch duplicates (service does). That’s documentation, not constraint coverage — one test max, clearly named.

Want me to plan a split of the current file along those lines?

---

**User**

yes

---

**Cursor**

I'll draft a concrete split plan from the current test file.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

Split complete — **31 tests passed**.

| File | Tests | Focus |
|------|-------|-------|
| [`tests/integration/test_snapshot_repository.py`](tests/integration/test_snapshot_repository.py) | 27 | Pure repo behaviour |
| [`tests/integration/test_model_constraints.py`](tests/integration/test_model_constraints.py) | 4 | Schema constraints (no `repository`) |

**Moved:** duplicate `(user_id, period)`, composite unique (same period / different users), zero amount CHECK.

**Added:** negative amount CHECK (`Decimal("-0.01")`).

**Removed** unused `pytest` / `IntegrityError` imports from the repository test file.

---

**User**

We want to implement unit tests for the service layer, these tests should focus on validating the business logic around

- Snapshot submission
- Calculation of assessment
- Getting snapshots
-  Getting history
- Business decisions around how we calculate the different statuses and the explanations that are mapped to them
- Handling of zero income/negative disposable income
- Handling of the status percentage boundaries (10% - critical, 25% - manageable)
- Rejection of duplicate periods
- Commits on success
- rollback and re raising of failues
- I'm open to edge cases I might not have thught about

Notes:
- As these are strictly validating business logic we should mock the repo/session
- Tests should strictly validate business logic
- @tests/conftest.py factories/fixtures are designed to be used across all tests, feel free to add new fixtures/use factories where needed
- Ask any questions on decisions you are unsure of

---

**Cursor**

Let me read the current codebase to plan the tests properly.

I have everything I need. No questions -- the scope is clear and the mocking approach is straightforward.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll implement the service unit tests per the plan, starting with the shared factories in `conftest.py`.

All 35 unit tests passed. Here's what was added:

**Shared fixtures** in [`tests/conftest.py`](tests/conftest.py):
- `financial_item_input_factory` — builds Pydantic `FinancialItemInput`
- `submit_snapshot_request_factory` — builds `SubmitSnapshotRequest`

**Unit suite** in [`tests/unit/test_financial_health_service.py`](tests/unit/test_financial_health_service.py) (mocked session + repository):

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestCalculateAssessment` | 15 | Statuses, 10%/25% boundaries, totals, explanations |
| `TestSubmitSnapshot` | 8 | Happy path, period normalization, duplicates, add/commit order, rollback |
| `TestGetSnapshot` | 3 | Found / not found / delegation |
| `TestGetHistory` | 5 | Delegation + limit validation (0, -1, 13, 1, 12) |
| `TestEdgeCases` | 4 | Expense-only, single item, many items, UTC `submitted_at` |

---

**User**

these 2 factories appear to be almost identical
@conftest.py (84-96) 
@conftest.py (99-112) 
could we remove the newly created one and use the existing one in for @conftest.py (115-141) ?

---

**Cursor**

The two factories look identical but they build **different types**:

- `financial_item_factory` (lines 84-96) → `FinancialItem`, the SQLAlchemy **ORM model** (`app.models.models`)
- `financial_item_input_factory` (lines 99-112) → `FinancialItemInput`, the Pydantic **schema** (`app.schemas.financial_health`)

`submit_snapshot_request_factory` builds a `SubmitSnapshotRequest`, whose `items` field is typed `list[FinancialItemInput]`:

```22:24:app/schemas/financial_health.py
class SubmitSnapshotRequest(BaseModel):
    user_id: UUID
    items: list[FinancialItemInput] = Field(min_length=1)
```

If we fed it `FinancialItem` ORM instances from the existing factory, Pydantic would reject them (it won't coerce an arbitrary ORM object into a `FinancialItemInput` without `from_attributes`, and even then it's fragile). They also serve genuinely different layers: the ORM factory is for persistence/integration tests, the input factory is for service-layer/API input.

So they're not truly duplicates — same field shape, different domain objects. I'd keep both. The naming already signals the distinction (`_item_factory` vs `_item_input_factory`).

If the near-identical bodies bother you, an alternative is to make the input factory reuse the ORM factory's values by delegating through a shared defaults constant — but that couples two layers that should stay independent, so I'd advise against it.

My recommendation: leave all three as they are. Want me to do anything, or shall we move on?

---

**User**

makes sense, leave as is

---

**Cursor**

Sounds good. Leaving all three factories as they are. Let me know what you'd like to tackle next.

