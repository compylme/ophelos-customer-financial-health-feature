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
- The user can track the state of their finances by getting a history of past monthly snapshots and associated assessments

##Snapshot idempotency
The creation of monthly snapshots will be idempotent. A user can have only one snapshot for a given monthly period:

- It prevents historical assessments being overwritten or manipulated
- It avoids the added complexity of maintaining multiple snaphots for the same period
- It ensures that the user's historical timeline remains clear and deterministic.

##Affordability assessment
- As the brief did not define an affordability algorithm, for the purposes of this exercise I will be implementing a simple, deterministic rule based assessment based on the percentage of their income that is disposable


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
- Submnit snapshot request endpoint will not obtain user creds from the payload. Creds will be obtained from authentication
- Using mappers to standardize and control accepted/exposed fields
