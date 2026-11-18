# test-automation-demo

A test automation demo for anyone who reviews how tests are derived from business rules: a small money-transfer service as the system under test, API tests chosen from its rules with black-box test techniques, UI tests of its form page in Playwright for Python and in the Robot Framework Browser library, and CI that runs them against the service in a container on every change.

## What it is for

It shows two things a test suite needs: a test environment that anyone can rebuild with one command, and test cases that each trace back to a written rule and to the technique that selected them. The techniques are equivalence partitioning, boundary value analysis, decision table testing and state transition testing, from the black-box test techniques that the [ISTQB Certified Tester Foundation Level v4.0](https://istqb.org/certifications/certified-tester-foundation-level-ctfl-v4-0/) covers under test analysis and design.

It also shows how a Robot Framework suite carries over to Playwright: both UI suites check the same cases under the same names.

It is not a payment system: the service keeps its transfers in memory and has no accounts, no authentication and no persistence.

## Getting started

Requires Git 2 or later, Docker 24 or later with Docker Compose v2, and Python 3.13 with pip.

Get the repository and start the service in a container. The command returns once the service answers its health check:

```bash
git clone https://github.com/tiavelum/test-automation-demo.git
cd test-automation-demo
docker compose up --build --detach --wait
```

Install the test dependencies and the browser of Playwright, which on Debian and Ubuntu asks for your password to install the system libraries the browser needs, then run the API tests and the Playwright UI tests against the service at `http://localhost:8000`:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
playwright install --with-deps chromium
pytest
```

The run ends with:

```
============================== 54 passed in 4.22s ==============================
```

## Example

Create a transfer while the service runs:

```bash
curl -s -X POST http://localhost:8000/transfers -H 'Content-Type: application/json' -d '{"account": "CH-1", "recipient": "CH-2", "account_type": "private", "amount": "250.00"}'
```

```
{"account":"CH-1","recipient":"CH-2","account_type":"private","amount":"250.00","id":"8c0e394883be49f9a7a7cb21c714996d","status":"created","created_on":"2026-11-18"}
```

In a browser, `http://localhost:8000/` shows the form that creates a transfer, and `http://localhost:8000/docs` the API reference that the service generates from its code.

## Run the tests of one rule or technique

```bash
pytest -v -k "R3-DT"
```

Each test id starts with its rule and its technique, as [tests/README.md](tests/README.md) describes, so the run selects the eight columns of the decision table of rule R3 and prints one line for each, such as:

```
tests/test_confirmation_rules.py::test_confirmation_follows_decision_table[R3-DT-D5-savings-low-single] PASSED
```

## Run the UI tests with Playwright and with Robot Framework

```bash
pytest -v tests/ui
```

With the service running (in its container, or started as under "Run the service without Docker"), this runs the eight UI cases with Playwright, one line each, such as:

```
tests/ui/test_transfer_form.py::test_amount_in_valid_partition_is_accepted[chromium-R1-BVA-lowest-valid-0.01] PASSED
```

The Robot Framework suite needs Node.js 22, 24 or 26, the versions that the [Browser library 21.0.0 supports](https://pypi.org/project/robotframework-browser/21.0.0/), since it drives Playwright from a Node.js process. Install its Node.js packages and its browser once, then run the same eight cases:

```bash
rfbrowser init chromium
robot --outputdir test-results/robot tests/ui
```

The run ends with `8 tests, 8 passed, 0 failed` and writes its log to `test-results/robot/log.html`. [tests/ui/README.md](tests/ui/README.md) maps each case and each keyword to its Playwright counterpart.

Where Playwright cannot download its browsers, run both suites in an installed Google Chrome instead:

```bash
rfbrowser init --skip-browsers
pytest tests/ui --browser-channel chrome
robot --outputdir test-results/robot --variable CHANNEL:chrome tests/ui
```

## Run the service without Docker

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python app/transfer_app.py
```

The service then prints `Uvicorn running on http://127.0.0.1:8000`. In a second terminal, run the tests in the same virtual environment:

```bash
. .venv/bin/activate
pytest
```

Stop the service with Ctrl+C.

## Stop the service in its container

```bash
docker compose down
```

## Check a change before a pull request

With the service running, run the checks that CI runs; each exits with status 0 when the change passes:

```bash
ruff format --check .
ruff check .
robocop format --check .
robocop check .
pytest
robot --outputdir test-results/robot tests/ui
```

## Content and structure

| Path | Contains |
|---|---|
| `app/` | The service: `transfer_app.py`, the form page `transfer-form.html`, the `Dockerfile` of its image and its pinned `requirements.txt` |
| `tests/` | The API tests and their fixtures; [tests/README.md](tests/README.md) maps each file to its rule and technique |
| `tests/ui/` | The UI tests of the form page, once with Playwright for Python and once with the Robot Framework Browser library; [tests/ui/README.md](tests/ui/README.md) pairs their cases |
| `docs/` | `business-rules.md`, the rules R1 to R4 that the service implements and the tests are derived from |
| `.github/workflows/` | `ci.yml`, the workflow of "How it works" |
| `compose.yaml` | Builds the image from `app/` and starts it on port 8000 with a health check |
| `requirements-dev.txt` | The pinned dependencies of the service, the tests and the checks, for a run without Docker |
| `ruff.toml`, `robocop.toml`, `.editorconfig`, `pytest.ini` | The configuration of the formatter and linter of the Python and of the Robot Framework files, of editors, and of pytest |
| `.env.example` | The environment variables of "Configuration" |
| `project-instructions.md`, `CLAUDE.md` | Rules for Claude sessions that work on this repository; `CLAUDE.md` imports the first |

Open [docs/business-rules.md](docs/business-rules.md) first, then `app/transfer_app.py`, [tests/README.md](tests/README.md) and [tests/ui/README.md](tests/ui/README.md).

## Configuration

The tests and the service read these variables from the environment; `.env.example` lists them.

| Variable | Default | Effect |
|---|---|---|
| `BASE_URL` | `http://localhost:8000` | The address of the service the tests run against |
| `PORT` | `8000` | The port the service listens on when it runs without Docker |
| `HOST` | `127.0.0.1` | The interface the service listens on; the image sets `0.0.0.0` |

## How it works

The tests reach the service only over HTTP at `BASE_URL`, the API tests directly and the UI tests through a browser that opens the form page, so the same tests run against the container that `compose.yaml` starts and against `app/transfer_app.py` started with Python. Playwright for Python and the Browser library drive the same Playwright release, 1.64.1, which `requirements-dev.txt` pins for the first and the Browser library locks for its Node.js process.

On every pull request and every push to `main`, `.github/workflows/ci.yml` runs three jobs. `lint` checks formatting and lint with ruff and Robocop. `api-tests` starts the service with `docker compose up --build --detach --wait`, runs the API tests against it and keeps the JUnit report `api-tests.xml` and the service log for seven days as the workflow artifact `api-test-report`. `ui-tests` installs Chromium for each UI tool, starts the service the same way, runs the Playwright and then the Robot Framework suite, and keeps the JUnit report, the traces and screenshots of failed Playwright tests, the Robot Framework log and report and the service log for seven days as the artifact `ui-test-report`.

## Known limits

- The service loses every transfer when it stops, and the tests leave their transfers behind while it runs; each test uses an account of its own, so a repeated run still passes.
- A transfer states its account type itself, since the service has no store of accounts.
- The daily limit counts days in UTC, so a test run across midnight UTC can see a limit reset.
- No test checks that a transfer of an earlier day stops counting towards the daily limit, because the service reads the clock itself.
- The form page has no confirm or execute step, so the UI tests cover rule R1, the refusal of rule R2 and the status of a new transfer; rule R3 and the events of rule R4 are tested only through the API.
- The UI tests run in Chromium only.

## License

MIT. See [LICENSE](LICENSE).
