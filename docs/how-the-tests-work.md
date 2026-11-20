# How the API tests reach the service

This document shows in five diagrams how the API tests in [tests/](../tests/README.md) reach the service in `app/transfer_app.py`, for anyone who reads, changes or explains them: the layers and where each is defined, one request end to end, what runs when and how long each object lives, which fixture provides what to a test, and where two sides must use the same name. The rules the tests check are in [business-rules.md](business-rules.md); how CI starts the service and runs the tests is in the root README's [How it works](../README.md#how-it-works).

## Reading the diagrams

| Mark | Meaning |
|---|---|
| Solid arrow | Our code calls the other side directly, such as `create(amount=…)` |
| Dashed arrow with a label | A framework connects the two sides by a name or convention, which the label states, such as "by fixture name" |
| Thick arrow | An HTTP request or response between the test process and the service process |
| Rounded box | A framework: pytest, uvicorn, FastAPI |
| Rectangle | Code of this repository |
| Cylinder | The `transfers` dictionary, the only state the service keeps |
| Blue, marked ⟨process⟩ | Lives as long as the service process |
| Green, marked ⟨run⟩ | Lives as long as one pytest run |
| Orange, marked ⟨test⟩ | Lives as long as one test case |
| Grey | A step of the CI job, collection or a clean-up, outside these lifespans |

A reference such as `conftest.py 50–63` names the file and the lines that define the box; files without a directory are in `tests/` or, for `transfer_app.py`, in `app/`.

## The layers and where they are defined

The tests and the service run in two processes that share nothing but HTTP. Inside each process, most connections are made by a framework from a name, not by a call in our code.

```mermaid
%%{init: {"theme": "base", "markdownAutoWrap": false, "flowchart": {"curve": "basis", "wrappingWidth": 400}, "themeVariables": {"fontSize": "15px", "lineColor": "#424242", "edgeLabelBackground": "#FFFFFF"}}}%%
flowchart TB
  subgraph TP["Test process · started by pytest"]
    direction TB
    PYT(["`**pytest**
    collects the tests, prepares
    fixtures, calls each test
    ⟨run⟩`"])
    TF["`**Test functions**
    tests/test_*.py
    ⟨test⟩`"]
    FXT["`**Per-test fixtures**
    conftest.py: account 44–47,
    create 50–63, transfer_in 66–77
    ⟨test⟩`"]
    API["`**api fixture and Api class**
    conftest.py 23–41
    ⟨run⟩`"]
    SES["`**requests.Session**
    one connection pool
    ⟨run⟩`"]
  end

  subgraph SP["Service process · container or python app/transfer_app.py"]
    direction TB
    UV(["`**uvicorn**
    listens on port 8000
    transfer_app.py 151–154
    ⟨process⟩`"])
    RT(["`**FastAPI app and route table**
    built from the decorators
    transfer_app.py 59, 90–148
    ⟨process⟩`"])
    PD["`**pydantic models**
    TransferRequest 41–46,
    ConfirmRequest 49–50`"]
    HD["`**Handlers**
    create_transfer 100–122,
    confirm, execute, cancel 130–148`"]
    RL["`**Rule helpers**
    is_allowed 65–70 (R3),
    move 79–87 (R4)`"]
    DB[("`**transfers**
    dictionary in memory, 60
    ⟨process⟩`")]
  end

  PYT -. "calls each test,
  by file and function name" .-> TF
  PYT -. "fills parameters,
  by fixture name" .-> FXT
  TF -- "create(amount=…)" --> FXT
  FXT -- "api.post(…)" --> API
  API -- "session.post(url, json)" --> SES
  SES == "HTTP request: POST /transfers
  JSON body · port 8000" ==> UV
  UV -- "hands over each request" --> RT
  RT -. "builds the model from JSON,
  by the handler's annotation" .-> PD
  RT -. "calls the handler,
  by method and path" .-> HD
  PD -. "handed in as request,
  by the annotation" .-> HD
  HD --> RL
  HD --> DB
  RL --> DB

  classDef run fill:#C8E6C9,stroke:#2E7D32,stroke-width:2px,color:#000
  classDef test fill:#FFE0B2,stroke:#E65100,stroke-width:2px,color:#000
  classDef process fill:#BBDEFB,stroke:#1565C0,stroke-width:2px,color:#000
  classDef plain fill:#FFFFFF,stroke:#546E7A,color:#000
  class PYT,API,SES run
  class TF,FXT test
  class UV,RT,DB process
  class PD,HD,RL plain
  style TP fill:#FAFAFA,stroke:#9E9E9E
  style SP fill:#FAFAFA,stroke:#9E9E9E
```

- No file imports `conftest.py`: pytest finds it in `tests/` and registers each function decorated with `@pytest.fixture` under its name.
- The only explicit calls in the test process are the solid arrows; everything a test receives, pytest hands it by name.
- In the service, the decorators such as `@app.post("/transfers")` fill the route table when the module is imported, before any request arrives.

## One request end to end

The case `R1-EP-valid-2500.50` of `test_amount_in_valid_partition_is_accepted`, with the form the data takes on each hop: a parameter value, a Python dict, JSON text, an HTTP request, a pydantic model with a `Decimal`, and back.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"fontSize": "15px", "actorBkg": "#FFFFFF", "actorBorder": "#546E7A", "actorTextColor": "#000000", "actorLineColor": "#90A4AE", "signalColor": "#424242", "signalTextColor": "#000000", "noteBkgColor": "#FFFDE7", "noteBorderColor": "#BDBDBD", "noteTextColor": "#000000", "labelBoxBkgColor": "#FFFFFF", "labelBoxBorderColor": "#546E7A", "loopTextColor": "#000000", "sequenceNumberColor": "#FFFFFF"}}}%%
sequenceDiagram
  autonumber
  box rgb(255, 250, 242) Test process
  participant P as pytest
  participant T as test function<br/>test_amount_limits.py 17–21
  participant C as create fixture<br/>conftest.py 50–63
  participant S as Api and Session<br/>conftest.py 23–41
  end
  box rgb(240, 247, 255) Service process
  participant F as uvicorn and FastAPI<br/>transfer_app.py 59, 100
  participant M as TransferRequest<br/>transfer_app.py 41–46
  participant H as create_transfer<br/>transfer_app.py 101–122
  end

  rect rgb(255, 243, 224)
    Note over P,C: Setup of the test: case R1-EP-valid-2500.50, so amount = "2500.50" (parametrize, lines 9–16)
    P-->>S: first test only: runs the api fixture, GET /health, opens the Session
    P-->>C: calls the fixture create(api, account), by its name, after account
    C-->>P: returns the inner function create (lines 54–61)
    P-->>T: calls test(create=inner create, amount="2500.50")
  end

  rect rgb(232, 245, 233)
    Note over T,H: The test body
    T->>C: create(amount="2500.50")
    Note over C: Python dict: account "CH-…" (own account), recipient,<br/>account_type "private", amount "2500.50"
    C->>S: api.post("/transfers", json=body)
    Note over S: dict becomes JSON text
    S->>F: HTTP POST http://localhost:8000/transfers, JSON body
    Note over F: route table: POST /transfers → create_transfer
    F-->>M: JSON → TransferRequest, by the handler's annotation
    alt amount outside R1, or a field missing
      M-->>F: validation error
      F-->>S: HTTP 422, the error as JSON, and the handler is never called
    else valid
      M-->>F: TransferRequest, amount as Decimal("2500.50")
      F-->>H: create_transfer(request=TransferRequest), by the route
      Note over F,H: R2: sums the account's transfers of today in transfers (line 60),<br/>and if within the limit stores a Transfer with id, status "created", created_on
      alt daily total above 20000.00 (R2)
        H-->>F: raises HTTPException 422
        F-->>S: HTTP 422, detail "daily limit exceeded"
      else within the limit
        H-->>F: Transfer
        F-->>S: HTTP 201, the Transfer as JSON
      end
    end
    S-->>C: requests.Response
    C-->>T: requests.Response
    Note over T: assert status 201, status "created", amount unchanged (lines 19–21)
  end

  rect rgb(236, 239, 241)
    Note over P,C: Teardown of the test: account and create are discarded, while api and its Session stay for the next test
  end
```

- R1 is checked before the handler runs: the `Field(ge=…, le=…, decimal_places=2)` of `TransferRequest` refuses the amount, and `create_transfer` never sees it.
- R2 needs the transfers stored so far, so it is checked in the handler; both refusals reach the test as status 422.
- The test sees only the `requests.Response`; that the service turned the amount into a `Decimal` shows in the JSON it sends back.

## What runs when

The order of one CI run of the job `api-tests`, not to scale. Each bar lives as long as its colour says: the service and its `transfers` for the whole job, the `api` fixture and its `requests.Session` for the pytest run, and `account` and `create` for one test case.

```mermaid
%%{init: {"theme": "base", "gantt": {"barHeight": 24, "barGap": 6, "topPadding": 40, "leftPadding": 190, "fontSize": 14, "sectionFontSize": 14, "numberSectionStyles": 2}, "themeVariables": {"fontSize": "14px", "sectionBkgColor": "#FFFFFF", "altSectionBkgColor": "#F5F5F5", "sectionBkgColor2": "#FFFFFF", "taskBkgColor": "#FFE0B2", "taskBorderColor": "#E65100", "taskTextColor": "#000000", "taskTextDarkColor": "#000000", "taskTextOutsideColor": "#000000", "taskTextLightColor": "#000000", "activeTaskBkgColor": "#C8E6C9", "activeTaskBorderColor": "#2E7D32", "doneTaskBkgColor": "#BBDEFB", "doneTaskBorderColor": "#1565C0", "critBkgColor": "#ECEFF1", "critBorderColor": "#546E7A", "gridColor": "#E0E0E0"}}}%%
gantt
  dateFormat HH:mm:ss
  axisFormat ·
  todayMarker off

  section CI job api-tests
    count check – pytest --collect-only, 46 expected   :crit, c1, 00:00:00, 00:00:06
    docker compose up --build --wait                  :crit, c2, 00:00:06, 00:00:16
    pytest – runs every test case                     :crit, c3, 00:00:16, 00:01:32
    save the service log                              :crit, c4, 00:01:32, 00:01:35
    docker compose down                               :crit, c5, 00:01:35, 00:01:40

  section Service ⟨process⟩
    image built, python transfer_app.py starts uvicorn :done, s1, 00:00:06, 00:00:13
    health check of compose.yaml passes               :done, s2, 00:00:13, 00:00:16
    answers HTTP requests on port 8000                :done, s3, 00:00:16, 00:01:35
    transfers {} – empty at start, grows with every test, gone at stop :done, s4, 00:00:10, 00:01:37

  section pytest run ⟨run⟩
    collection – import conftest.py and test files, expand parametrize :active, r1, 00:00:16, 00:00:22
    api up to yield – GET /health, Session open        :active, r2, 00:00:22, 00:00:25
    api and Session alive, shared by every test        :active, r3, 00:00:25, 00:01:26
    api after yield – Session closed                   :crit, r4, 00:01:26, 00:01:28
    report – summary and junit XML                     :active, r5, 00:01:28, 00:01:32

  section Test 1 ⟨test⟩
    setup – api on first use, then account, then create :t1a, 00:00:22, 00:00:28
    body – create(amount) sends POST, asserts          :t1b, 00:00:28, 00:00:36
    teardown – account and create discarded           :crit, t1c, 00:00:36, 00:00:38

  section Test 2 ⟨test⟩
    setup – a new account, a new create, api reused   :t2a, 00:00:38, 00:00:41
    body                                             :t2b, 00:00:41, 00:00:49
    teardown                                         :crit, t2c, 00:00:49, 00:00:51

  section Tests 3 to 46 ⟨test⟩
    the same, once per test case                     :t3, 00:00:51, 00:01:26
```

- Before any test: collection imports the files and turns each `parametrize` value into a test case of its own; nothing has reached the service yet.
- `scope="session"` makes the `api` fixture run once, when the first test that needs it is set up; its `yield` keeps the `with requests.Session()` block open until the last test has finished.
- `account` and `create` run again for every test case, so each case gets an account of its own; their objects are discarded after the test, but the transfers the test created stay in the service until it stops.

## Which fixture provides what

Three tests, each with the parameters pytest fills for it. Every arrow is made by pytest from a name: a parameter of a test or a fixture names either a fixture or a `parametrize` argument.

```mermaid
%%{init: {"theme": "base", "markdownAutoWrap": false, "flowchart": {"wrappingWidth": 400, "curve": "basis", "nodeSpacing": 30, "rankSpacing": 70}, "themeVariables": {"fontSize": "15px", "lineColor": "#424242", "edgeLabelBackground": "#FFFFFF"}}}%%
flowchart LR
  classDef run fill:#C8E6C9,stroke:#2E7D32,stroke-width:2px,color:#000
  classDef test fill:#FFE0B2,stroke:#E65100,stroke-width:2px,color:#000
  classDef data fill:#ECEFF1,stroke:#546E7A,stroke-width:2px,color:#000,stroke-dasharray:4 3
  classDef fn fill:#FFFFFF,stroke:#424242,stroke-width:1.5px,color:#000

  subgraph CF["tests/conftest.py · fixtures, found by pytest without an import"]
    direction TB
    API["`**api** ⟨run⟩
    conftest.py:34–41
    scope=session
    yields Api(session)`"]
    ACC["`**account** ⟨test⟩
    conftest.py:44–47
    returns 'CH-' + 12 hex digits`"]
    CRE["`**create** ⟨test⟩
    conftest.py:50–63
    returns the function
    create(amount, account_type, account_id)`"]
    TIN["`**transfer_in** ⟨test⟩
    conftest.py:66–77
    returns the function
    transfer_in(status)`"]
  end

    PA["`@pytest.mark.parametrize
    **amount**
    test_amount_limits.py:9–16
    '0.01', '2500.50', '10000.00'`"]
    PS["`@pytest.mark.parametrize
    **start, event, target**
    test_status_transitions.py:26–34
    four valid transitions`"]

  subgraph TS["Test functions · one test case per parameter set"]
    direction TB
    T1["`test_amount_in_valid_partition_is_accepted(**create, amount**)
    test_amount_limits.py:17 · 3 cases`"]
    T2["`test_daily_limit_applies_per_account(**create, account**)
    test_amount_limits.py:67 · 1 case`"]
    T3["`test_valid_transition(**api, transfer_in, start, event, target**)
    test_status_transitions.py:35 · 4 cases`"]
  end

  API -. "api" .-> CRE
  ACC -. "account" .-> CRE
  API -. "api" .-> TIN
  CRE -. "create" .-> TIN

  CRE -. "create" .-> T1
  PA -. "amount" .-> T1
  CRE -. "create" .-> T2
  ACC -. "account · same value" .-> T2
  PS -. "start, event, target" .-> T3
  TIN -. "transfer_in" .-> T3
  API -. "api · one Api for all tests" .-> T3

  class API run
  class ACC,CRE,TIN test
  class PA,PS data
  class T1,T2,T3 fn
  style CF fill:#FAFAFA,stroke:#9E9E9E
  style TS fill:#FAFAFA,stroke:#9E9E9E
```

- pytest creates each fixture at most once per test case and hands the same object to everyone in that case who names it: the `account` that `test_daily_limit_applies_per_account` receives is the one its `create` uses by default, which is how the test knows which account its transfers went to.
- `create` and `transfer_in` return a function instead of a transfer, so that a test decides when to create a transfer and with which amount, and can create several.
- A `parametrize` argument and a fixture fill a parameter the same way; the only difference is where the value comes from.

## Where the two sides must match

Each of the six hand-overs of a test case works only because both sides use the same name. Only the solid arrow is checked by Python at the call; the dashed and thick ones are matched by a framework at run time.

```mermaid
%%{init: {"theme": "base", "markdownAutoWrap": false, "flowchart": {"wrappingWidth": 500, "nodeSpacing": 20, "rankSpacing": 60, "padding": 10}, "themeVariables": {"fontSize": "15px", "lineColor": "#424242", "edgeLabelBackground": "#FFFFFF", "fontFamily": "Arial"}}}%%
flowchart TB
  classDef tp fill:#FFF3E0,stroke:#E65100,stroke-width:2px,color:#000
  classDef sp fill:#E3F2FD,stroke:#1565C0,stroke-width:2px,color:#000

  subgraph I1["① pytest hands values to the test function"]
    direction LR
    A1["`*test process* · test_amount_limits.py:17
    def test_…(**create**, **amount**)`"]
    B1["`*test process* · conftest.py:50 and test_amount_limits.py:10
    def **create**(api, account) · parametrize(**'amount'**, …)`"]
    B1 -. "pytest matches parameter name = fixture name or parametrize name" .-> A1
  end

  subgraph I2["② The test calls the function that create returned"]
    direction LR
    A2["`*test process* · test_amount_limits.py:18
    create(**amount**=amount)`"]
    B2["`*test process* · conftest.py:54
    def create(**amount**='100.00', **account_type**='private', **account_id**=None)`"]
    A2 -- "Python matches keyword = parameter name, at the call" --> B2
  end

  subgraph I3["③ create sends the request to the service"]
    direction LR
    A3["`*test process* · conftest.py:61 and 31
    api.post(**'/transfers'**, json=body) → session.**post**(BASE_URL + path)`"]
    B3["`*service process* · transfer_app.py:100
    @app.**post**(**'/transfers'**, status_code=201)`"]
    A3 == "FastAPI matches method + path = a route of the table" ==> B3
  end

  subgraph I4["④ The JSON body becomes a TransferRequest"]
    direction LR
    A4["`*test process* · conftest.py:55–60
    body keys **account**, **recipient**, **account_type**, **amount**`"]
    B4["`*service process* · transfer_app.py:41–46
    TransferRequest fields **account**, **recipient**, **account_type**, **amount**`"]
    A4 == "pydantic matches JSON key = field name, then checks type and range" ==> B4
  end

  subgraph I5["⑤ FastAPI hands the model to the handler"]
    direction LR
    A5["`*service process* · transfer_app.py:41
    class **TransferRequest**(BaseModel)`"]
    B5["`*service process* · transfer_app.py:101
    def create_transfer(request: **TransferRequest**) -> **Transfer**`"]
    A5 -. "FastAPI reads the annotation and parses the body into that class" .-> B5
  end

  subgraph I6["⑥ The answer goes back to the test"]
    direction LR
    A6["`*service process* · transfer_app.py:53–56 and 122
    return transfer · Transfer adds **id**, **status**, **created_on**`"]
    B6["`*test process* · test_amount_limits.py:19–21
    response.status_code · response.json()[**'status'**] · [**'amount'**]`"]
    A6 == "the test reads JSON keys = field names of Transfer" ==> B6
  end

  I1 ~~~ I2 ~~~ I3 ~~~ I4 ~~~ I5 ~~~ I6

  class A1,B1,A2,B2,B6 tp
  class B3,B4,A5,B5,A6 sp
  class A3,A4 tp
  style I1 fill:#FAFAFA,stroke:#9E9E9E
  style I2 fill:#FAFAFA,stroke:#9E9E9E
  style I3 fill:#FAFAFA,stroke:#9E9E9E
  style I4 fill:#FAFAFA,stroke:#9E9E9E
  style I5 fill:#FAFAFA,stroke:#9E9E9E
  style I6 fill:#FAFAFA,stroke:#9E9E9E
```

What happens when the two sides of a hand-over do not match:

| Hand-over | Mismatch | What you see |
|---|---|---|
| ① parameter → fixture | A parameter names no fixture, such as `creat` | The test errors at setup: `fixture 'creat' not found` |
| ① parameter → parametrize | `parametrize` names an argument the test does not have | Collection fails, `function uses no argument 'amount'`, and pytest runs no test at all |
| ② keyword → parameter | `create(amonut="1.00")` | The test fails with `TypeError: … got an unexpected keyword argument 'amonut'` |
| ③ method and path → route | A path the route table lacks, or another method on a known path | Status 404 or 405; the test fails on its status assertion |
| ④ JSON key → field | A required key missing or misspelled, or a value outside its type or range | Status 422 with `"type": "missing"` or the failed check; a key the model does not know is ignored without an error |
| ⑤ annotation → body | The annotation `: TransferRequest` removed | FastAPI reads `request` as a query parameter and answers 422 for every body |
| ⑥ JSON key → test | The test reads a key the response lacks | The test fails with `KeyError` |
