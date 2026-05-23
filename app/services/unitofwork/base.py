from sqlalchemy.orm import Session, sessionmaker

from app.db import engine


class BaseUnitOfWork:
    """Base Unit of Work for write operations.

    Transaction semantics: callers must commit explicitly via ``commit()``.
    ``__exit__`` only rolls back — which is a no-op once ``commit()`` has run,
    and discards any uncommitted work otherwise. This keeps a single, explicit
    commit boundary and avoids the previous double-commit (explicit commit plus
    an auto-commit on context exit).

    Subclasses implement :meth:`_setup_repositories` to attach repositories to
    the active session.
    """

    expire_on_commit: bool = False

    def __init__(self):
        self.session_factory = sessionmaker(engine, expire_on_commit=self.expire_on_commit)

    def __enter__(self):
        self.session = self.session_factory()
        self._setup_repositories(self.session)
        return self

    def _setup_repositories(self, session: Session) -> None:
        raise NotImplementedError

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            # Roll back anything not explicitly committed (no-op after commit()).
            self.session.rollback()
        finally:
            self.session.close()

    def commit(self):
        """Commit the current transaction."""
        self.session.commit()

    def rollback(self):
        """Rollback the current transaction."""
        self.session.rollback()


class BaseQueryUnitOfWork:
    """Base Unit of Work for read-only queries: never commits, just closes."""

    expire_on_commit: bool = False

    def __init__(self):
        self.session_factory = sessionmaker(engine, expire_on_commit=self.expire_on_commit)

    def __enter__(self):
        self.session = self.session_factory()
        self._setup_repositories(self.session)
        return self

    def _setup_repositories(self, session: Session) -> None:
        raise NotImplementedError

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
