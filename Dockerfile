# Usa a imagem oficial do Playwright com Python pré-instalado
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos de dependências primeiro (otimiza o cache do Docker)
COPY requirements.txt .

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Instala apenas o navegador Firefox
RUN playwright install firefox

# Copia o restante do código para o container
COPY . .

# Expõe a porta que o FastAPI usará
EXPOSE 8000

# Comando para iniciar a API com Uvicorn
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]