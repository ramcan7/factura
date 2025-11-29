import streamlit as st
import google.generativeai as genai
import json
import re
from fpdf import FPDF

# ==========================================
# 1. CONFIGURATION (SETUP)
# ==========================================

# Configure page settings
st.set_page_config(page_title="SUNAT Billing Agent", page_icon="🧾")

# Get API Key from sidebar for security during demo
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Google API Key", type="password")
    if api_key:
        genai.configure(api_key=api_key)

# SYSTEM INSTRUCTIONS (The "Brain")
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

# Initialize Model (Fallback to 1.5 if 2.5 is not available in your region)
try:
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", # Changed to 1.5 stable for hackathon safety
        system_instruction=GEM_SYSTEM_INSTRUCTION
    )
except Exception as e:
    st.error(f"Error configuring model: {e}")

# ==========================================
# 2. BACKEND LOGIC (The Processor)
# ==========================================

def calculate_invoice_totals(data):
    """
    Backend Logic: Receives raw JSON from AI, applies business rules (math),
    and returns the finalized data structure.
    """
    IGV_RATE = 0.18
    
    subtotal_accumulated = 0.0
    processed_items = []

    # Iterate items to calculate line totals
    for item in data.get('items', []):
        try:
            qty = float(item.get('quantity', 1))
            price = float(item.get('unit_price', 0))
        except ValueError:
            qty, price = 1.0, 0.0
            
        line_total = qty * price
        subtotal_accumulated += line_total
        
        # Update item with calculated total
        item['quantity'] = qty
        item['unit_price'] = price
        item['line_total'] = round(line_total, 2)
        processed_items.append(item)

    # Final Tax Calculations
    subtotal = subtotal_accumulated
    igv = subtotal * IGV_RATE
    total = subtotal + igv

    # Construct the final "Backend" object
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
    """
    PDF Generator Service: Takes the final JSON object and renders a 
    professional-looking PDF file.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- Header Design ---
    pdf.set_fill_color(0, 0, 0) # Black
    pdf.rect(0, 0, 210, 20, 'F') # Top black bar
    
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(255, 255, 255) # White text
    pdf.set_xy(10, 5)
    pdf.cell(0, 10, "FACTURA ELECTRÓNICA", ln=True)
    
    # --- Company Info (Left) ---
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(10, 30)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 5, "MI EMPRESA S.A.C.", ln=True)
    pdf.set_font("Arial", '', 9)
    pdf.set_text_color(100, 100, 100) # Grey
    pdf.cell(0, 5, "RUC: 20100100100", ln=True)
    pdf.cell(0, 5, "Av. La Innovación 123, Lima", ln=True)
    
    # --- Client Info (Right Box) ---
    client = data.get('client', {})
    pdf.set_xy(120, 30)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 5, "CLIENTE / ADQUIRENTE", ln=True)
    pdf.set_xy(120, 36)
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(80, 5, f"{client.get('name', 'N/A')}\nRUC: {client.get('ruc', 'N/A')}\n{client.get('address', 'Lima, Perú')}")

    # --- Table Header ---
    pdf.ln(20)
    pdf.set_xy(10, 60)
    pdf.set_fill_color(50, 50, 50) # Dark Grey
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 9)
    
    # Header Row
    pdf.cell(100, 8, "DESCRIPCIÓN", 0, 0, 'L', 1)
    pdf.cell(20, 8, "CANT.", 0, 0, 'C', 1)
    pdf.cell(35, 8, "P. UNIT", 0, 0, 'R', 1)
    pdf.cell(35, 8, "TOTAL", 0, 1, 'R', 1)

    # --- Table Rows ---
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 9)
    
    for item in data.get('items', []):
        pdf.cell(100, 8, str(item['description']), 'B')
        pdf.cell(20, 8, str(item['quantity']), 'B', 0, 'C')
        pdf.cell(35, 8, f"{item['unit_price']:.2f}", 'B', 0, 'R')
        pdf.cell(35, 8, f"{item['line_total']:.2f}", 'B', 1, 'R')

    # --- Totals Section ---
    totals = data.get('totals', {})
    pdf.ln(5)
    
    # Helper for right-aligned totals
    def print_total_line(label, value, is_bold=False):
        pdf.set_font("Arial", 'B' if is_bold else '', 10)
        pdf.cell(140, 7, "", 0) # Padding left
        pdf.cell(25, 7, label, 0, 0, 'R')
        pdf.cell(25, 7, f"S/ {value:.2f}", 0, 1, 'R')

    print_total_line("Subtotal:", totals['subtotal'])
    print_total_line("IGV (18%):", totals['igv'])
    
    # Grand Total Line
    pdf.set_draw_color(0, 0, 0)
    pdf.line(150, pdf.get_y(), 200, pdf.get_y()) # Line above total
    print_total_line("TOTAL:", totals['total'], is_bold=True)
    
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 3. FRONTEND UI (The Interaction)
# ==========================================

st.title("🧾 SUNAT Billing Agent")
st.caption("Powered by Google Gemini 1.5 Flash")
st.write("---")

# 1. Input Section
user_input = st.chat_input("Escribe: 'Factura para Empresa ABC con RUC 20555... por 5 laptops a 1500'")

if user_input:
    # Validate API Key
    if not api_key:
        st.warning("⚠️ Please enter your API Key in the sidebar first.")
        st.stop()

    # Show User Bubble
    st.chat_message("user").write(user_input)

    with st.chat_message("assistant"):
        status_container = st.status("Processing Invoice...", expanded=True)
        
        try:
            # STEP A: Send prompt to Gemini (Frontend -> API)
            status_container.write("🧠 AI Extracting data...")
            response = model.generate_content(
                user_input,
                generation_config={"response_mime_type": "application/json"}
            )
            raw_data = json.loads(response.text)
            
            # STEP B: Send JSON to Backend Logic (Frontend -> Backend Function)
            status_container.write("⚙️ Calculating taxes (IGV)...")
            final_invoice = calculate_invoice_totals(raw_data)
            
            # STEP C: Generate PDF File (Backend Function -> File Bytes)
            status_container.write("📄 Rendering PDF file...")
            pdf_bytes = generate_pdf(final_invoice)
            
            status_container.update(label="✅ Invoice Ready!", state="complete", expanded=False)

            # Display Results
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.success("Data Extracted & Verified")
                st.json(final_invoice) # Show the JSON data
                
            with col2:
                st.info("Actions")
                # Download Button (The final output)
                st.download_button(
                    label="📥 Download PDF Invoice",
                    data=pdf_bytes,
                    file_name=f"Factura_{final_invoice['client'].get('ruc', 'Draft')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        except Exception as e:
            status_container.update(label="❌ Error", state="error")
            st.error(f"An error occurred: {e}")