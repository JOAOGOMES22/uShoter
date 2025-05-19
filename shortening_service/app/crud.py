from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from . import models


async def get_url_by_short_code(db: AsyncSession, short_code: str) -> models.URLMap | None:
    """Busca um mapeamento de URL pelo código curto."""
    result = await db.execute(
        select(models.URLMap).filter(models.URLMap.short_code == short_code)
    )
    return result.scalars().first()


async def create_url_mapping(db: AsyncSession, url_create: models.URLCreate) -> models.URLMap:
    """Cria um novo mapeamento de URL no banco."""
    # Cria a instância do modelo SQLAlchemy
    db_url_map = models.URLMap(
        short_code=url_create.short_code,
        long_url=str(url_create.long_url)  # Armazena como string
    )
    db.add(db_url_map)
    try:
        await db.commit()
        await db.refresh(db_url_map)  # Atualiza o objeto com dados do DB (ex: ID)
        return db_url_map
    except IntegrityError:
        await db.rollback()
        # Isso pode acontecer em uma condição de corrida rara se generate_unique_short_code falhar
        raise HTTPException(status_code=409, detail="Short code already exists (collision)")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during URL creation: {e}")
