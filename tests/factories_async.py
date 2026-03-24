import factory
from sqlalchemy.ext.asyncio import AsyncSession


class AsyncSQLAlchemyFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Async-compatible SQLAlchemy factory."""

    class Meta:
        abstract = True

    @classmethod
    async def _create(cls, model_class, *args, **kwargs):
        """Override factory_boy's sync _create to support async sessions."""
        session: AsyncSession = cls._meta.sqlalchemy_session

        obj = model_class(*args, **kwargs)
        session.add(obj)
        await session.flush()   # async flush
        return obj
