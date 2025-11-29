def calcular_totales(data: Dict[str, Any], igv_rate: float = IGV_RATE) -> Dict[str, Any]:
    """
    Calcula el subtotal, el IGV y el total a partir de los ítems extraídos.
    """
    if "error" in data:
        return data

    subtotal_neto = 0.0
    items_calculados = []

    for item in data.get("items", []):
        try:
            subtotal = round(item["cantidad"] * item["precio_unitario"], 2)
            item["subtotal"] = subtotal
            subtotal_neto += subtotal
            items_calculados.append(item)
        except (KeyError, TypeError) as e:
            raise ValueError(f"Dato numérico faltante o inválido en un ítem: {e}")

    monto_igv = round(subtotal_neto * igv_rate, 2)
    total = round(subtotal_neto + monto_igv, 2)


    final_invoice = {
        "tipo_documento": data.get("tipo_documento", "Factura"),
        "cliente": data["cliente"],
        "ruc_simulado": data["ruc_simulado"],
        "items": items_calculados,
        "moneda": data.get("moneda", "Soles"),
        "subtotal_neto": subtotal_neto,
        "monto_igv": monto_igv,
        "total": total,
        "igv_porcentaje": igv_rate
    }
    
    return final_invoice