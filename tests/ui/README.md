# UI tests

This directory holds the UI tests of the form page of the money-transfer service, for anyone who compares Playwright for Python with the Robot Framework Browser library: `test_transfer_form.py` and `transfer-form.robot` check the same eight cases, under the same names, through the same Playwright release. The root [README](../../README.md#getting-started) gives the commands that run them.

## Files

| File | Contains |
|---|---|
| `test_transfer_form.py` | The cases with Playwright for Python, run by pytest through pytest-playwright |
| `transfer-form.robot` | The same cases with the Robot Framework Browser library |
| `conftest.py` | The fixture `base_url`, which takes the address of the service from `BASE_URL`, so that `page.goto("/")` opens the form page |

## Cases

Each case is named as [../README.md](../README.md#how-a-test-names-its-source) describes. pytest prints the name after the browser, such as `[chromium-R1-BVA-lowest-valid-0.01]`; Robot Framework uses it as the test name.

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

## From a Robot Framework keyword to a Playwright call

| Robot Framework Browser library | Playwright for Python with pytest-playwright |
|---|---|
| `New Browser    chromium` in the suite setup | The session fixture `browser` |
| `New Context    baseURL=${BASE_URL}` and `New Page` in the test setup | The fixture `page`: a new context and page for each test, with `base_url` from `conftest.py` |
| `Go To    /` in `Submit A Transfer` | `page.goto("/")` in `submit_transfer` |
| `Get Element By    Label    Amount in CHF    exact=${True}` | `page.get_by_label("Amount in CHF", exact=True)` |
| `Get Element By Role    button    name=Create transfer` | `page.get_by_role("button", name="Create transfer")` |
| `Fill Text`, `Select Options By    ...    value`, `Click` | `.fill()`, `.select_option()`, `.click()` |
| `Get Text    ${result}    matches    ${CREATED}` | `expect(result).to_have_text(CREATED)` |
| Waits up to 10 seconds for the element, then retries the assertion for 1 second, the [defaults of `timeout` and `retry_assertions_for`](https://robotframework-browser.org/docs/concepts/assertions) | Retries the assertion for 5 seconds, the [default of `expect()`](https://playwright.dev/python/docs/test-assertions) |
| `Http    /transfers/${id}`, a request from the browser context | `page.request.get(f"/transfers/{id}")` |
| One test per case, each calling the keywords with its amount | Test functions parametrised over their cases with `pytest.mark.parametrize`, each case with its name as its id |
| `--variable CHANNEL:chrome` | `--browser-channel chrome` |

## Writing a case

Add each case to both files under the same name, and give it an account of its own: the `account` fixture of [../conftest.py](../conftest.py) in pytest, and the account that `Submit A Transfer` makes and returns in Robot Framework, which a case passes back to it as `account` for a further transfer of the same account. Find each element by its label or its role, as a user finds it, so that the form page needs no test ids.
