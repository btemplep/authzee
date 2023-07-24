
import sys

import nox

nox.options.sessions = [
    "build-docs",
    "unit-tests-versions"
]

@nox.session(name="build-docs")
def build_docs(session: nox.Session):
    """Build the documentation.
    """
    if "--no-venv" not in sys.argv:
        dev_venv_setup(session=session)

    session.run("rm", "-rf", "./docs/_build/", 
        external=True
    )
    session.run("sphinx-build", "-b", "html", "./docs", "./docs/_build/html/")


@nox.session(
    name="docs-server",
    venv_backend="none"
)
def docs_server(session: nox.Session):
    """Run a local server for the docs at http://localhost:7999/index.html
    """
    session.run("python", "-m", "http.server", "-d", "docs/_build/html/", "7999")


@nox.session(name="publish-package")
def publish(session: nox.Session):
    """Build a new src and wheel and publish to PYPI
    """
    dev_venv_setup(session=session)
    session.run(
        "rm", "-rf", "./build/", "./dist/",
        external=True
    )
    session.run("python", "-m", "build", "--sdist", "--wheel")
    session.run("twine", "upload", "dist/*", "--repository", "authzee")


@nox.session(
    name="unit-tests",
    python=False
)
def unit_tests(session: nox.Session):
    """Run tests with current python version and generate html coverage report.
    """
    session.run("coverage", "erase")
    session.run("pytest", "-vvv", "--cov=src/authzee", "--cov-report", "html", "tests/unit")


@nox.session(
    name="unit-tests-versions",
    python=[
        "3.8",
        "3.9",
        "3.10",
        "3.11"
    ]
)
def unit_tests_versions(session: nox.Session):
    """Run tests with all specified python version and generate missing coverage report in terminal.
    """
    dev_venv_setup(session=session)
    session.run("coverage", "erase")
    session.run("pytest", "-vvv", "--cov=src/authzee", "--cov-report", "term-missing", "tests/unit")


def dev_venv_setup(session: nox.Session):
    session.install("-U", "pip", "build")
    session.install("-e", ".[dev,all]")

