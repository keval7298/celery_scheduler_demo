from datetime import date, datetime
from enum import Enum
from typing import List

from sqlalchemy.orm import validates

from app.core.database import with_session

_epoch = datetime.utcfromtimestamp(0)


def DATETIME_TO_UTC(dt: datetime) -> int:
    """Return a string representation of date
    Note: In our models we normally define now
    as datetime.datetime.utcnow however our db
    doesn't seem to be storing the ms, therefore
    we don't have ms resolution and thus we
    return the result in seconds instead of ms
    at least for the time being.
    """
    return int((dt - _epoch).total_seconds()) if dt else None


def DATE_TO_UTC(dt: date) -> int:
    """Return a string representation of date
    Note: In our models we normally define now
    as datetime.datetime.utcnow however our db
    doesn't seem to be storing the ms, therefore
    we don't have ms resolution and thus we
    return the result in seconds instead of ms
    at least for the time being.
    """
    return (
        int((datetime.combine(dt, datetime.min.time()) - _epoch).total_seconds())
        if dt
        else None
    )


def serialize_value(value):
    if value:
        # TODO: since jsonsify also converts
        # Decide on which conversion is required
        if isinstance(value, datetime):
            return DATETIME_TO_UTC(value)
        elif isinstance(value, date):
            return DATE_TO_UTC(value)
        elif isinstance(value, Enum):
            return value.value
        elif isinstance(value, dict):
            return {k: serialize_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return value.__class__(map(serialize_value, value))
        elif hasattr(value, "to_dict"):
            return value.to_dict()
    return value


def update_model_fields(
    model, skip_if_value_none=False, field_names: List[str] = None, **fields
) -> bool:
    """Update sqlalchemy model's fields while does some boilerplatey functionalities

    Arguments:
        model {sqlalchemy model} -- The model we update, represents a row in the database

    Keyword Arguments:
        skip_if_value_none {bool} -- If true, skip updating all values that are None (default: {False})
        field_names {List[str]} -- If not none, only update fields in the list (default: {None})

    Returns:
        bool -- Whether or not the model got updated
    """
    model_updated = False

    if field_names is None:
        field_names = fields.keys()

    for key in field_names:
        if key not in fields:
            continue

        value = fields[key]
        if skip_if_value_none and value is None:
            continue

        if getattr(model, key) != value:
            setattr(model, key, value)
            model_updated = True

    return model_updated


class SerializeMixin:
    def to_dict(self, skip_columns=[], extra_fields=[]):
        result = {
            column.name: serialize_value(getattr(self, column.name))
            for column in self.__table__.columns
            if column.name not in skip_columns
        }
        for field in extra_fields:
            result[field] = serialize_value(getattr(self, field))
        return result

    def __repr__(self):
        _id = getattr(self, "id", "")
        name = getattr(self, "name", "")
        if _id and name:
            return '{}(id={}, name="{}")'.format(self.__class__.__name__, _id, name)
        if _id:
            return str(_id)
        return name


class CRUDMixin(SerializeMixin):
    @classmethod
    def _get_query(cls, session=None, **kwargs):
        query = session.query(cls)
        if len(kwargs) > 0:
            query = query.filter_by(**kwargs)
        return query

    @classmethod
    @with_session()
    def get(cls, session=None, **kwargs):
        query = cls._get_query(session=session, **kwargs)
        return query.first()

    @classmethod
    @with_session()
    def get_all(
        cls, session=None, limit=None, offset=None, order_by=None, desc=False, **kwargs
    ):
        query = cls._get_query(session=session, **kwargs)
        if order_by is not None:
            col = getattr(cls, order_by)
            if desc:
                col = col.desc()
            query = query.order_by(col)
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        return query.all()

    @classmethod
    @with_session()
    def create(
        cls,
        fields={},
        commit=True,
        session=None,
    ):
        item = cls()
        for key, value in fields.items():
            setattr(item, key, value)
        session.add(item)
        if commit:
            session.commit()
        else:
            session.flush()
        session.refresh(item)
        return item

    @classmethod
    @with_session()
    def update(
        cls,
        id,
        fields={},
        field_names=None,
        skip_if_value_none=False,
        update_callback=None,
        commit=True,
        session=None,
    ):
        item = cls.get(id=id, session=session)
        if not item:
            return

        updated = update_model_fields(
            item,
            skip_if_value_none=skip_if_value_none,
            field_names=field_names,
            **fields,
        )

        if updated:
            if hasattr(item, "updated_at"):
                setattr(item, "updated_at", datetime.now())

            if commit:
                session.commit()
            else:
                session.flush()
            session.refresh(item)

            if update_callback is not None:
                update_callback(item)
        return item

    @classmethod
    @with_session()
    def delete(cls, id, commit=True, session=None):
        item = cls.get(id=id, session=session)
        if not item:
            return

        session.delete(item)
        if commit:
            session.commit()


# from https://stackoverflow.com/questions/32364499/truncating-too-long-varchar-when-inserting-to-mysql-via-sqlalchemy
def TruncateString(*fields):
    class TruncateStringMixin:
        @validates(*fields)
        def validate_string_field_length(self, key, value):
            max_len = getattr(self.__class__, key).prop.columns[0].type.length
            if value and len(value) > max_len:
                return value[:max_len]
            return value

    return TruncateStringMixin


def update_model_fields(
    model, skip_if_value_none=False, field_names: List[str] = None, **fields
) -> bool:
    """Update sqlalchemy model's fields while does some boilerplatey functionalities

    Arguments:
        model {sqlalchemy model} -- The model we update, represents a row in the database

    Keyword Arguments:
        skip_if_value_none {bool} -- If true, skip updating all values that are None (default: {False})
        field_names {List[str]} -- If not none, only update fields in the list (default: {None})

    Returns:
        bool -- Whether or not the model got updated
    """
    model_updated = False

    if field_names is None:
        field_names = fields.keys()

    for key in field_names:
        if key not in fields:
            continue

        value = fields[key]
        if skip_if_value_none and value is None:
            continue

        if getattr(model, key) != value:
            setattr(model, key, value)
            model_updated = True

    return model_updated
