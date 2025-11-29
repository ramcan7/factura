# Facturador (local)

Repositorio local para desarrollar y probar un frontend Streamlit que consume un backend FastAPI.

Resumen
- Frontend: `streamlit_app.py` — interfaz que permite enviar texto para extraer factura y enviar JSON para generar PDF.
- Backend: `backend/main.py` — expone dos endpoints principales:
  - `POST /procesar-factura` — acepta `{ "texto_factura": "..." }` y devuelve JSON estructurado.
  - `POST /generar-pdf` — acepta el JSON completo de la factura y devuelve bytes del PDF.

Requisitos
- Python 3.11/3.12/3.13 (según tu entorno virtual)
- Instalar dependencias (desde la raíz del repo o dentro de `backend/` si tienes archivo `requirements.txt`).

Instalación rápida (ejemplo macOS / zsh):
```bash
# desde la raíz del repo
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install -r requirements.txt || true
```

Ejecutar localmente

1) Levantar el backend (FastAPI + Uvicorn):
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

2) Levantar el frontend (Streamlit):
```bash
streamlit run streamlit_app.py
```

Por defecto la app usa `http://localhost:8000` como backend. Para cambiarlo sin editar código:

- localmente (temporal):
```bash
export BACKEND_URL="http://localhost:8000"
streamlit run streamlit_app.py
```

- en Streamlit Cloud / deploy: añadir `backend_url` en `st.secrets` o en la UI de deploy.

Probar los endpoints con `curl`

- `/procesar-factura` (ejemplo):
```bash
curl -sS -X POST http://localhost:8000/procesar-factura \
  -H "Content-Type: application/json" \
  -d '{"texto_factura": "Boleta de venta: Juan Perez, 1 Martillo a S/20.00"}'
```

- `/generar-pdf` (ejemplo payload):
```bash
curl -sS -X POST http://localhost:8000/generar-pdf \
  -H "Content-Type: application/json" \
  -d '
{
    "document_type": "Factura",
    "serie_correlativo": "F001-0000001",
    "emisor_nombre": "D&B COMBUSTIBLES DEL PERU S.A.C.",
    "emisor_ruc": "20521579782",
    "emisor_direccion": "CALLE LOS PRECIADOS N 156 INT 304, LIMA",
    "client": "Juan Perez",
    "client_address": "Dirección Desconocida - Lima",
    "ruc_simulado": "00000000000",
    "fecha_emision": "30/12/2024",
    "fecha_vencimiento": "30/12/2024",
    "forma_pago": "Contado",
    "moneda": "SOLES",
    "items": [
        {"descripcion": "Martillo","cantidad": 1.0,"unidad_medida": "UNI","precio_unitario": 20.0}
    ],
    "monto_letras": "VEINTE CON 00/100 SOLES"
}
' --output invoice.pdf
```

Este `curl` guarda la respuesta (bytes PDF) en `invoice.pdf`.

Exponer temporalmente backend con `ngrok` (para probar Streamlit desplegado):
```bash
# instalar ngrok si no lo tienes
ngrok http 8000
# Copia la URL https://xxxxxx.ngrok.io y configúrala en Streamlit (env o st.secrets)
export BACKEND_URL="https://xxxxxx.ngrok.io"
streamlit run streamlit_app.py
```

Troubleshooting
- Si Streamlit desplegado no llega al backend local, usa ngrok o despliega el backend en un host público.
- Si ves errores CORS, revisa `backend/main.py` y ajusta `allow_origins` a tu dominio en producción.
- Asegúrate de no exponer claves de API en el frontend.

¿Quieres que añada un pequeño script `test_endpoints.sh` que haga estos `curl` automáticamente? 
# 💬 Chatbot template

A simple Streamlit app that shows how to build a chatbot using OpenAI's GPT-3.5.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://chatbot-template.streamlit.app/)

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```
