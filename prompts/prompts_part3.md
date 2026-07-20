# API tests for endpoints
_Exported on 7/20/2026 at 21:39:08 GMT+1 from Cursor (3.12.10)_

---

**User**

Implement API tests covering each of the 3 endpoints. Primary goal should be to validate return shapes and validate that errors/exceptions are mapped to the right hgttp statuses

- No need to write specific tests for error handler as those will be covered in the endpoint tests
- Mock the service to make sure we are only validating http/route behaviour

POST /snapshots
- valid requests return 201
- response matches SnapshotResponse
- all invalid states are mapped to the mapped the correct status codes

GET /snapshot/uid/history
- existing history returns 200
- response matches the responses schema (list of historical snapshots)
- all invalid states are mapped to the mapped the correct status codes
- limit is enforced
- history contains only the requested snapshots

GET /snapshot/uid/period
- existing snapshot returns 200
- financial items and assessment are both returned
- all invalid states are mapped to the mapped the correct status codes

- Open to questions and suggestions


---

**Cursor**

Let me also read the existing conftest and unit test file to understand the exact fixture patterns.

I've thoroughly explored the codebase. I have a couple of observations to share before finalizing the plan.

**Observations / suggestions:**

1. **Duplicate limit validation** -- The `limit` parameter on `GET /snapshots/{user_id}/history` is validated twice: first by FastAPI's `Query(ge=1, le=12)`, then by the service's `InvalidHistoryLimit` check. At the HTTP layer, FastAPI's validation fires first, meaning `InvalidHistoryLimit` is unreachable via the API. The API tests should verify FastAPI's 422 for out-of-range limits. The service-level check is still useful as a domain guard if the service is called outside the API, but it won't surface through these tests.

2. **Mock return type** -- The routes call `SnapshotResponse.model_validate(snapshot)` with `from_attributes=True`, which reads attributes off the returned object. A bare `MagicMock` won't work here; the mock service needs to return real `MonthlySnapshot` model instances (constructed in-memory, no DB needed). This keeps the tests honest about serialization without touching a database.

3. **Pydantic request validation** -- Several invalid-input cases (empty items list, zero/negative amounts, empty descriptions, malformed UUIDs) are caught by Pydantic/FastAPI before the service is invoked. These all produce 422s and are worth covering since they validate the route's contract.

---

**User**

This keeps the tests honest about serialization without touching a database.

explain this last bit again

---

**Cursor**

When the route handler runs, it does this:

```python
snapshot = service.submit_snapshot(request=request)
return SnapshotResponse.model_validate(snapshot)
```

`model_validate` with `from_attributes=True` reads real Python attributes off the object -- `snapshot.id`, `snapshot.period`, `snapshot.financial_items[0].amount`, `snapshot.assessment.status`, etc. -- and converts them into the Pydantic response model.

If we gave the mock service a bare `MagicMock()` as its return value, every attribute access would silently return another `MagicMock` object. Pydantic would either accept nonsense values (a `MagicMock` where a `UUID` should be) or fail in confusing ways. Either outcome means the test isn't actually verifying that the route can serialize a real domain object into the expected JSON shape.

By returning a real in-memory `MonthlySnapshot` (with real `FinancialItem` and `MonthlyAssessment` children, all constructed with actual UUIDs, Decimals, dates, etc.), the `model_validate` call in the route exercises the same serialization path it would in production. The test confirms that the route can take a genuine domain object, pass it through Pydantic, and produce JSON that matches the `SnapshotResponse` schema.

The "without touching a database" part just means these model instances are plain Python objects -- we never call `session.add()` or `session.flush()`. They have no database-generated IDs or timestamps; we set everything explicitly. So the tests stay fast, need no Postgres, and still exercise the full serialization pipeline from domain model to HTTP response.

---

**User**

Duplicate limit validation -- The limit parameter on GET /snapshots/{user_id}/history is validated twice: first by FastAPI's Query(ge=1, le=12), then by the service's InvalidHistoryLimit check. At the HTTP layer, FastAPI's validation fires first, meaning InvalidHistoryLimit is unreachable via the API. The API tests should verify FastAPI's 422 for out-of-range limits. The service-level check is still useful as a domain guard if the service is called outside the API, but it won't surface through these tests.

This is a good catch historical limits are already  already enforced in get_history method. this test will create some redundancy, are there any other redundant validations that might be introduced by the proposed tests?



---

**Cursor**

Good question. Let me walk through every proposed test against what already exists.

**No redundancy (genuinely new coverage):**
- All the Pydantic/FastAPI request validation tests (empty items, bad amounts, empty descriptions, malformed UUIDs, invalid date formats) -- these are untested today because the existing unit tests construct `SubmitSnapshotRequest` objects directly in Python, bypassing HTTP parsing entirely. These validate the API's input contract.
- Response shape validation (`SnapshotResponse.model_validate` on JSON) -- untested today.
- Default limit=12 being passed to the service -- untested today.

**Partial overlap but still valuable:**
- `SnapshotAlreadyExists` -> 409 and `SnapshotNotFound` -> 404 -- the service unit tests already verify these exceptions are *raised*. The new tests would verify they're *mapped to the correct HTTP status*. That's the missing half of the chain, and it's the whole point of these API tests. Not redundant.

**Actually redundant (beyond the limit issue):**
- The **generic `DomainError` -> 400 fallback** tests I proposed on POST and GET `/{user_id}/{period}`. No current service method raises a bare `DomainError` -- we'd have to force the mock to raise an exception that can't actually happen through any real endpoint. This is an error-handler-fallback test in disguise, which contradicts your "no dedicated error handler tests" instruction. I'd drop these two cases.

So in total, the items I'd remove from the plan:

1. **Limit out-of-range tests** (already identified) -- FastAPI catches these before our code runs, and the service-level check is already covered in `TestGetHistory`
2. **Generic DomainError -> 400** on both POST and GET period -- contrived scenario, effectively a standalone error handler test

That leaves each proposed test either covering something new (input validation, response shape, HTTP status mapping) or verifying the HTTP layer specifically (which is the gap in the current suite).

Want me to update the plan with these removals, or do you want to adjust anything else first?

---

**User**

update the plan

---

**Cursor**

Plan updated. Here's what changed:

**Removed 5 tests:**
- 3 limit-out-of-range tests on GET history (0, 13, negative) -- redundant since FastAPI's `Query(ge=1, le=12)` fires before the service, and the service's `InvalidHistoryLimit` is already covered in existing unit tests
- 2 generic `DomainError` -> 400 tests on POST and GET period -- no service method actually raises a bare `DomainError`, so these would be error-handler tests in disguise

**Final test count: 20 tests** across 3 classes, each covering only the HTTP-layer gaps that aren't already tested elsewhere (response shape, status code mapping, request validation contract).

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll implement the API route tests per the plan, starting with the test file and fixtures.

Creating the full API routes test file with fixtures and all three test classes.

All 20 API route tests are in place and passing.

**Created:** [tests/unit/test_api_routes.py](tests/unit/test_api_routes.py)

**Setup:**
- `TestClient` with `get_financial_health_service` overridden by a `MagicMock`
- Real in-memory `MonthlySnapshot` objects for serialization
- `seed_database` patched so startup doesn’t need Postgres

**Coverage:**
| Class | Cases |
|-------|-------|
| `TestSubmitSnapshot` | 201 + shape, 409 conflict, 6× 422 validation |
| `TestGetHistory` | 200 list/empty, default & explicit limit, response isolation, 422 bad UUID |
| `TestGetSnapshot` | 200 + nested items/assessment, 404, 422 bad UUID/period |

```
20 passed in 1.08s
```

---

**User**

you've added fixtures to the actual @tests/unit/test_api_routes.py fixtures should live in the dedicated @tests/conftest.py 

---

**Cursor**

Moving the API fixtures into `tests/conftest.py` and updating the test file to use them.

Moved the API fixtures into [tests/conftest.py](tests/conftest.py):

- `in_memory_snapshot_factory`
- `sample_snapshot`
- `valid_submit_payload_factory`
- `mock_service`
- `client`

[tests/unit/test_api_routes.py](tests/unit/test_api_routes.py) now only contains the test classes. All 59 unit tests pass.

---

**User**

all defined variabled should be moved to the top of the file for readability as done with the test db url

---

**Cursor**

Moved the `API_*` constants up next to `TEST_DATABASE_URL` at the top of [tests/conftest.py](tests/conftest.py).

---

**User**

@test_api_routes.py (72-74) Is this asserton necessary since we are already mocking this via mock side effect?

---

**Cursor**

The **409 status** assertion is the one that matters — that verifies `SnapshotAlreadyExists` is mapped correctly.

The exact `detail` string match is mostly redundant. You set the message on the mock and then assert the same string comes back, so you’re really only checking that the handler forwards `exc.message` into `{"detail": ...}`. That’s thin coverage of the error handler, not of route behaviour.

Keeping `assert "detail" in response.json()` (or that `detail` is a non-empty string) is enough if you want the error body shape; matching the literal mock message isn’t necessary for this test’s goal.

---

**User**

At the moment we are returning every financial item as part of snapshot response. A user might have 500 financial items which introduces the added complexity of returning all the line items. We should update @financial_health.py (57-65)  to not return financial items as @financial_health.py (48-55)  already returns the aggregated values.

This will also mean an update to api tests that validate what is returned on the respective endpoints. Actually we might not need to update that since 'model_validates' validates via the schema. @test_api_routes.py (36-46) 

Tasks:
- Update SnapshotResponse to remove financial items

Notes:
- Questions/concerns are welcome
- Raise any oversights in my prompt

---

**Cursor**

You're right that `model_validate` will catch a schema mismatch if we remove the field -- but the tests do more than just call `model_validate`. There are explicit `financial_items` assertions that will break:

- **Line 52**: `assert len(body.financial_items) == 2` in `test_response_contains_all_expected_fields`
- **Lines 302-321**: The entire `test_response_contains_financial_items_and_assessment` test, which asserts on individual item IDs, directions, descriptions, and amounts

These need updating. Additionally, that test's name and purpose ("response contains financial_items and assessment") becomes misleading once `financial_items` is removed -- it should be renamed to just validate the assessment.

One concern: removing `financial_items` from `SnapshotResponse` is a breaking API change for any consumer currently relying on that field. If existing clients depend on it, this would need versioning or a migration path. Flagging this since it wasn't mentioned in your prompt -- happy to proceed if this is intentional.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

Done. Summary of changes:

1. **Schema** ([app/schemas/financial_health.py](app/schemas/financial_health.py)): Removed `FinancialItemResponse` and dropped `financial_items` from `SnapshotResponse`. Responses now only include the aggregated `assessment`.

2. **API tests** ([tests/unit/test_api_routes.py](tests/unit/test_api_routes.py)):
   - Removed the `financial_items` length assertion from `test_response_contains_all_expected_fields`
   - Renamed `test_response_contains_financial_items_and_assessment` → `test_response_contains_assessment` and kept only assessment assertions
   - Dropped unused `Direction` import

All 20 API route tests pass.

---

**User**

Review any grammatical errors in my @DECISIONS.md 

- This should only be a review of errors and not suggestions of what I should add or take out

---

**Cursor**

Grammar and spelling issues only:

**Line 10**
- `snapsot` → `snapshot`
- Awkward clause after `but`: either drop `but` (`…timelines. Corrections would require…`) or rephrase (`…timelines, but corrections would require…`)

**Line 12**
- `Stored derived explanations` → `Store derived explanations` (imperative, to match the other bullets)

**Line 17**
- `how much of the user's data would be needed to be stored` → `how much of the user's data would need to be stored`

**Line 21**
- `customer facing` → `customer-facing`
- `explanations which is appropriate` → `explanations, which are appropriate` (subject is plural)

**Line 22**
- Trailing comma after `advice,` should be a full stop, or continue the sentence

**Line 25**
- `rule based` → `rule-based`
- `percentage of their income` — “their” has no clear antecedent for a singular customer; use `the customer's` or `disposable income as a percentage of income`

**Line 29**
- `manageent` → `management`
- `outsude` → `outside`
- `exercis` → `exercise`
- `left outsude the scope` → `left outside the scope` (after fixing the typo)

**Line 31–32**
- Line break mid-phrase (`verified` / `access token`) is fine stylistically, but there’s a trailing space after `verified` that looks unintentional

**Line 51–54** (duplicate “Frontend next steps” block)
- `tha visualises` → `that visualises`
- Bullet casing is inconsistent: first starts with a capital, the next two with lowercase (`allows`, `displays`)

**Line 60**
- `focussed` → `focused` (US) or keep `focussed` if you prefer British spelling — both are acceptable; the rest of the doc mixes styles (`visualises` is British). Not an error either way.
- `especially focussed around` → `especially focused on` reads more naturally, but that’s borderline style rather than a hard grammar error

---

**User**

make the changes

---

**Cursor**

Applied the grammar and spelling fixes in [DECISIONS.md](DECISIONS.md): typos, verb agreement, hyphenation, the trailing comma, pronoun clarity, bullet casing, and the mid-line break after “verified”.

---

**User**

check in README.md as well for grammatical errors

---

**Cursor**

[README.md](README.md) is in much better shape than `DECISIONS.md`. Only a few minor points:

**Line 43 (setup comment)**
- `# Docker run` is an incomplete fragment. Prefer something like `# Run Postgres with Docker` if you want the comment to read as English.

**Line 95**
- `Failures exit non-zero.` is elliptical. Clearer: `Failures cause a non-zero exit.` or `The process exits with a non-zero status on failure.`

**Lines 16–17**
- Not a grammar error, but the naming is inconsistent: `PostgreSQL` then `Postgres`. Pick one form.

Everything else reads cleanly — no typos, agreement issues, or broken sentences stood out.

