from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import google.generativeai as genai
import json

# 1. Configuración inicial
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

# --- BLOQUE DE VALIDACIÓN ---
if not api_key:
    print("❌ ERROR CRÍTICO: No se encontró la variable GEMINI_API_KEY.")
    # Esto detiene el programa inmediatamente para que no siga ejecutándose roto
    raise ValueError("La API Key no está configurada en el archivo .env")
else:
    # Muestra un mensaje de éxito y una vista segura (solo los primeros 4 caracteres)
    print(f"✅ Variable de entorno cargada correctamente. Key: {api_key[:4]}...******")

# Configuración de Gemini
genai.configure(api_key=api_key)

# Usamos el nombre limpio, sin "models/"
model = genai.GenerativeModel("gemini-2.5-flash")

# 2. Iniciamos la APP (API)
app = FastAPI()

# Definimos qué datos esperamos recibir (el texto de la factura)
class InvoiceRequest(BaseModel):
    texto_factura: str

# 3. Función mejorada para extraer JSON
def extract_invoice_data(text: str):
    prompt = f"""
    Eres un Agente Contable experto en facturación SUNAT. Tu única misión es extraer *solamente* la información necesaria para armar un borrador de factura o boleta, y devolverla estrictamente en el formato JSON.

    **REGLAS DE EXTRACCIÓN (MUY ESTRICTAS):**
    1. **No Inventar:** SOLO extrae los valores que están explícitamente en el "TEXTO DEL USUARIO". Si un dato requerido no se menciona (items, precios), no generes el JSON.
    2. **Validación Mínima:** Si el texto es ambiguo o faltan campos CRÍTICOS para los ítems (descripción, cantidad o precio unitario), genera un mensaje de error claro y NO DEVUELVAS EL JSON.
    3. **Valores por Defecto:**
        - Si no se especifica RUC, usa el placeholder '00000000000'.
        - Si no se especifica moneda, usa 'Soles'.
    4. **Respuesta Exclusiva:** Tu salida debe ser **SOLAMENTE** el objeto JSON estructurado que sigue el esquema. No añadas introducciones, explicaciones, markdown adicional ni texto fuera del JSON.
        
    El JSON debe tener esta estructura estricta:
    {{
        "emisor": "Nombre de la empresa o universidad",
        "ruc": "Número de RUC si existe",
        "fecha_emision": "YYYY-MM-DD",
        "cliente": "Nombre del cliente",
        "items": [
            {{ "descripcion": "Nombre del producto", "cantidad": 1, "precio_unitario": 0.0, "total": 0.0 }}
        ],
        "moneda": "Soles o Dolares",
        "total_pagar": 0.0
    }}

    Texto de la factura:
    {text}
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2, # Bajo para ser preciso
                "response_mime_type": "application/json" # ¡Truco clave! Fuerza la salida JSON
            }
        )
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e)}

# 4. El Endpoint (La ruta web)
@app.post("/procesar-factura")
def process_invoice(request: InvoiceRequest):
    print(f"Recibiendo datos: {request.texto_factura[:50]}...")
    resultado_json = extract_invoice_data(request.texto_factura)
    return resultado_json

# Bloque para correrlo localmente si ejecutas 'python main.py'
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)