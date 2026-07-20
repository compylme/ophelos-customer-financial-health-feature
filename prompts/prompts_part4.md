# Country and currency support
_Exported on 7/20/2026 at 23:19:55 GMT+1 from Cursor (3.12.10)_

---

**User**

We want to introduce the ability for financial items and snapshots to accept country_codes and currency. We will be scoping to 3 currencies/countries.

- GB/GBP
- FR/EUR
- US/USD

In scope:
- Intended behaviour would be that the user selects a supported country_code and currency during onboarding (since user management is outside the scope of this task we will be hardcoding a currency and country code to our seeded user)
- The client does not provide currency when submitting a snapshot. The service should pull the currency and country code from the user attributes
- Explanations should now use the preferred currency in their formattimg
- Historical snapshots will also expose the stored currency
- Changing a user's currency affects future snapshots only
- No new currency columns for financial_items, currency is determined during run time

Out of scope:
- FX conversions are not supported on snapshots (currency used for historical snapshots are immutable)

Changes needed:

user model:
country_code: str
currency: str

monthlysnapshot model:
currency: str

curr code and currency should be constrained as strings but enforced

Schemas:
New enums for supported countries/currency codes - actually I dont think this is needed as it will be validated via user management (which is out of scope for this task)

Tests:
model_constraints: validate that unsupported currency codes are rejected
service_integration: validate that the user currency preference is acknowledged in assessment explanations

Factories:
Update factories/fixtures to allow currency configuration

Migration:
Migration is required for the current user table

Notes:
- ask any questions on decisions you are unsure about
- I'm open to suggestions/risks I might have overlooked

---

**Cursor**

Let me read a few key files to nail down the explanation formatting and seed data details.

I have a thorough understanding of the codebase now. Before creating the plan, I have one clarifying question.

**Country/Currency Pairing**

> **Should we enforce that country_code and currency form a valid pair (GB must use GBP, FR must use EUR, US must use USD), or validate each independently (a user could theoretically be GB with EUR)?**
> - Enforce valid pairs (GB↔GBP, FR↔EUR, US↔USD) (Recommended)
> - Validate independently (any supported country + any supported currency)
>
> Answer: Enforce valid pairs but I'm struggling to understand where this will be needed within the current scope. Explain

Good question. Within the current scope, pairing enforcement has limited practical impact because user creation/update is out of scope -- the only user creation happens in the seed script and test factories (both hardcoded by us). The enforcement would primarily be a **data integrity guard** via a DB check constraint, protecting against bad data if someone inserts a user directly or when the user management feature is eventually built.

Given that, I'd recommend we keep it simple for now: define a `SUPPORTED_COUNTRY_CURRENCIES` Python-level mapping (used for currency formatting and as a source of truth), add independent `CHECK` constraints on each column for the allowed values, and defer cross-column pairing validation to the user management feature. This gives us the formatting lookup we need without over-engineering a constraint that no current code path can trigger.

Let me now put together the full plan.

---

**User**

We should also add a new currency column to the monthlyAssessment model so that we can recall what currency the snapshot was generated with 

---

**Cursor**

Good call -- storing `currency` on `MonthlyAssessment` directly makes it self-contained for retrieval without needing to join back to the snapshot. Let me update the plan.

Now update the plan body to reflect the `MonthlyAssessment.currency` addition across models, schemas, migration, service, seed, factories, and tests.

The plan is updated. Here's a summary of what changed:

**`MonthlyAssessment` now also gets a `currency` column.** This means:

- **Model**: new `currency: Mapped[str]` column with a `CHECK` constraint on `monthly_assessments`
- **Schema**: `AssessmentResponse` gains a `currency: str` field
- **Service**: `submit_snapshot` sets `currency` on both the `MonthlySnapshot` and the `MonthlyAssessment` it creates
- **Seed**: each seeded `MonthlyAssessment` gets `currency="GBP"`
- **Migration**: `monthly_assessments` table gets the same `currency VARCHAR(3) NOT NULL DEFAULT 'GBP'` + CHECK constraint treatment
- **Factories**: `assessment_factory` gains a `currency="GBP"` default
- **Tests**: new constraint test for `MonthlyAssessment` with an unsupported currency, and API response assertions updated to check `currency` inside the nested assessment

This makes the assessment fully self-describing -- it can tell you which currency its totals and explanation were generated with without needing to traverse up to the snapshot.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll implement the plan starting with the models, then work through migration, service, schemas, seed, factories, and tests.

Updating factories next, then the test files.

Updating the constraint and integration tests first, then the unit and API tests.

Now updating the unit tests. I'll add a helper for mocking the user and update all `calculate_assessment` calls.

There's a bad edit in the single-item test — fixing that, then updating explanation assertions and submit_snapshot mocks.

Unit and API tests passed. Running integration tests next — I'll reset the test DB schema first so the new columns exist.

All 100 tests passed. Currency and country code support is in place. Summary of what changed:

### Models
- **User**: `country_code` (GB/FR/US) and `currency` (GBP/EUR/USD) with CHECK constraints
- **MonthlySnapshot**: `currency` with CHECK constraint
- **MonthlyAssessment**: `currency` with CHECK constraint

### Service
- Looks up the user on submit and raises `UserNotFound` if missing
- Stamps user currency onto both snapshot and assessment
- Formats explanation amounts with `£` / `€` / `$`

### Schemas
- `SnapshotResponse.currency` and `AssessmentResponse.currency` exposed in API responses

### Seed / factories / migration
- Demo user hardcoded as `GB` / `GBP`
- Factories default to GBP and accept overrides
- Alembic migration `a1b2c3d4e5f6` adds columns with backfill defaults, then drops the defaults

### Tests
- New constraint tests for unsupported codes
- Integration coverage for GBP and EUR explanation formatting
- Unit/API tests updated for currency formatting and response fields

---

**User**

why was this test removed/renamed?
test_rollback_on_commit_failure_leaves_no_partial_state

---

**Cursor**

It was renamed to `test_raises_user_not_found_for_unknown_user` because the behaviour under test changed.

Previously, submitting with a random non-existent `user_id` hit a foreign-key violation at commit time (`IntegrityError`), and the test checked that nothing was left in the DB after rollback.

With the currency work, `submit_snapshot` looks up the user first and raises `UserNotFound` before any insert. So that path never reaches commit/rollback anymore — the FK failure case is gone for an unknown user.

The new test still covers the “unknown user leaves no partial state” guarantee, but asserts the new exception instead of `IntegrityError`.

If you still want an explicit rollback-on-commit-failure test, we can add one back that stubs a real user and forces `commit` to fail (as the unit tests already do with `test_rollback_and_reraise_on_failure`).

---

**User**

no that test now indirectly validates 2 differnt things. Add a new test that validates rollback leaving no partial states 

---

**Cursor**

I'll add a dedicated integration test that forces a commit-time failure with a valid user and asserts nothing partial is left behind.

The unique-constraint approach rolled back the seeded snapshot too (session savepoints). Switching to a forced commit failure with a valid user so we only assert the failed submit leaves nothing behind.

Added `test_rollback_on_commit_failure_leaves_no_partial_state` back as its own test.

It uses a real user, forces a commit-time `IntegrityError` (invalid currency on the snapshot being persisted), and asserts that after the service rolls back there are no leftover snapshots, financial items, or assessments.

`test_raises_user_not_found_for_unknown_user` stays focused only on the early user-lookup path.

---

**User**

we are repeatung the stubbing of user lookup
and submit_snapshot_request_factory seems like a good candidate for a fixture. Thoughts?

---

**Cursor**

Agreed on both — the duplication is real and worth cleaning up.

### User lookup stubbing

Almost every `TestSubmitSnapshot` test does the same two lines:

```python
_stub_user_lookup(mock_session, mock_user)
request = submit_snapshot_request_factory(user_id=mock_user.id)
```

The helper helps a bit, but the call sites still repeat. Better options, in order of preference:

1. **Class-scoped autouse fixture on `TestSubmitSnapshot`** that wires `mock_session.scalar.return_value = mock_user` by default. The one exception (`test_raises_user_not_found`) overrides to `None`. That removes the stub from ~8 tests without changing behaviour elsewhere (`calculate_assessment` tests don't need it).

2. **A composed fixture** e.g. `service_ready_to_submit` that returns `(service, mock_user, request)` already wired. Slightly heavier, but makes happy-path tests very thin.

I’d avoid baking the stub into the shared `service` / `mock_session` fixtures — those are also used by get/history tests that don’t care about user lookup.

### Request fixture

`submit_snapshot_request_factory` is already a factory fixture in `conftest.py`, and that’s the right shape for *variants* (custom items, random user for the not-found case).

What’s missing is a **ready-made request fixture** for the common case:

```python
@pytest.fixture
def submit_snapshot_request(
    mock_user: User,
    submit_snapshot_request_factory: Callable[..., SubmitSnapshotRequest],
) -> SubmitSnapshotRequest:
    return submit_snapshot_request_factory(user_id=mock_user.id)
```

Keep the factory for:
- `test_raises_user_not_found` (random / unmatched `user_id`)
- `test_builds_financial_items_from_request` (custom `items`)

So: factory stays for configurability; add a concrete `submit_snapshot_request` for the default path. Combined with an autouse user-lookup stub on `TestSubmitSnapshot`, most submit tests shrink to asserting behaviour only.

---

**User**

make the change with option 1

---

**Cursor**

I'll add a class-scoped autouse fixture on `TestSubmitSnapshot` to stub user lookup by default, then remove the repeated `_stub_user_lookup` calls.

Done. `TestSubmitSnapshot` now has an autouse fixture that stubs the user lookup by default:

```python
@pytest.fixture(autouse=True)
def _stub_user_lookup(self, mock_session: MagicMock, mock_user: User) -> None:
    mock_session.scalar.return_value = mock_user
```

`test_raises_user_not_found` still overrides to `None`. I also moved `test_submitted_at_is_utc_aware` into that class so it picks up the same stub. All 40 unit tests pass.

---

**User**

Is this needed?
@test_financial_health_service.py (548-563) 
I believe we already validate timezone functionality elsewhere within our test stack

---

**Cursor**

Not really validated elsewhere for **service behaviour**.

This is the only test that asserts `submit_snapshot` sets a UTC-aware `submitted_at`. Other timezone usage is fixture setup (`datetime.now(UTC)` / `API_SUBMITTED_AT` in `conftest.py`) or the API test comparing against a pre-built sample snapshot — neither exercises the service’s `datetime.now(UTC)` path.

Integration tests don’t assert on `submitted_at` timezone at all.

So it’s not redundant with existing coverage. Whether you still want it is a judgement call: it’s a thin guard on a one-liner (`submitted_at=datetime.now(UTC)`). Safe to drop if you’re fine relying on that code being obvious; keep it if you want an explicit regression check against naive datetimes.

---

**User**

update the readme.md referencing the new currency coe/country functionality

---

**Cursor**

Updated [README.md](README.md) in three places:

- **Intro** — how country/currency preferences work, supported pairs, imprint on snapshot/assessment, and historical immutability
- **Demo data** — seeded user is `GB`/`GBP`
- **API endpoints** — currency comes from the user on submit; responses expose `currency` on snapshot and assessment

