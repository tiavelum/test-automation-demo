# UI tests

This directory holds the UI tests of the form page of the money-transfer service, for anyone who compares Playwright for Python with the Robot Framework Browser library: `test_transfer_form.py` and `transfer-form.robot` check the same seven cases, under the same names, through the same Playwright release. The root [README](../../README.md#run-the-ui-tests-with-playwright-and-with-robot-framework) gives the commands that run them.

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
| New transfer starts in created (R4, ST) | 250.00 from a savings account | `Transfer <id> created, status created`, and the service holds the transfer `<id>` in status `created` with the values entered |

A refused case checks the prefix `Rejected: ` and not the reason after it, which the validation library of the service words.

## From a Robot Framework keyword to a Playwright call

| Robot Framework Browser library | Playwright for Python with pytest-playwright |
|---|---|
| `New Browser    chromium` in the suite setup | The session fixture `browser` |
| `New Context    baseURL=${BASE_URL}` and `New Page    /` in the test setup | The fixture `page`: a new context and page for each test, with `base_url` from `conftest.py` |
| `Get Element By    Label    Amount in CHF` | `page.get_by_label("Amount in CHF")` |
| `Get Element By Role    button    name=Create transfer` | `page.get_by_role("button", name="Create transfer")` |
| `Fill Text`, `Select Options By    ...    value`, `Click` | `.fill()`, `.select_option()`, `.click()` |
| `Get Text    ${result}    matches    ${CREATED}` | `expect(result).to_have_text(CREATED)` |
| `Http    /transfers/${id}`, a request from the browser context | `page.request.get(f"/transfers/{id}")` |
| One test per case, each calling the keywords with its amount | One test function parametrised over the cases with `pytest.mark.parametrize` |
| `--variable CHANNEL:chrome` | `--browser-channel chrome` |

## Writing a case

Add each case to both files under the same name, and give it an account of its own: the `account` fixture of [../conftest.py](../conftest.py) in pytest, and the account that `Submit A Transfer` makes and returns in Robot Framework. Find each element by its label or its role, as a user finds it, so that the form page needs no test ids.
