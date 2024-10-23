"""
To manage the database, and it's sessions
"""

import functools
import os
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.exc import DisconnectionError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import scoped_session, sessionmaker

from app.core import settings

__session = {}
__engine = {}


def get_db_engine(
    database=None,
    pool_size=settings.DATABASE_POOL_SIZE,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
):
    if not database:
        database = "local"
    global __engine
    if not __engine.get(database):
        """Returns the engine, Session, Base and with_session decorator
        for the given db configuration.
        """

        conn_string = settings.DATABASE_URI
        __engine[database] = create_engine(
            conn_string,
            pool_size=pool_size,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,
            # connect_args={
            #     "connect_timeout": 10,
            #     "keepalives": 1,
            #     "keepalives_idle": 600,
            #     "keepalives_interval": 30,
            #     "keepalives_count": 60,
            # },
        )

        """This is to ensure pooled connections are not used in multi-processing.
           Primarily to ensure forked celery worker does not reuse the same connection.

           See https://docs.sqlalchemy.org/en/13/core/pooling.html#using-connection-pools-with-multiprocessing
           for more details.
        """

        @event.listens_for(__engine[database], "connect")
        def connect(dbapi_connection, connection_record):
            connection_record.info["pid"] = os.getpid()

            if conn_string.startswith("sqlite"):
                # Sqlite DB requires foreign keys to be turned on manually
                # to ensure on delete cascade works
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        @event.listens_for(__engine[database], "checkout")
        def checkout(dbapi_connection, connection_record, connection_proxy):
            pid = os.getpid()
            if connection_record.info["pid"] != pid:
                connection_record.connection = connection_proxy.connection = None
                raise DisconnectionError(
                    "Connection record belongs to pid %s, "
                    "attempting to check out in pid %s"
                    % (connection_record.info["pid"], pid)
                )

        if conn_string.startswith("mysql"):
            __engine[database].execute("SET SESSION sql_mode='TRADITIONAL'")

    return __engine.get(database)


@as_declarative()
class Base:
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def validate(session):
    try:
        _ = session.connection()
        return True
    except Exception:
        return False


def get_session(scopefunc=None, database: str = None):
    """Create a global bound scoped_session

    Returns:
        [type] -- [description]
    """
    if not database:
        database = "local"
    global __session
    if session := __session.get(database):
        if validate(session):
            session.expire_on_commit = False
            return session
    db_session = scoped_session(
        sessionmaker(bind=get_db_engine(database=database), expire_on_commit=False),
        scopefunc=scopefunc,
    )
    db_session.expire_on_commit = False
    __session[database] = db_session
    return db_session


def with_session(database=None, retry_count=3):
    """Decorator for handling sessions."""

    def wrapper(fn):
        @functools.wraps(fn)
        def func(*args, **kwargs):
            session = None
            # If there's no session, create a new one. We will
            # automatically close this after the function is called.
            for _ in range(retry_count):
                if not kwargs.get("session"):
                    # By default we try to use global flask db session first
                    session = get_session(database=database)()
                    kwargs["session"] = session

                if session is None:
                    return fn(*args, **kwargs)
                try:
                    result = fn(*args, **kwargs)
                    # session.commit()
                # except OperationalError as e:
                #     continue
                except SQLAlchemyError as e:
                    session.rollback()
                    # TODO: Log the sqlalchemy error?
                    import traceback

                    # LOG.error(traceback.format_exc())
                    raise e
                finally:
                    # Since we created the session, close it.
                    # session.close()
                    # get_session().remove()
                    session.close()
                return result

            session.rollback()
            # raise OperationalError(f"Retry count exceeded. There some issue while connecting to the '{database}' database.")

        return func

    return wrapper


@contextmanager
def DBSession(database=None):
    # Otherwise create the session as normal
    # and teardown at the end
    session = get_session(database=database)()
    try:
        yield session
    except SQLAlchemyError as e:
        session.rollback()
        # TODO: Log the sqlalchemy error?
        import traceback

        # LOG.error(traceback.format_exc())
        raise e
    finally:
        get_session().remove()
