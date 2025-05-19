from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from . import models


async def get_url_by_short_code(db: AsyncSession, short_code: str) -> models.URLMap | None:
    """Busca um mapeamento de URL pelo código curto."""
    result = await db.execute(
        select(models.URLMap).filter(models.URLMap.short_code == short_code)
    )
    # first() retorna o primeiro resultado ou None se não houver nenhum
    return result.scalars().first()
