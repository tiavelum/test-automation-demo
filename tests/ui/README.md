# UI tests

This directory holds the UI tests of the form page of the money-transfer service, for anyone who reads, runs or extends them: `test_transfer_form.py` checks eight cases through the form with Playwright for Python. The root [README](../../README.md#run-the-ui-tests) gives the commands that run them.

## Files

| File | Contains |
|---|---|
| `test_transfer_form.py` | The cases with Playwright for Python, run by pytest through pytest-playwright |
| `conftest.py` | The fixture `base_url`, which takes the address of the service from `BASE_URL`, so that `page.goto("/")` opens the form page |

## Cases

Each case is named as [../README.md](../README.md#how-a-test-names-its-source) describes. pytest prints the name after the browser, such as `[chromium-R1-BVA-lowest-valid-0.01]`.

| Case | Amount | The page shows |
|---|---|---|
| `R1-BVA-lowest-valid-0.01` | 0.01 | `Transfer <id> created, status created` |
| `R1-EP-valid-2500.50` | 2500.50 | `Transfer <id> created, status created` |
| `R1-BVA-highest-valid-10000.00` | 10000.00 | `Transfer <id> created, status created` |
| `R1-BVA-highest-invalid-below-0.00` | 0.00 | `Rejected: ` and the reason of the service |
| `R1-BVA-lowest-invalid-above-10000.01` | 10000.01 | `Rejected: ` and the reason of the service |
| `R1-EP-invalid-not-a-number` | ten | `Rejected: ` and the reason of the service |
| `R2-BVA-above-limit-0.01` | 10000.00, 10000.00, then 0.01 for one account | `Transfer <id> created, status created` twice, then `Rejected: daily limit exceeded` |
| `R4-ST-new-transfer-starts-created` | 250.00 from a savings account | `Transfer <id> created, status created`, and the service holds the transfer `<id>` in status `created` with the values entered |

A refused R1 case checks the prefix `Rejected: ` and not the reason after it, which the validation library of the service words; the API tests check that the service refuses the amount, with `loc` `["body", "amount"]`. The R2 case checks the whole line, since [docs/business-rules.md](../../docs/business-rules.md#r2-daily-limit) fixes its reason, and it is the one case where the page shows a reason that is a string rather than the first entry of a validation list.

`R4-ST-new-transfer-starts-created` covers the transition of a new transfer into its initial state; beyond that it is an integration check of the page and the service rather than a further state transition test.

Each assertion is an `expect()`, which retries for 5 seconds, the [default of `expect()`](https://playwright.dev/python/docs/test-assertions), so a test needs no wait for the response of the service.

## Writing a case

Give each case an account of its own through the `account` fixture of [../conftest.py](../conftest.py). Find each element by its label or its role, as a user finds it, so that the form page needs no test ids.
