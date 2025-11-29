from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
import google.generativeai as genai
import json
from fpdf import FPDF
from typing import List

# 1. Configuración inicial
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI(title="Facturador AI - Strict Mode")

# --- 2. MODELOS DE DATOS (Sin valores por defecto) ---
# Quitamos todos los 'defaults'. Si falta un dato, Pydantic o la IA deben gritar.

class Item(BaseModel):
    descripcion: str
    cantidad: float
    unidad_medida: str
    precio_unitario: float

class InvoiceData(BaseModel):
    document_type: str = Field(..., description="Factura o Boleta")
    serie_correlativo: str
    
    # Datos Emisor (Ahora la IA debe extraerlos, no están fijos)
    emisor_nombre: str
    emisor_ruc: str
    emisor_direccion: str 

    # Datos Cliente (OBLIGATORIOS)
    client: str
    client_address: str # Antes tenía default, ahora es obligatorio
    client_ruc_dni: str # Antes tenía default, ahora es obligatorio
    
    # Datos Factura
    fecha_emision: str
    fecha_vencimiento: str
    forma_pago: str
    moneda: str
    
    items: List[Item]
    monto_letras: str

class InvoiceRequest(BaseModel):
    texto_factura: str

# --- 3. EXTRACCIÓN CON IA (Modo Auditor Estricto) ---

def extract_invoice_data(text: str) -> dict:
    prompt = f"""
    Eres un AUDITOR de facturación electrónica SUNAT muy estricto.
    Tu trabajo es verificar si el texto del usuario tiene TODA la información necesaria para crear un documento legal válido.
    
    TEXTO DEL USUARIO: "{text}"

    **LISTA DE REQUISITOS OBLIGATORIOS (CHECKLIST):**
    1. **Datos del Emisor:** ¿Dice quién vende? (Nombre, RUC, Dirección).
    2. **Datos del Cliente:** ¿Dice quién compra? (Nombre, Dirección, RUC o DNI).
    3. **Datos de Venta:** Items, Cantidades, Precios, Moneda.
    4. **Fechas:** Fecha de emisión.
    
    **REGLA DE ORO:** NO INVENTES NADA. Si el usuario no menciona la dirección del cliente, NO pongas "Lima". Si no menciona el RUC, NO pongas "000".
    
    **RESPUESTA (JSON):**
    
    CASO 1: FALTA INFORMACIÓN
    Si falta CUALQUIERA de los datos obligatorios (especialmente Dirección del Cliente o RUC/DNI del Cliente, o Dirección del Emisor), devuelve:
    {{
        "error_message": "Falta información obligatoria: [Lista aquí exactamente qué campos faltan, por ejemplo: Dirección del Cliente, RUC del Emisor]"
    }}

    CASO 2: INFORMACIÓN COMPLETA
    Solo si tienes TODO, devuelve el JSON completo:
    {{
        "document_type": "Factura o Boleta",
        "serie_correlativo": "F001-00001 (Genera uno si no hay)",
        "emisor_nombre": "Extraído del texto",
        "emisor_ruc": "Extraído del texto",
        "emisor_direccion": "Extraído del texto",
        "client": "Nombre Cliente",
        "client_address": "Dirección Cliente",
        "client_ruc_dni": "RUC o DNI Cliente",
        "fecha_emision": "DD/MM/YYYY",
        "fecha_vencimiento": "DD/MM/YYYY",
        "forma_pago": "Contado o Crédito",
        "moneda": "SOLES o DOLARES",
        "items": [
            {{ "descripcion": "Prod", "cantidad": 1.0, "unidad_medida": "UNI/GLN", "precio_unitario": 0.0 }}
        ],
        "monto_letras": "CALCULA EL TEXTO (Ej: VEINTE CON 00/100 SOLES)"
    }}
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        return {"error_message": f"Error procesando solicitud: {str(e)}"}

# --- 4. GENERACIÓN PDF (Adaptada para datos dinámicos) ---

class PDFGenerator(FPDF):
    def __init__(self, invoice_data: InvoiceData):
        super().__init__()
        self.data = invoice_data # Guardamos los datos para usarlos en header/footer

    def header(self):
        # Header Dinámico (Usa los datos del Emisor extraídos)
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 51, 153)
        self.cell(100, 10, self.data.emisor_nombre[:35], 0, 0, 'L') # Nombre Emisor
        
        # Cuadro RUC
        self.set_text_color(0)
        self.set_font('Arial', 'B', 10)
        x_ruc = 130
        y_ruc = 10
        self.set_xy(x_ruc, y_ruc)
        self.cell(70, 25, '', 1)
        self.set_xy(x_ruc, y_ruc + 5)
        self.cell(70, 5, f"{self.data.document_type.upper()} ELECTRÓNICA", 0, 1, 'C')
        self.cell(70, 5, f"RUC: {self.data.emisor_ruc}", 0, 1, 'C', x=x_ruc) # RUC Emisor
        self.cell(70, 5, self.data.serie_correlativo, 0, 1, 'C', x=x_ruc)
        
        self.set_xy(10, 20)
        self.set_font('Arial', '', 8)
        self.cell(100, 5, self.data.emisor_direccion[:60], 0, 1) # Dirección Emisor
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def create_invoice_pdf(data: InvoiceData) -> bytes:
    pdf = PDFGenerator(data) # Pasamos data al constructor
    pdf.add_page()
    
    # --- Datos Cliente ---
    pdf.set_font("Arial", "", 9)
    pdf.rect(10, 45, 190, 20)
    pdf.set_xy(12, 47)
    
    pdf.cell(20, 5, "Cliente:", 0, 0)
    pdf.cell(100, 5, data.client, 0, 1)
    
    pdf.set_x(12)
    pdf.cell(20, 5, "Dirección:", 0, 0)
    pdf.cell(100, 5, data.client_address, 0, 1) # Ahora esto vendrá de la IA, no default
    
    pdf.set_x(12)
    pdf.cell(20, 5, "RUC/DNI:", 0, 0)
    pdf.cell(50, 5, data.client_ruc_dni, 0, 0)
    pdf.cell(20, 5, "Moneda:", 0, 0)
    pdf.cell(30, 5, data.moneda, 0, 1)
    
    pdf.ln(10)
    
    # --- Items ---
    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(20, 6, "CANT", 1, 0, 'C', fill=True)
    pdf.cell(100, 6, "DESCRIPCION", 1, 0, 'C', fill=True)
    pdf.cell(20, 6, "UND", 1, 0, 'C', fill=True)
    pdf.cell(25, 6, "P.UNIT", 1, 0, 'C', fill=True)
    pdf.cell(25, 6, "TOTAL", 1, 1, 'C', fill=True)
    
    pdf.set_font("Arial", "", 9)
    subtotal = 0.0
    for item in data.items:
        total = item.cantidad * item.precio_unitario
        subtotal += total
        pdf.cell(20, 6, str(item.cantidad), 1, 0, 'C')
        pdf.cell(100, 6, item.descripcion, 1, 0, 'L')
        pdf.cell(20, 6, item.unidad_medida, 1, 0, 'C')
        pdf.cell(25, 6, f"{item.precio_unitario:.2f}", 1, 0, 'R')
        pdf.cell(25, 6, f"{total:.2f}", 1, 1, 'R')
        
    # --- Totales ---
    pdf.ln(5)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 5, f"SON: {data.monto_letras}", 0, 1)
    
    igv = subtotal * 0.18
    total_final = subtotal + igv
    
    pdf.set_x(130)
    pdf.cell(30, 6, "Subtotal", 1, 0)
    pdf.cell(30, 6, f"{subtotal:.2f}", 1, 1, 'R')
    
    pdf.set_x(130)
    pdf.cell(30, 6, "IGV 18%", 1, 0)
    pdf.cell(30, 6, f"{igv:.2f}", 1, 1, 'R')
    
    pdf.set_x(130)
    pdf.cell(30, 6, "TOTAL", 1, 0)
    pdf.cell(30, 6, f"{total_final:.2f}", 1, 1, 'R')

    return bytes(pdf.output())

# --- 5. ENDPOINTS ---

@app.post("/procesar-factura", response_model=InvoiceData)
def process_invoice(request: InvoiceRequest):
    print(f"Recibiendo: {request.texto_factura}")
    raw_data = extract_invoice_data(request.texto_factura)
    
    # DETECCIÓN DE ERROR
    if "error_message" in raw_data:
        print(f"❌ Validación fallida: {raw_data['error_message']}")
        raise HTTPException(status_code=400, detail=raw_data['error_message'])
    
    return InvoiceData(**raw_data)

@app.post("/generar-pdf")
def generate_pdf_endpoint(invoice_data: InvoiceData):
    try:
        pdf_bytes = create_invoice_pdf(invoice_data)
        filename = f"{invoice_data.document_type}_{invoice_data.client_ruc_dni}.pdf"
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error PDF: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)