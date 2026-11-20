# How the API tests reach the service

This document shows in four diagrams and a table how the API tests in [tests/](../tests/README.md) reach the service in `app/transfer_app.py`, for anyone who reads, changes or explains them: the layers and where each is defined, one request end to end, what runs when and how long each object lives, which fixture provides what to a test, and where two sides must use the same name. The rules the tests check are in [business-rules.md](business-rules.md); how CI starts the service and runs the tests is in the root README's [How it works](../README.md#how-it-works).

## Reading the diagrams

The first and the fourth diagram are flowcharts:

| Mark | Meaning |
|---|---|
| Solid arrow | Our code calls the other side directly, such as `create(amount=…)` |
| Dashed arrow with a label | A framework connects the two sides by a name or convention, which the label states, such as "by fixture name" |
| Thick arrow | An HTTP request between the test process and the service process |
| Rounded box | A framework: pytest, uvicorn, FastAPI |
| Rectangle | Code of this repository |
| Dashed grey box | A `parametrize` argument with its values |
| Cylinder | The `transfers` dictionary, the only state the service keeps |
| Blue, marked ⟨process⟩ | Lives as long as the service process |
| Green, marked ⟨run⟩ | Lives as long as one pytest run |
| Orange, marked ⟨test⟩ | Lives as long as one test case |

The second and the third diagram are UML sequence diagrams. Time runs downwards, and each column is one object with its lifeline:

| Mark | Meaning |
|---|---|
| Solid arrow | A call |
| Dashed arrow | A return, or a call that pytest or FastAPI makes |
| Arrow that bends back to its own column | A step inside that object |
| ✕ at the end of an arrow | The object is destroyed; its column ends there |
| A box partway down a column | The object is created there; before it, the object does not exist |
| `alt` frame | Alternatives: only one of the parts separated by the dashed line happens |
| `loop` frame | The steps inside happen once per item named in its label |
| Coloured band with a label such as SETUP | A phase: setup, body and teardown of a test, or one test case |

A reference such as `conftest.py 50–63` names the file and the lines that define the box; files without a directory are in `tests/` or, for `transfer_app.py`, in `app/`.

Terms: a **fixture** is a function marked `@pytest.fixture`; pytest calls it and passes its result to every test or fixture with a parameter of the same name. `@pytest.mark.parametrize` runs one test function once per listed value; each run is a **test case**, and CI counts test cases. `api` is a fixture and `Api` the class of the object it yields. A **route** is a pair of HTTP method and path that FastAPI maps to a **handler**, a function of `transfer_app.py`.

## The layers and where they are defined

The tests and the service run in two processes that share nothing but HTTP. Inside each process, most connections are made by a framework from a name, not by a call in our code.

```mermaid
%%{init: {"theme": "base", "markdownAutoWrap": false, "flowchart": {"curve": "basis", "wrappingWidth": 400, "nodeSpacing": 40, "rankSpacing": 55}, "themeVariables": {"darkMode": false, "background": "#FFFFFF", "fontSize": "15px", "textColor": "#212121", "titleColor": "#212121", "primaryTextColor": "#212121", "secondaryTextColor": "#212121", "tertiaryTextColor": "#212121", "nodeTextColor": "#212121", "lineColor": "#424242", "edgeLabelBackground": "#FFFFFF", "clusterBkg": "#FAFAFA", "clusterBorder": "#9E9E9E"}}}%%
flowchart TB
  subgraph ALL[" "]
  direction TB
  subgraph TP["Test process · the pytest command"]
    direction LR
    PYT(["`**pytest**
    collects the tests,
    prepares fixtures,
    calls each test
    ⟨run⟩`"])
    TF["`**Test functions**
    tests/test_*.py
    ⟨test⟩`"]
    FXT["`**Per-test fixtures**
    conftest.py: account 44–47,
    create 50–63, transfer_in 66–77
    ⟨test⟩`"]
    API["`**api fixture, Api class**
    conftest.py 23–41
    ⟨run⟩`"]
    SES["`**requests.Session**
    one connection pool
    ⟨run⟩`"]
  end

  subgraph SP["Service process · in the container, or started with python app/transfer_app.py"]
    direction RL
    UV(["`**uvicorn**
    listens on port 8000
    transfer_app.py 134–137
    ⟨process⟩`"])
    RT(["`**FastAPI app, route table**
    built from the decorators
    transfer_app.py 46, 77–131
    ⟨process⟩`"])
    PD["`**pydantic models**
    TransferRequest 28–33,
    ConfirmRequest 36–37`"]
    HD["`**Handlers**
    create_transfer 87–108,
    confirm, execute,
    cancel 116–131`"]
    RL["`**Rule helpers**
    is_allowed 52–57 (R3),
    get_transfer 60–63,
    move 66–74 (R4)`"]
    DB[("`**transfers**
    dictionary in memory, 49
    ⟨process⟩`")]
  end
  end

  PYT -. "calls each test,
  by file and function name" .-> TF
  PYT -. "fills parameters,
  by fixture name" .-> FXT
  TF -- "create(amount=…)" --> FXT
  FXT -- "api.post(…)" --> API
  API -- "session.post(url, json)" --> SES
  TP == "HTTP request from requests.Session to uvicorn:
  POST /transfers, JSON body, port 8000" ==> SP
  UV -- "hands over
  each request" --> RT
  RT -. "builds the model,
  by the handler's annotation" .-> PD
  RT -. "calls the handler,
  by method and path" .-> HD
  PD -. "handed in as request" .-> HD
  HD --> RL
  HD --> DB
  RL --> DB

  classDef run fill:#C8E6C9,stroke:#2E7D32,stroke-width:2px,color:#000
  classDef test fill:#FFE0B2,stroke:#E65100,stroke-width:2px,color:#000
  classDef process fill:#BBDEFB,stroke:#1565C0,stroke-width:2px,color:#000
  classDef plain fill:#FFFFFF,stroke:#546E7A,stroke-width:1.5px,color:#000
  class PYT,API,SES run
  class TF,FXT test
  class UV,RT,DB process
  class PD,HD,RL plain
  style ALL fill:#FFFFFF,stroke:#BDBDBD
  style TP fill:#FAFAFA,stroke:#9E9E9E,color:#212121
  style SP fill:#FAFAFA,stroke:#9E9E9E,color:#212121
```

- No file imports `conftest.py`: pytest finds it in `tests/` and registers each function decorated with `@pytest.fixture` under its name.
- The only explicit calls in the test process are the solid arrows; everything a test receives, pytest hands it by name.
- In the service, the decorators such as `@app.post("/transfers")` fill the route table when the module is imported, before any request arrives.

## One request end to end

The case `R1-EP-valid-2500.50` of `test_amount_in_valid_partition_is_accepted`, with the form the data takes on each step: a parameter value, a Python dict, JSON text, an HTTP request, a pydantic model with a `Decimal`, a stored `Transfer`, and back.

```mermaid
%%{init: {"theme": "base", "sequence": {"actorMargin": 30, "messageMargin": 40, "mirrorActors": false, "boxTextMargin": 6}, "themeVariables": {"darkMode": false, "background": "#FFFFFF", "fontSize": "15px", "textColor": "#212121", "titleColor": "#212121", "primaryTextColor": "#212121", "secondaryTextColor": "#212121", "tertiaryTextColor": "#212121", "lineColor": "#424242", "actorBkg": "#FFFFFF", "actorBorder": "#546E7A", "actorTextColor": "#000000", "actorLineColor": "#90A4AE", "signalColor": "#424242", "signalTextColor": "#000000", "noteBkgColor": "#FFFFFF", "noteBorderColor": "#757575", "noteTextColor": "#000000", "labelBoxBkgColor": "#FFFFFF", "labelBoxBorderColor": "#546E7A", "labelTextColor": "#000000", "loopTextColor": "#000000", "sequenceNumberColor": "#FFFFFF"}}}%%
sequenceDiagram
  autonumber
  box rgb(255, 255, 255) Test process on the left · joined only by HTTP in step 9 · Service process on the right
  participant P as pytest
  participant T as test function<br/>test_amount_limits.py 17–21
  participant C as create fixture<br/>conftest.py 50–63
  participant S as Api and Session<br/>conftest.py 23–41
  participant F as uvicorn, FastAPI<br/>transfer_app.py 46, 87
  participant M as TransferRequest<br/>transfer_app.py 28–33
  participant H as create_transfer<br/>transfer_app.py 88–108
  participant D as transfers<br/>transfer_app.py 49
  end

  rect rgb(255, 255, 255)
  rect rgb(255, 224, 178)
    Note over P: SETUP
    P-->>S: first test only: api fixture opens the Session
    P-->>C: create(api, account), by name
    C-->>P: the inner function create
    P-->>T: test(create, amount="2500.50")
  end

  rect rgb(200, 230, 201)
    Note over P: BODY
    T->>C: create(amount="2500.50")
    C->>C: dict: account, recipient, …
    C->>S: api.post("/transfers", json=dict)
    S->>S: dict → JSON text
    S->>F: HTTP POST /transfers with the JSON
    F->>F: route table → create_transfer
    F->>M: JSON → TransferRequest, by the annotation
    alt amount outside R1, or a field missing
      M-->>F: validation error
      F-->>S: HTTP 422, the handler is never called
    else valid
      M-->>F: TransferRequest, amount Decimal("2500.50")
      F->>H: create_transfer(request), by the route
      H->>D: R2: sum today's transfers of the account
      alt total above the daily limit
        H-->>F: HTTPException 422
        F-->>S: HTTP 422
      else within the limit
        H->>D: store Transfer: id, status "created"
        H-->>F: the Transfer
        F-->>S: HTTP 201, the Transfer as JSON
      end
    end
    S-->>C: requests.Response
    C-->>T: requests.Response
    T->>T: assert 201, "created", amount
  end

  rect rgb(236, 239, 241)
    Note over P: TEARDOWN
    P-->>C: discards create and account
  end
  end
```

- Step 1 happens only in the first test case of the run; for this case, the second, the `api` fixture and its `requests.Session` already exist.
- R1 is checked in step 11, before the handler runs: the `Field(ge=…, le=…, decimal_places=2)` of `TransferRequest` refuses the amount, and `create_transfer` never sees it.
- R2 needs the transfers stored so far, so it is checked in the handler; both refusals reach the test as status 422.
- The `Decimal` stays inside the service: the amount comes back in the JSON as a string, which is why the test compares `Decimal(response.json()["amount"])` with `Decimal(amount)`.

## What runs when

The main steps of one CI run of the job `api-tests`, with the lifespan of each object: a column starts where the object is created and ends with the box where it is destroyed. Installing, and keeping the report between the service log and `docker compose down`, are left out.

```mermaid
%%{init: {"theme": "base", "sequence": {"actorMargin": 30, "messageMargin": 34, "mirrorActors": true}, "themeVariables": {"darkMode": false, "background": "#FFFFFF", "fontSize": "15px", "textColor": "#212121", "titleColor": "#212121", "primaryTextColor": "#212121", "secondaryTextColor": "#212121", "tertiaryTextColor": "#212121", "lineColor": "#424242", "actorBkg": "#FFFFFF", "actorBorder": "#546E7A", "actorTextColor": "#000000", "actorLineColor": "#90A4AE", "signalColor": "#424242", "signalTextColor": "#000000", "noteBkgColor": "#FFFFFF", "noteBorderColor": "#757575", "noteTextColor": "#000000", "labelBoxBkgColor": "#FFFFFF", "labelBoxBorderColor": "#546E7A", "labelTextColor": "#000000", "loopTextColor": "#000000"}}}%%
sequenceDiagram
  participant CI as CI job api-tests
  rect rgb(255, 255, 255)
  CI->>CI: counts the test cases
  create participant SV as service process<br/>⟨process⟩
  CI->>SV: docker compose up --build --detach --wait
  create participant TR as transfers<br/>⟨process⟩
  SV->>TR: importing transfer_app.py creates {}
  SV-->>CI: the health check of compose.yaml passes
  create participant PY as pytest<br/>⟨run⟩
  CI->>PY: pytest
  PY->>PY: collection: imports conftest.py and the test files, one test case per parametrize value

  rect rgb(255, 224, 178)
    Note over PY: TEST CASE 1
    create participant API as api fixture and Session<br/>⟨run⟩
    PY->>API: setup, on first use: GET /health, opens the Session
    create participant A1 as account<br/>⟨test⟩
    PY->>A1: setup
    create participant C1 as create<br/>⟨test⟩
    PY->>C1: setup, with api and account
    PY->>C1: body: the test calls create(amount)
    C1->>API: api.post("/transfers", json=…)
    API->>SV: HTTP POST /transfers
    SV->>TR: stores the transfer
    SV-->>API: HTTP 201
    destroy C1
    PY-xC1: teardown
    destroy A1
    PY-xA1: teardown
  end

  rect rgb(255, 224, 178)
    Note over PY: TEST CASE 2
    create participant A2 as account<br/>⟨test⟩
    PY->>A2: setup, a new account
    create participant C2 as create<br/>⟨test⟩
    PY->>C2: setup, api reused
    C2->>API: api.post
    API->>SV: HTTP POST /transfers
    SV->>TR: stores a second transfer, the first stays
    destroy C2
    PY-xC2: teardown
    destroy A2
    PY-xA2: teardown
  end

  loop every further test case
    PY->>PY: setup, body and teardown as in test case 2
  end

  destroy API
  PY-xAPI: after the yield: closes the Session
  destroy PY
  PY-->>CI: summary, junit XML and exit code, then pytest ends
  CI->>SV: docker compose logs, saved as the service log
  destroy TR
  SV-xTR: gone with the process
  destroy SV
  CI-xSV: docker compose down
  end
```

- The count check compares the number of test cases that `pytest --collect-only` finds with `EXPECTED_TESTS` in `ci.yml`, before the service starts.
- Collection runs before any test: it imports the files and turns each `parametrize` value into a test case of its own; nothing has reached the service yet.
- `scope="session"` makes the `api` fixture run once, when the first test that needs it is set up; its `yield` keeps the `with requests.Session()` block open until the last test has finished.
- `account` and `create` are made again for every test case, so each case gets an account of its own; they are discarded after the test, but the transfers the test created stay in `transfers` until the service stops.

## Which fixture provides what

Three tests, each with the parameters pytest fills for it. Every arrow is made by pytest from a name: a parameter of a test or a fixture names either a fixture or a `parametrize` argument.

```mermaid
%%{init: {"theme": "base", "markdownAutoWrap": false, "flowchart": {"wrappingWidth": 400, "curve": "basis", "nodeSpacing": 30, "rankSpacing": 70}, "themeVariables": {"darkMode": false, "background": "#FFFFFF", "fontSize": "15px", "textColor": "#212121", "titleColor": "#212121", "primaryTextColor": "#212121", "secondaryTextColor": "#212121", "tertiaryTextColor": "#212121", "nodeTextColor": "#212121", "lineColor": "#424242", "edgeLabelBackground": "#FFFFFF", "clusterBkg": "#FAFAFA", "clusterBorder": "#9E9E9E"}}}%%
flowchart LR
  subgraph ALL[" "]
  direction LR
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
  style ALL fill:#FFFFFF,stroke:#BDBDBD
  style CF fill:#FAFAFA,stroke:#9E9E9E,color:#212121
  style TS fill:#FAFAFA,stroke:#9E9E9E,color:#212121
```

- pytest creates each fixture at most once per test case and hands the same object to everyone in that case who names it: the `account` that `test_daily_limit_applies_per_account` receives is the one its `create` uses by default, which is how the test knows which account its transfers went to.
- `create` and `transfer_in` return a function instead of a transfer, so that a test decides when to create a transfer and with which amount, and can create several.
- A `parametrize` argument and a fixture fill a parameter the same way; the only difference is where the value comes from.

## Where the two sides must match

Six hand-overs of a test case work only because both sides spell a name the same way. The steps refer to the request diagram above. Python itself checks ② at the call and ⑥ in the test's own dictionary lookup; pytest, FastAPI and pydantic match ①, ③, ④ and ⑤ while the test runs.

| Hand-over | This side | Must equal | That side | When they differ |
|---|---|---|---|---|
| ① pytest → test, step 4 | `def test_…(create, amount)`, `test_amount_limits.py:17` | parameter name = fixture or `parametrize` name | `def create(…)`, `conftest.py:51`; `parametrize("amount", …)`, `test_amount_limits.py:10` | The test errors at setup: `fixture 'creat' not found`. A `parametrize` name the test lacks fails collection, `function uses no argument 'amount'`, and pytest runs no test at all |
| ② test → create, step 5 | `create(amount=amount)`, `test_amount_limits.py:18` | keyword = parameter name | `def create(amount=…, account_type=…, account_id=None)`, `conftest.py:54` | The test fails with `TypeError: … got an unexpected keyword argument 'amonut'` |
| ③ create → route, steps 9–10 | `session.post(BASE_URL + "/transfers")`, `conftest.py:61` and `31` | method and path = a route | `@app.post("/transfers")`, `transfer_app.py:87` | Status 404 or 405; the test fails on its status assertion, or with a `KeyError` where it reads the body first |
| ④ JSON body → model, step 11 | keys `account`, `recipient`, `account_type`, `amount`, `conftest.py:55–60` | JSON key = field name | fields of `TransferRequest`, `transfer_app.py:28–33` | Status 422 with `"type": "missing"`; a key the model does not know is ignored without an error |
| ⑤ model → handler, step 15 | `class TransferRequest`, `transfer_app.py:28` | annotation = class | `async def create_transfer(request: TransferRequest)`, `transfer_app.py:88` | Without the annotation, FastAPI reads `request` as a query parameter and answers 422 for every body |
| ⑥ response → test, steps 21–24 | fields of `Transfer`: `id`, `status`, …, `transfer_app.py:40–43` | JSON key = field name | `response.json()["status"]`, `test_amount_limits.py:19–21` | The test fails with `KeyError` |
