Repository tiavelum/test-automation-demo.

These are the rules for a Claude session that works on this public test automation demo: a money-transfer service as the system under test, API tests and UI tests, the latter in Playwright for Python and in the Robot Framework Browser library, derived from its business rules with black-box test techniques, and CI that runs them against the service in a container.

Public content: Never add personal data of the owner or of anyone else to a file, a commit, an issue or a pull request: no names, addresses, employers or details of job applications. The one exception is the owner's name in the copyright line of `LICENSE`, which WR-6 of tiavelum/engineering-standards asks for.

Rules before tests: A change to what the service does changes `docs/business-rules.md` in the same pull request. Every new test names the rule and the technique it is derived from in its id or docstring, in the form `tests/README.md` describes, and uses an account of its own: the `account` fixture in pytest, the account that `Submit A Transfer` makes in Robot Framework.

Small service: Keep the service in the single module `app/transfer_app.py`. A second module would bring the layers, diagram and checks of the module-layers standard of tiavelum/engineering-standards.

Pinned dependencies: Pin a new dependency together with every transitive dependency it installs, in `app/requirements.txt` for the service and in `requirements-dev.txt` for the tests and the checks.

Done: A change is ready when the following pass with the service running, and then the CI run on its pull request. Where Docker is not available, start the service with `python app/transfer_app.py` and report that only CI built and started the container. Where Playwright cannot download its browsers, use an installed Chrome as README.md shows.

```bash
ruff format --check .
ruff check .
robocop format --check .
robocop check .
pytest
robot --outputdir test-results/robot tests/ui
```
