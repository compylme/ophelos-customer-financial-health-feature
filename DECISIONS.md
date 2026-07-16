##Backend scope

I will be building the following
- create affordability assessment
- create monthly snapshots
- get snapshot
- get history

##Frontend scope

I will build a single page frontend that enables monthly assessments and displays a range of historical assessments so that the user can track their progress

##Monthly financial snapshots

- I have decided to build a backend that stores a snapshot of the user's finances on a monthly basis. 
- The contents of that snapshot informs the user's financial assessment. This will be stored so that the assessment can be recalaculated for auditing and debugging
- The user can track the state of their finances by getting a history of past monthly snapshots and associated assessments
- We are limiting the amount of monthly snapshots to 12 per user

##Snapshot retention
- For the purposes of this exercise, each user will be limited to a maximum of 12 monthly snapshots.
In a production environment there would be a scheduled retention job that would identify and delete snapshots to align with applicable leagl and regulatory requirements

##Snapshot idempotency

The creation of monthly snapshots will be idempotent. A user can have only one snapshot for a given monthly period

I have made this decision for the following reasons:

- It prevents historical assessments being overwritten or manipulated
- It avoids the added complexity of maintaining multiple snaphots for the same period
- It ensures that the user's historical timeline remains clear and deterministic.

The tradeoff genuine mistakes cannot be corrected through the standard submission flow, coreection woulf require manual intervention

In a production system, the intervention would require the appropriate authorization/auditing

##Affordability assessment

- As the brief did not define an affordability algorithm, for the purposes of this exercise I will be implementing a simple, deterministic rule based assessment based on the percentage of their income that is disposable
- Every assessment will be reproducible from stored inputs
- The assessment result will always include an explanation
- The assessment result will not include any financial_items for the following reasons, to simplify the text that will bedisplayed to the user
- There should be no personal identifiable information that can be tied to the user
- The assessment result will be sensitive to text that could possibly shame the user/imply blame
- The assessment will not be presented as financial advise


##Logging

- We log application actions for traceablity and observability whilst not exposing user pii

##User management and authentication

I will be seeding users and their data for demo purposes. 

As a result this demo will not include API/services around
- user account management
- authZ
- authN. 

In a production environment, these services would need to be implemented or integrated with an existing identity provider to ensure controlled user access 

##Testing
- Unit Tests
- Integration Tests
- API Tests


##Future scope
- Hardcoded values such as affordability threshold values will be moved to and imported from an env file 
