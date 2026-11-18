*** Settings ***
Documentation    UI tests of the form page with the Robot Framework Browser library: R1, the
...              amount range, through the form, with equivalence partitioning (EP) and
...              boundary value analysis (BVA), and the transfer the form creates (R4).
...              `test_transfer_form.py` checks the same cases with Playwright for Python.

Library          Browser

Suite Setup      New Browser    chromium    headless=${HEADLESS}    channel=${CHANNEL}
Test Setup       Open The Form


*** Variables ***
${BASE_URL}    %{BASE_URL=http://localhost:8000}
# The browser of Playwright by default; `--variable CHANNEL:chrome` runs an installed Chrome.
${CHANNEL}     ${None}
${HEADLESS}    ${True}
${CREATED}     ^Transfer [0-9a-f]{32} created, status created$
${REFUSED}     ^Rejected:${SPACE}


*** Test Cases ***
R1-BVA-lowest-valid-0.01
    Submit A Transfer    0.01
    The Result Matches    ${CREATED}

R1-EP-valid-2500.50
    Submit A Transfer    2500.50
    The Result Matches    ${CREATED}

R1-BVA-highest-valid-10000.00
    Submit A Transfer    10000.00
    The Result Matches    ${CREATED}

R1-BVA-highest-invalid-below-0.00
    Submit A Transfer    0.00
    The Result Matches    ${REFUSED}

R1-BVA-lowest-invalid-above-10000.01
    Submit A Transfer    10000.01
    The Result Matches    ${REFUSED}

R1-EP-invalid-not-a-number
    Submit A Transfer    ten
    The Result Matches    ${REFUSED}

New Transfer Starts In Created
    [Documentation]    R4, ST: the transfer the form reports is the one the service holds, in its
    ...    initial state created, with the values entered.
    ${account}    Submit A Transfer    250.00    account_type=savings
    ${text}    The Result Matches    ${CREATED}
    ${words}    Evaluate    $text.split()
    ${response}    Http    /transfers/${words}[1]
    Should Be Equal    ${response}[status]    ${200}
    Should Be Equal    ${response}[body][status]    created
    Should Be Equal    ${response}[body][account]    ${account}
    Should Be Equal    ${response}[body][account_type]    savings
    Should Be Equal    ${response}[body][amount]    250.00


*** Keywords ***
Open The Form
    [Documentation]    A new context and page for each test, as the `page` fixture of
    ...    pytest-playwright gives.
    New Context    baseURL=${BASE_URL}
    New Page    /

Submit A Transfer
    [Documentation]    Fills the form the way a user does, finding each field by its label, and
    ...    submits it. Returns the account, which no other test uses (R2).
    [Arguments]    ${amount}    ${account_type}=private
    ${account}    Evaluate    f"CH-{uuid.uuid4().hex[:12]}"    modules=uuid
    Fill The Field Labelled    Account    ${account}
    ${type_field}    Get Element By    Label    Account type
    Select Options By    ${type_field}    value    ${account_type}
    Fill The Field Labelled    Recipient    CH-recipient
    Fill The Field Labelled    Amount in CHF    ${amount}
    ${submit}    Get Element By Role    button    name=Create transfer
    Click    ${submit}
    RETURN    ${account}

Fill The Field Labelled
    [Documentation]    Fills the field whose label is exactly ``label``, as `get_by_label()` of
    ...    Playwright finds it.
    [Arguments]    ${label}    ${text}
    ${field}    Get Element By    Label    ${label}    exact=${True}
    Fill Text    ${field}    ${text}

The Result Matches
    [Documentation]    Returns the result line of the page once it matches ``pattern``. Get Text
    ...    retries until then or until its timeout passes, as `expect()` of Playwright does.
    [Arguments]    ${pattern}
    ${result}    Get Element By Role    status
    ${text}    Get Text    ${result}    matches    ${pattern}
    RETURN    ${text}
