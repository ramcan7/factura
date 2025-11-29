# Usamos una imagen ligera de Python
FROM python:3.10-slim

# Establecemos el directorio de trabajo en la raíz del contenedor
WORKDIR /app

# Forzamos a Python a mostrar los logs inmediatamente
ENV PYTHONUNBUFFERED=1

# Copiamos requirements.txt desde la raíz (gracias al contexto del compose)
COPY requirements.txt .

# Instalamos dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos TODO el proyecto (carpeta backend, README, etc.)
COPY . .

# Exponemos el puerto
EXPOSE 8000

# --- EL CAMBIO IMPORTANTE ---
# Como main.py está dentro de la carpeta 'backend', usamos la notación de punto:
# "backend.main:app" significa: Carpeta backend -> archivo main.py -> objeto app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
