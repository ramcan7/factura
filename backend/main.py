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
if not api_key:
    # Fallback para pruebas locales si no hay env
    print("⚠️ ADVERTENCIA: No se detectó GEMINI_API_KEY")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI(title="Facturador AI - Final Stable")

# --- 2. MODELOS DE DATOS (Sincronizados al 100%) ---

class Item(BaseModel):
    descripcion: str
    cantidad: float
    unidad_medida: str
    precio_unitario: float

class InvoiceData(BaseModel):
    document_type: str = Field(..., description="Factura o Boleta de Venta")
    serie_correlativo: str
    
    # Datos Emisor
    emisor_nombre: str
    emisor_ruc: str
    emisor_direccion: str 

    # Datos Cliente
    client: str
    client_address: str 
    client_ruc_dni: str 
    
    # Datos Factura
    fecha_emision: str
    fecha_vencimiento: str
    forma_pago: str
    moneda: str
    
    items: List[Item]
    monto_letras: str

class InvoiceRequest(BaseModel):
    texto_factura: str

# --- 3. EXTRACCIÓN CON IA (Prompt Refinado) ---

def extract_invoice_data(text: str) -> dict:
    prompt = f"""
    Eres un AUDITOR de facturación SUNAT. Extrae datos exactos del texto.
    
    TEXTO: "{text}"

    **REGLAS:**
    1. Si falta Dirección del Cliente, RUC/DNI del Cliente o Dirección del Emisor, DEVUELVE ERROR.
    2. Document Type debe ser "Factura Electrónica" o "Boleta de Venta Electrónica".
    
    **RESPUESTA JSON (Si falta info, usa la clave "error_message"):**
    {{
        "document_type": "Boleta de Venta",
        "serie_correlativo": "B001-00001",
        "emisor_nombre": "Nombre Emisor",
        "emisor_ruc": "RUC Emisor",
        "emisor_direccion": "Dirección Emisor",
        "client": "Nombre Cliente",
        "client_address": "Dirección Cliente",
        "client_ruc_dni": "DNI/RUC Cliente",
        "fecha_emision": "DD/MM/YYYY",
        "fecha_vencimiento": "DD/MM/YYYY",
        "forma_pago": "Contado",
        "moneda": "SOLES",
        "items": [
            {{ "descripcion": "Item", "cantidad": 1.0, "unidad_medida": "UNI", "precio_unitario": 10.0 }}
        ],
        "monto_letras": "DIEZ CON 00/100 SOLES"
    }}
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        return {"error_message": f"Error IA: {str(e)}"}

# --- 4. GENERACIÓN PDF (Corrección de Bug 'x=') ---

class PDFGenerator(FPDF):
    def __init__(self, invoice_data: InvoiceData):
        super().__init__()
        self.data = invoice_data 

    def header(self):
        # Función auxiliar para decodificar caracteres latinos (tildes)
        def txt(texto):
            return str(texto).encode('latin-1', 'replace').decode('latin-1')

        # --- Logo / Nombre Emisor ---
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 51, 153)
        # Nombre de la empresa
        self.cell(100, 10, txt(self.data.emisor_nombre[:35]), 0, 0, 'L')
        
        # --- Cuadro RUC (CORREGIDO) ---
        self.set_text_color(0)
        self.set_font('Arial', 'B', 10)
        
        # Coordenadas fijas para el cuadro
        x_ruc = 120
        y_ruc = 10
        
        # 1. Dibujamos el rectángulo
        self.rect(x_ruc, y_ruc, 80, 25)
        
        # 2. Posicionamos textos usando set_xy (NO x= en cell)
        self.set_xy(x_ruc, y_ruc + 4)
        self.cell(80, 5, txt(f"{self.data.document_type.upper()}"), 0, 1, 'C')
        
        self.set_xy(x_ruc, y_ruc + 11)
        self.cell(80, 5, txt(f"RUC: {self.data.emisor_ruc}"), 0, 1, 'C')
        
        self.set_xy(x_ruc, y_ruc + 18)
        self.cell(80, 5, txt(self.data.serie_correlativo), 0, 1, 'C')
        
        # --- Dirección Emisor ---
        self.set_xy(10, 20)
        self.set_font('Arial', '', 8)
        self.cell(100, 5, txt(self.data.emisor_direccion[:60]), 0, 1)
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def create_invoice_pdf(data: InvoiceData) -> bytes:
    # Helper para tildes
    def txt(texto):
        return str(texto).encode('latin-1', 'replace').decode('latin-1')

    pdf = PDFGenerator(data)
    pdf.add_page()
    
    # --- Datos Cliente ---
    pdf.set_font("Arial", "", 9)
    # Dibujar cuadro
    pdf.rect(10, 45, 190, 25)
    pdf.set_xy(12, 47)
    
    # Fila 1: Cliente
    pdf.set_font("Arial", "B", 9)
    pdf.cell(20, 5, "Cliente:", 0, 0)
    pdf.set_font("Arial", "", 9)
    pdf.cell(100, 5, txt(data.client), 0, 1)
    
    # Fila 2: Dirección
    pdf.set_x(12)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(20, 5, txt("Dirección:"), 0, 0)
    pdf.set_font("Arial", "", 9)
    pdf.cell(100, 5, txt(data.client_address), 0, 1)
    
    # Fila 3: RUC/DNI y Moneda
    pdf.set_x(12)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(20, 5, "RUC/DNI:", 0, 0)
    pdf.set_font("Arial", "", 9)
    pdf.cell(50, 5, txt(data.client_ruc_dni), 0, 0)
    
    pdf.set_font("Arial", "B", 9)
    pdf.cell(20, 5, "Moneda:", 0, 0)
    pdf.set_font("Arial", "", 9)
    pdf.cell(30, 5, txt(data.moneda), 0, 1)

    # Fila 4: Fechas (Agregado para completitud)
    pdf.set_x(12)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(20, 5, "Fecha:", 0, 0)
    pdf.set_font("Arial", "", 9)
    pdf.cell(50, 5, txt(data.fecha_emision), 0, 1)
    
    pdf.ln(10)
    
    # --- Tabla Items ---
    # Encabezado
    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("Arial", "B", 9)
    
    pdf.cell(20, 7, "CANT", 1, 0, 'C', fill=True)
    pdf.cell(100, 7, txt("DESCRIPCIÓN"), 1, 0, 'C', fill=True)
    pdf.cell(20, 7, "UND", 1, 0, 'C', fill=True)
    pdf.cell(25, 7, "P.UNIT", 1, 0, 'C', fill=True)
    pdf.cell(25, 7, "TOTAL", 1, 1, 'C', fill=True)
    
    # Filas
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
    
    # --- Totales ---
    pdf.set_font("Arial", "B", 9)
    pdf.cell(0, 5, txt(f"SON: {data.monto_letras}"), 0, 1)
    
    igv = subtotal * 0.18
    total_final = subtotal + igv
    
    # Cuadro totales a la derecha
    x_totales = 135
    pdf.set_x(x_totales)
    pdf.cell(30, 6, "Subtotal", 1, 0)
    pdf.cell(30, 6, f"{subtotal:.2f}", 1, 1, 'R')
    
    pdf.set_x(x_totales)
    pdf.cell(30, 6, "IGV 18%", 1, 0)
    pdf.cell(30, 6, f"{igv:.2f}", 1, 1, 'R')
    
    pdf.set_x(x_totales)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(30, 6, "TOTAL", 1, 0)
    pdf.cell(30, 6, f"{total_final:.2f}", 1, 1, 'R')

    return bytes(pdf.output())

# --- 5. ENDPOINTS ---

@app.post("/procesar-factura", response_model=InvoiceData)
def process_invoice(request: InvoiceRequest):
    print(f"📥 Procesando texto: {request.texto_factura[:30]}...")
    
    raw_data = extract_invoice_data(request.texto_factura)
    
    if "error_message" in raw_data:
        print(f"❌ Error validación IA: {raw_data['error_message']}")
        raise HTTPException(status_code=400, detail=raw_data['error_message'])
    
    try:
        return InvoiceData(**raw_data)
    except Exception as e:
        print(f"❌ Error Pydantic: {e}")
        raise HTTPException(status_code=422, detail="La IA generó datos incompletos. Intente ser más específico.")

@app.post("/generar-pdf")
def generate_pdf_endpoint(invoice_data: InvoiceData):
    print(f"📄 Generando PDF para: {invoice_data.client}")
    try:
        pdf_bytes = create_invoice_pdf(invoice_data)
        filename = f"{invoice_data.document_type.replace(' ', '_')}_{invoice_data.client_ruc_dni}.pdf"
        
        return Response(
            content=pdf_bytes, 
            media_type="application/pdf", 
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc() # Esto imprimirá el error real en tu consola
        raise HTTPException(status_code=500, detail=f"Error interno generando PDF: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)