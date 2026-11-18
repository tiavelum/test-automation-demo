# API tests

This directory holds the API tests of the money-transfer service, for anyone who reads, runs or extends them. Each test checks one rule of [docs/business-rules.md](../docs/business-rules.md), and its test case is derived with one black-box test technique.

## How a test names its source

Every parametrised case carries an id, and every other test a docstring, that starts with the rule and the technique, followed by what the case checks: `R1-BVA-lowest-valid-0.01` is a boundary value of rule R1, `R3-DT-D5-savings-low-single` is column D5 of the decision table of rule R3, and `R4-ST-invalid-executed-cancel` is an invalid transition of the state table of rule R4.

| Abbreviation | Technique |
|---|---|
| `EP` | Equivalence partitioning: one representative per valid and invalid partition |
| `BVA` | Boundary value analysis, two-value: each boundary and its nearest neighbour outside the partition |
| `DT` | Decision table testing: one case per column of the full table |
| `ST` | State transition testing: every valid transition, and every invalid one of the state table |

## Files

| File | Rule | Techniques |
|---|---|---|
| `test_amount_limits.py` | R1 amount range, R2 daily limit | EP, BVA |
| `test_confirmation_rules.py` | R3 confirmation rule | DT, EP for inputs outside its conditions |
| `test_status_transitions.py` | R4 transfer status | ST, EP for unknown transfer ids |
| `conftest.py` | | The fixtures: an API client for the base URL in `BASE_URL`, and helpers that create a transfer and bring it into a status |

## Writing a test

Give each test an account of its own through the `account` fixture, which `create` uses by default. The service keeps its transfers in memory for as long as it runs, so a test that shared an account with another would count that test's transfers towards its daily limit, and a second run against the same instance would fail.
