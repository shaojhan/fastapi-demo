import nox


@nox.session
def tests(session):
    session.install('pytest')
    session.run('pytest')


@nox.session
def lint(session):
    """Static lint with ruff (advisory)."""
    session.install('ruff')
    session.run('ruff', 'check', 'app', 'database')


@nox.session
def typecheck(session):
    """Static type check with mypy (advisory)."""
    session.install('mypy')
    session.run('mypy', 'app')


@nox.session
def security(session):
    """Security scan: bandit (code) + pip-audit (dependencies) (advisory)."""
    session.install('bandit', 'pip-audit')
    session.run('bandit', '-r', 'app', 'database')
    session.run('pip-audit')
