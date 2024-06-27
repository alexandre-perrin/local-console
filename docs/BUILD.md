# Building the Local Console

## Basic setup

1. Create a Python 3.11+ virtual environment

```sh
$ python3.11 -m venv lcenv
```

2. Install the local console in editable mode, plus test dependencies

```sh
$ . lcenv/bin/activate # on Linux and OSX
# . .\lcenv\Scripts\Activate.ps1 on Windows PowerShell

(lcenv)$ pip install -e local-console/
...

(lcenv)$ pip install -r tests/requirements.txt
...
```

This editable installation uses the same configuration data as a normal end-user installation does (e.g. for settings such as `local-console config get`).

## Development habits

Before submitting a pull request, or a change to an existing one, please make sure to perform the following actions.

1. Run linting

```sh
(lcenv)$ pre-commit run --all-files
```

2. Run unit tests

```sh
(lcenv)$ pytest tests/
```

3. If you want to capture coverage data:

```sh
(lcenv)$ coverage run -m pytest tests -o junit_family=xunit1 --junitxml=xunit-result.xml
...
(lcenv)$ coverage xml
...
```
