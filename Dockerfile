# Usa una immagine Python minimal
FROM python:3.11-slim

# Imposta la working directory
WORKDIR /app

# Copia i requisiti e installali
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto del codice
COPY . .

# Comando di default se l'utente non ne specifica uno
CMD ["python", "src/main.py", "--help"]
