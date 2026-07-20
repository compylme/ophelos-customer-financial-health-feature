**Product and domain**
- Build a monthly financial-health assessment API:
    - Customers submit income and expenditure items
    - The system calculates an affordability status and explanation
    - Customers can retrieve previous monthly assessments to track changes over time

- Treat each monthly submission as an immutable snapshot:
    - A user can submit only one snapshot for a given month
    - Existing snapshots are not silently overwritten
    - Removes the complexity of managing multiple versions of the same snapshot and protects the integrity of historical timelines, but corrections would require explicit/manual intervention rather than mutation

- Store derived explanations in the database as part of the snapshot:
    - The generated explanation is stored alongside the assessment so that each immutable snapshot preserves the exact wording produced at submission time. In a production environment, I would version assessment rules mapped to a table that contains explanations but not related to any customer
    - As calculation logic evolves/new languages are supported, we can simply update the mapping to the new explanation text

- Limit history to 12 monthly snapshots per user:
    - This was an assumption made on how much of the user's data would need to be stored and processed by the system.
    - In a production environment, this would be governed by the needs of the business and FCA regulations.

- Distinguish different financial situations with separate statuses which are mapped to different explanations:
    - Used neutral, factual customer-facing explanations, which are appropriate for customers in financial difficulty and to reflect FCA regulated context
    - Handled all possible outcomes meaningfully taking care not to provide unsolicited financial advice.

- Affordability assessment:
    - As the brief did not define an affordability algorithm, for the purposes of this exercise I implemented a simple, deterministic rule-based assessment based on disposable income as a percentage of income

- Currency handling:
   - The api currently supports 3 currencies: GBP, EUR and USD.
   - In a production environment, the user would be able to select their preferred currency from a list of supported currencies during user onboarding
   - When snapshots are generated, the currency is derived from the user's preferred currency
   - In line with the snapshot's immutable nature, the currency is not allowed to be changed after the snapshot is generated

- Frontend demo page:
    - A simple html/css demo page to help demonstrate the API in action.
    - The page allows you to submit a new snapshot for the current month and view the history of snapshots for the demo user.

**What was left out and what would be built next**
- Implement secure statement sharing via a time-limited link
- Generate a PDF export of the statement with appropriate branding
   - The above were left out due to time constraints as generating time limited secure statements raises complexities around but not limited to:
        - User authentication and authorization
        - Token expiry management
        - enforcement of link expiration
        - Extensive testing and validation of the secure statement sharing mechanism

- User management and authentication: 
    - User registration, login and identity management were deliberately left outside the scope of this exercise. I assumed that Ophelos would already have an existing identity provider and user management system.

    - For simplicity, the current API accepts a user_id as part of the request. In a production implementation, the authenticated user's identity should instead be derived from a verified access token or session.

    - Steps would be:  
        - integrate with an existing identity provider
        - validate authentication credentials at the API boundary
        - derive the user identity from the authenticated principal
        - enforce authorization so users can access only their own data
        - remove user_id from the request payload
        - add tests covering unauthenticated, forbidden and cross-user access

- Frontend implementation:
    I deliberately prioritised the assessment domain, persistence model, API
    contract and automated tests over building a complex frontend within the available time.

    The REST API and Swagger UI provide a complete demonstrable workflow, while
    keeping the solution within the application types explicitly permitted by the
    brief.

    - Steps would be:
        - Lightweight customer interface that visualises disposable income and affordability status over time
        - Allows customers to enter their current monthly income and expenditure
        - Displays the assessment in a clear, understandable format


**Test coverage**
- Unit Tests: Full coverage of all business logic functions and classes including edge cases
- Integration Tests: Coverage of repository and service layer interactions with the database
- API Tests: Coverage of all API endpoints especially focused on happy path return shapes, error/exception mapping to HTTP status codes
