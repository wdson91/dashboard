import re

def parse_faturas(text):
    # O padrão para identificar o início de cada fatura
    # Como a fatura começa com 'Fatura-Recibo nº FR ...'
    # Usamos split para separar o texto em blocos, mantendo o delimitador no resultado
    partes = re.split(r'(Fatura-Recibo nº\s*FR\s*\S+)', text)

    faturas_texto = []
    # Reconstruindo cada fatura completa, pois o split separa o delimitador
    for i in range(1, len(partes), 2):
        cabecalho = partes[i]
        corpo = partes[i+1] if i+1 < len(partes) else ''
        faturas_texto.append(cabecalho + corpo)

    lista_faturas = []

    for fatura_text in faturas_texto:
        fatura = {
            "numero_fatura": None,
            "data": None,
            "hora": None,
            "itens": [],
            "total": 0.0
        }

        match_num = re.search(r"Fatura-Recibo nº\s*(FR\s*\S+)", fatura_text)
        if match_num:
            fatura["numero_fatura"] = match_num.group(1).strip()

        match_data = re.search(r"Data:\s*(\d{1,2})/(\d{1,2})/(\d{2})\s+(\d{2}):(\d{2})", fatura_text)
        if match_data:
            dia = match_data.group(1).zfill(2)
            mes = match_data.group(2).zfill(2)
            ano = match_data.group(3)
            hora = match_data.group(4).zfill(2)
            minuto = match_data.group(5).zfill(2)
            fatura["data"] = f"20{ano}-{mes}-{dia}"
            fatura["hora"] = f"{hora}:{minuto}:00"

        item_pattern = re.findall(r"(\d+)\s+x\s+(.+?)\s+@\s+([\d,\.]+).*?(\d{1,2}%)[\s\u20AC]*([\d,\.]+)", fatura_text)
        for qty, name, unit_price, tax, total in item_pattern:
            fatura["itens"].append({
                "nome": name.strip(),
                "quantidade": int(qty),
                "preco_unitario": float(unit_price.replace(",", ".")),
                "total": float(total.replace(",", "."))
            })

        match_total = re.search(r"Total\s+([\d,\.]+)", fatura_text)
        if match_total:
            fatura["total"] = float(match_total.group(1).replace(",", "."))

        lista_faturas.append(fatura)

    return lista_faturas
