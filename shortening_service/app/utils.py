import secrets
import string
from sqlalchemy.ext.asyncio import AsyncSession
from . import crud

# Caracteres possíveis para o código curto (alfanumérico seguro para URL)
# Exclui caracteres que podem ser confundidos (O, 0, I, l) - opcional
# ALPHABET = string.ascii_letters + string.digits
ALPHABET = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6  # Comprimento do código curto
MAX_RETRIES = 10  # Tentativas máximas para evitar colisão


async def generate_short_code() -> str:
    """Gera um código curto aleatório."""
    return ''.join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


async def generate_unique_short_code(db: AsyncSession) -> str:
    """Gera um código curto e garante que ele seja único no banco."""
    for _ in range(MAX_RETRIES):
        code = await generate_short_code()
        existing = await crud.get_url_by_short_code(db, code)
        if not existing:
            return code
    # Se esgotar as tentativas (extremamente improvável com um bom tamanho/alfabeto)
    raise Exception("Could not generate a unique short code after multiple retries.")
