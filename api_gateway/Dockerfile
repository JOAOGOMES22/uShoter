# Use uma imagem base oficial do Python
FROM python:3.10-slim

# Defina variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Defina o diretório de trabalho
WORKDIR /code

# Instale as dependências
COPY requirements.txt /code/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copie o código da aplicação
COPY ./app /code/app

# Expõe a porta que o Uvicorn usará
EXPOSE 8080

# CMD definido no docker-compose.yml
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]