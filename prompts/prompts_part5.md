# Affordability status removal
_Exported on 7/21/2026 at 00:06:46 GMT+1 from Cursor (3.12.10)_

---

**User**

In line with the business logic, users should not see the status classification as it is contrary to the business decision to `Used neutral, factual customer-facing explanations, which are appropriate for customers in financial difficulty and to reflect FCA regulated context`

Tasks
- remove status: AffordabilityStatus from AssessmentResponse schema
- update any tests that validate the affordability status
- no changes need to be made to the service as we still need the status to explanation mapping

Notes
- open to questions/suggestions or any other areas this change might affect

---

**Cursor**

I'll inspect the AssessmentResponse schema and where affordability status is exposed or asserted in tests so we can plan a clean removal from the customer-facing API.

Checking how the API builds responses and whether the frontend or OpenAPI docs expose status.

Clear scope: hide status only on the customer-facing response schema; internal `AssessmentResult`, DB persistence, and service mapping stay. Demo already shows explanation only.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

I'll remove `status` from `AssessmentResponse`, then update the API tests and README.

Done. Affordability status is no longer exposed on API responses.

**Changes**
- Removed `status` from `AssessmentResponse` in [`app/schemas/financial_health.py`](app/schemas/financial_health.py); `AssessmentResult` and service mapping unchanged
- API tests now assert `"status" not in response.json()["assessment"]` instead of reading the enum
- README wording updated so status labels are described as internal, not customer-facing

All 20 API route tests passed.

