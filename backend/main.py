from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
import google.generativeai as genai
import json
import re  # <--- Agregado para limpiar el JSON
from fpdf import FPDF
from typing import List

# 1. Configuración inicial
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("⚠️ ADVERTENCIA: No se detectó GEMINI_API_KEY")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI(title="Facturador AI - Robust Mode")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. MODELOS DE DATOS (Con Defaults para que NO falle) ---

class Item(BaseModel):
    descripcion: str
    cantidad: float
    # Si la IA no detecta unidad, usará "UNI" en vez de romper
    unidad_medida: str = Field(default="UNI") 
    precio_unitario: float

class InvoiceData(BaseModel):
    # Valores por defecto para evitar errores 422 de validación
    document_type: str = Field(default="Boleta de Venta")
    serie_correlativo: str = Field(default="B001-00001")
    
    # Datos Emisor (Si faltan, se ponen genéricos)
    emisor_nombre: str = Field(default="EMISOR POR DEFECTO")
    emisor_ruc: str = Field(default="00000000000")
    emisor_direccion: str = Field(default="Dirección del Emisor")

    # Datos Cliente
    client: str = Field(..., description="El nombre del cliente SI es obligatorio")
    client_address: str = Field(default="Dirección no especificada")
    client_ruc_dni: str = Field(default="00000000")
    
    # Datos Factura
    fecha_emision: str = Field(default="HOY")
    fecha_vencimiento: str = Field(default="HOY")
    forma_pago: str = Field(default="Contado")
    moneda: str = Field(default="SOLES")
    
    items: List[Item]
    monto_letras: str = Field(default="---")

class InvoiceRequest(BaseModel):
    texto_factura: str

# --- 3. EXTRACCIÓN CON IA (Lógica Permisiva) ---

def clean_json_text(text: str) -> str:
    """Limpia los bloques de código markdown que a veces pone Gemini"""
    cleaned = re.sub(r"```json\s*", "", text) # Quita ```json
    cleaned = re.sub(r"```", "", cleaned)      # Quita ``` al final
    return cleaned.strip()

def extract_invoice_data(text: str) -> dict:
    prompt = f"""
    Actúa como un asistente de facturación INTELIGENTE y PROACTIVO.
    Tu objetivo es generar un JSON válido SIEMPRE, completando la información faltante con datos lógicos o valores por defecto.

    TEXTO DEL USUARIO: "{text}"

    **REGLAS DE INFERENCIA (NO DEVUELVAS ERROR, RESUELVE):**
    1. **Cliente:** Extrae el nombre. Si no hay DNI/RUC, inventa uno genérico o pon "00000000". Si no hay dirección, pon "Ciudad".
    2. **Emisor:** Si el texto no dice quién vende, usa "Mi Empresa S.A.C." con RUC "20000000001".
    3. **Items:** Si falta la unidad de medida, asume "UNI".
    4. **Fechas/Pagos:** Si faltan, usa fecha de hoy y pago "Contado".
    5. **Moneda:** Si no se dice, asume "SOLES".
    6. **Monto en letras:** CALCULA el total y escríbelo.

    **Devuelve SOLAMENTE el JSON con esta estructura:**
    {{
        "document_type": "Factura o Boleta",
        "serie_correlativo": "F001-00001",
        "emisor_nombre": "Texto...",
        "emisor_ruc": "Texto...",
        "emisor_direccion": "Texto...",
        "client": "Texto...",
        "client_address": "Texto...",
        "client_ruc_dni": "Texto...",
        "fecha_emision": "DD/MM/YYYY",
        "fecha_vencimiento": "DD/MM/YYYY",
        "forma_pago": "Contado",
        "moneda": "SOLES",
        "items": [
            {{ "descripcion": "Prod", "cantidad": 1.0, "unidad_medida": "UNI", "precio_unitario": 0.0 }}
        ],
        "monto_letras": "SON: ..."
    }}
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        # Limpiamos la respuesta antes de parsear
        clean_text = clean_json_text(response.text)
        return json.loads(clean_text)
    except Exception as e:
        # En el peor de los casos, devolvemos un error controlado
        return {"error_message": f"Error procesando IA: {str(e)}"}

# --- 4. GENERACIÓN PDF (INTACTO - SOLO CON HELPER DE TILDES) ---

class PDFGenerator(FPDF):
    def __init__(self, invoice_data: InvoiceData):
        super().__init__()
        self.data = invoice_data 

    def header(self):
        def txt(texto): return str(texto).encode('latin-1', 'replace').decode('latin-1')

        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 51, 153)
        self.cell(100, 10, txt(self.data.emisor_nombre[:35]), 0, 0, 'L')
        
        self.set_text_color(0)
        self.set_font('Arial', 'B', 10)
        
        x_ruc = 120
        y_ruc = 10
        self.rect(x_ruc, y_ruc, 80, 25)
        self.set_xy(x_ruc, y_ruc + 4)
        self.cell(80, 5, txt(f"{self.data.document_type.upper()}"), 0, 1, 'C')
        self.set_xy(x_ruc, y_ruc + 11)
        self.cell(80, 5, txt(f"RUC: {self.data.emisor_ruc}"), 0, 1, 'C')
        self.set_xy(x_ruc, y_ruc + 18)
        self.cell(80, 5, txt(self.data.serie_correlativo), 0, 1, 'C')
        
        self.set_xy(10, 20)
        self.set_font('Arial', '', 8)
        self.cell(100, 5, txt(self.data.emisor_direccion[:60]), 0, 1)
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def create_invoice_pdf(data: InvoiceData) -> bytes:
    def txt(texto): return str(texto).encode('latin-1', 'replace').decode('latin-1')

    pdf = PDFGenerator(data)
    pdf.add_page()
    
    pdf.set_font("Arial", "", 9)
    pdf.rect(10, 45, 190, 25)
    pdf.set_xy(12, 47)
    
    pdf.set_font("Arial", "B", 9)
    pdf.cell(20, 5, "Cliente:", 0, 0)
    pdf.set_font("Arial", "", 9)
    pdf.cell(100, 5, txt(data.client), 0, 1)
    
    pdf.set_x(12)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(20, 5, txt("Dirección:"), 0, 0)
    pdf.set_font("Arial", "", 9)
    pdf.cell(100, 5, txt(data.client_address), 0, 1)
    
    pdf.set_x(12)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(20, 5, "RUC/DNI:", 0, 0)
    pdf.set_font("Arial", "", 9)
    pdf.cell(50, 5, txt(data.client_ruc_dni), 0, 0)
    
    pdf.set_font("Arial", "B", 9)
    pdf.cell(20, 5, "Moneda:", 0, 0)
    pdf.set_font("Arial", "", 9)
    pdf.cell(30, 5, txt(data.moneda), 0, 1)

    pdf.set_x(12)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(20, 5, "Fecha:", 0, 0)
    pdf.set_font("Arial", "", 9)
    pdf.cell(50, 5, txt(data.fecha_emision), 0, 1)
    
    pdf.ln(10)
    
    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(20, 7, "CANT", 1, 0, 'C', fill=True)
    pdf.cell(100, 7, txt("DESCRIPCIÓN"), 1, 0, 'C', fill=True)
    pdf.cell(20, 7, "UND", 1, 0, 'C', fill=True)
    pdf.cell(25, 7, "P.UNIT", 1, 0, 'C', fill=True)
    pdf.cell(25, 7, "TOTAL", 1, 1, 'C', fill=True)
    
    pdf.set_font("Arial", "", 9)
    subtotal = 0.0
    
    for item in data.items:
        total = item.cantidad * item.precio_unitario
        subtotal += total
        pdf.cell(20, 6, str(item.cantidad), 1, 0, 'C')
        pdf.cell(100, 6, txt(item.descripcion), 1, 0, 'L')
        pdf.cell(20, 6, txt(item.unidad_medida), 1, 0, 'C')
        pdf.cell(25, 6, f"{item.precio_unitario:.2f}", 1, 0, 'R')
        pdf.cell(25, 6, f"{total:.2f}", 1, 1, 'R')
        
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 5, txt(f"SON: {data.monto_letras}"), 0, 1)
    
    igv = subtotal * 0.18
    total_final = subtotal + igv
    
    x_totales = 135
    pdf.set_x(x_totales)
    pdf.cell(30, 6, "Subtotal", 1, 0); pdf.cell(30, 6, f"{subtotal:.2f}", 1, 1, 'R')
    pdf.set_x(x_totales)
    pdf.cell(30, 6, "IGV 18%", 1, 0); pdf.cell(30, 6, f"{igv:.2f}", 1, 1, 'R')
    pdf.set_x(x_totales)
    pdf.cell(30, 6, "TOTAL", 1, 0); pdf.cell(30, 6, f"{total_final:.2f}", 1, 1, 'R')

    return bytes(pdf.output())

# --- 5. ENDPOINTS ---

@app.post("/procesar-factura", response_model=InvoiceData)
def process_invoice(request: InvoiceRequest):
    print(f"📥 Procesando: {request.texto_factura[:40]}...")
    
    raw_data = extract_invoice_data(request.texto_factura)
    
    if "error_message" in raw_data:
        # Solo lanza error si la IA explotó de verdad
        raise HTTPException(status_code=400, detail=raw_data['error_message'])
    
    try:
        # Aquí Pydantic usará los defaults si falta algo
        return InvoiceData(**raw_data)
    except Exception as e:
        print(f"❌ Error Data: {e}")
        # Reporte detallado solo si falla Pydantic (muy raro ahora con los defaults)
        raise HTTPException(status_code=422, detail=f"Error procesando datos: {str(e)}")

@app.post("/generar-pdf")
def generate_pdf_endpoint(invoice_data: InvoiceData):
    try:
        pdf_bytes = create_invoice_pdf(invoice_data)
        filename = f"Doc_{invoice_data.client_ruc_dni}.pdf"
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error PDF: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)