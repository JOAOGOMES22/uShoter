import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import asyncio  # Adicionar
import random  # Adicionar
import sys

# Removi os prints de debug do database.py, presumindo que não são mais necessários
from . import crud, models, database # Remover , utils


# Context Manager para ciclo de vida da aplicação FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- ADICIONAR SLEEP ALEATÓRIO ---
    startup_delay = random.uniform(0.1, 1.5)  # Espera entre 0.1 e 1.5 segundos
    print(f"{app.title}: Waiting {startup_delay:.2f}s before DB init...")
    await asyncio.sleep(startup_delay)
    # --- FIM DO SLEEP ---

    print(f"{app.title}: Initializing database...")
    try:
        await database.init_db()
        print(f"{app.title}: Database initialized.")
    except Exception as e:
        # Logar o erro se a inicialização falhar, mas tentar continuar se possível
        # Ou relançar para parar a aplicação: raise e
        print(f"ERROR during {app.title} DB initialization: {e}", file=sys.stderr)
        # Dependendo da criticidade, você pode querer parar a aplicação aqui
        # raise e

    yield
    # Código a ser executado APÓS a aplicação finalizar (shutdown)
    print(f"{app.title}: Closing down...")


app = FastAPI(
    title="µShort - Redirection Service",
    description="Serviço responsável por buscar a URL original dado um código curto.",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/lookup/{short_code}", response_model=models.OriginalURL)
async def get_long_url(
        short_code: str,
        db: AsyncSession = Depends(database.get_db)
):
    """
    Busca a URL longa correspondente ao short_code fornecido.
    Retorna a URL original ou 404 se não encontrada.
    """
    print(f"Redirection Service looking up: {short_code}")  # Log
    db_url_map = await crud.get_url_by_short_code(db, short_code)

    if db_url_map is None:
        print(f"Redirection Service: Code {short_code} not found.")  # Log
        raise HTTPException(status_code=404, detail="Short code not found")

    print(f"Redirection Service found: {short_code} -> {db_url_map.long_url}")  # Log
    return models.OriginalURL(long_url=db_url_map.long_url)


@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok"}
