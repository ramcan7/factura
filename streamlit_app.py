import streamlit as st
import google.generativeai as genai
import json
import re
from fpdf import FPDF

GEM_SYSTEM_INSTRUCTION = """
Role: You are an expert billing assistant for the Peruvian system (SUNAT).
Task: Extract invoice details from natural language and return strict JSON.

Business Rules:
1. Client: Extract name and RUC (Tax ID). If RUC is missing, generate a dummy 11-digit one.
2. Items: Extract description, quantity (default to 1), and unit price.
3. Constraint: Do NOT calculate totals. Set 'subtotal', 'igv', and 'total' to 0.
4. Output: Return ONLY raw JSON. No markdown, no explanations.

JSON Structure:
{
  "client": { "name": "string", "ruc": "string", "address": "string" },
  "items": [
    { "description": "string", "quantity": float, "unit_price": float }
  ]
}
"""

# Initialize the model with your Gem's instructions
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=GEM_SYSTEM_INSTRUCTION
)

# --- 3. HELPER FUNCTIONS (LOGIC) ---

def calculate_invoice_totals(data):
    """
    Performs deterministic math calculations (Python).
    Rule: Total = Base * 1.18 (18% IGV)
    """
    IGV_RATE = 0.18
    
    subtotal_accumulated = 0.0
    processed_items = []

    # Calculate line by line
    for item in data.get('items', []):
        qty = float(item.get('quantity', 1))
        price = float(item.get('unit_price', 0))
        line_total = qty * price
        
        subtotal_accumulated += line_total
        
        # Add calculation back to item
        item['line_total'] = round(line_total, 2)
        processed_items.append(item)

    # Calculate Finals
    subtotal = subtotal_accumulated
    igv = subtotal * IGV_RATE
    total = subtotal + igv

    # Construct final dictionary
    return {
        "client": data.get('client', {}),
        "items": processed_items,
        "totals": {
            "subtotal": round(subtotal, 2),
            "igv": round(igv, 2),
            "total": round(total, 2)
        }
    }

def generate_pdf(data):
    """Generates a simple PDF invoice"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "ELECTRONIC INVOICE (SUNAT)", ln=True, align='C')
    
    pdf.set_font("Arial", size=10)
    client = data['client']
    pdf.ln(10)
    pdf.cell(0, 5, f"Client: {client.get('name', 'N/A')}", ln=True)
    pdf.cell(0, 5, f"RUC: {client.get('ruc', 'N/A')}", ln=True)
    
    pdf.ln(10)
    # Headers
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(100, 8, "Description", 1, 0, 'C', 1)
    pdf.cell(20, 8, "Qty", 1, 0, 'C', 1)
    pdf.cell(35, 8, "Unit Price", 1, 0, 'C', 1)
    pdf.cell(35, 8, "Total", 1, 1, 'C', 1)
    
    # Rows
    for item in data['items']:
        pdf.cell(100, 8, str(item['description']), 1)
        pdf.cell(20, 8, str(item['quantity']), 1, 0, 'C')
        pdf.cell(35, 8, f"{item['unit_price']:.2f}", 1, 0, 'R')
        pdf.cell(35, 8, f"{item['line_total']:.2f}", 1, 1, 'R')
        
    # Totals
    totals = data['totals']
    pdf.ln(5)
    pdf.cell(155, 8, "Subtotal:", 0, 0, 'R')
    pdf.cell(35, 8, f"{totals['subtotal']:.2f}", 0, 1, 'R')
    pdf.cell(155, 8, "IGV (18%):", 0, 0, 'R')
    pdf.cell(35, 8, f"{totals['igv']:.2f}", 0, 1, 'R')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(155, 10, "TOTAL:", 0, 0, 'R')
    pdf.cell(35, 10, f"{totals['total']:.2f}", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. USER INTERFACE (STREAMLIT) ---

st.title("🧾 SUNAT Agente de facturación")
st.caption("Powered by Google Gemini 1.5 Flash")

# Chat Input
user_input = st.chat_input("Ejemplo: Crea una factura para el cliente ABC, RUC 20123456789, 5 laptops a 1500 cada una...")

if user_input and api_key:
    # 1. Display User Message
    st.chat_message("user").write(user_input)
    
    with st.spinner("Gemini is extracting data..."):
        try:
            # 2. Call Gemini (The Brain)
            response = model.generate_content(
                user_input,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # 3. Process Data
            raw_data = json.loads(response.text)
            final_invoice = calculate_invoice_totals(raw_data)
            
            # 4. Display Result
            with st.chat_message("assistant"):
                st.success("Invoice generated successfully!")
                
                # Show JSON for debugging/validation
                with st.expander("View Raw JSON Data"):
                    st.json(final_invoice)
                
                # Generate PDF
                pdf_bytes = generate_pdf(final_invoice)
                
                # Download Button
                st.download_button(
                    label="📥 Download PDF Invoice",
                    data=pdf_bytes,
                    file_name="invoice_output.pdf",
                    mime="application/pdf"
                )
                
        except Exception as e:
            st.error(f"An error occurred: {e}")