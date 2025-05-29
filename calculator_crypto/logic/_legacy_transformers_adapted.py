# logic/_legacy_transformers_adapted.py

import pandas as pd
from datetime import datetime
from .api_pricing import YAHOO_CRYPTO_SYMBOLS  # para obtener las claves conocidas

# Construimos el set de monedas “USD-like” y de todas las criptos listadas
KNOWN_CURRENCIES = set(YAHOO_CRYPTO_SYMBOLS.keys()) | {"eur"}

def normalizar_simbolo_cripto_legacy(simbolo_bruto):
    """
    Normaliza el símbolo que viene en el CSV:
     - Pasa a minúsculas y quita espacios.
     - Si está en KNOWN_CURRENCIES, lo devuelve tal cual.
     - Si acaba en sufijos típicos '-usdt', 'usdt', '-usd', 'usd', elimina el sufijo.
    """
    if pd.isna(simbolo_bruto) or not isinstance(simbolo_bruto, str):
        return None
    s = simbolo_bruto.strip().lower()

    # Si es exactamente una moneda conocida, mantenla
    if s in KNOWN_CURRENCIES:
        return s

    # Si termina en uno de estos sufijos, límpialo (p.ej. 'pepe-usdt' → 'pepe')
    for suf in ("-usdt", "usdt", "-usd", "usd"):
        if s.endswith(suf) and len(s) > len(suf):
            return s[:-len(suf)]

    # Si no coincide con nada, devolvemos el valor limpio
    return s or None


def _convertir_a_eur_si_necesario(valor, moneda, fecha_obj, fn_obtener_precio, errores, cripto_error=""):
    """
    Convierte un importe en una moneda dada a EUR:
     - Si la moneda es EUR, lo devuelve tal cual.
     - Si es USD-like, usa fn_obtener_precio('usd', fecha) como tasa.
     - En caso de error, añade la tupla (moneda, fecha) a errores y devuelve None.
    """
    if valor is None or pd.isna(valor):
        return None

    moneda_norm = normalizar_simbolo_cripto_legacy(moneda)
    if moneda_norm == "eur":
        return float(valor)

    usd_like = {"usd","usdt","usdc","busd","dai","tusd","fdusd"}
    if moneda_norm in usd_like:
        tasa = fn_obtener_precio("usd", fecha_obj)
        if tasa is not None:
            return float(valor) * tasa
        errores.append(("usd", fecha_obj))
        if cripto_error:
            errores.append((cripto_error, fecha_obj))
    return None


def transformar_binance_adaptado(df_raw: pd.DataFrame, fn_obtener_precio):
    """
    Transformador para Binance CSV “Transaction History”.
    Extrae COMPRAS, VENTAS e INGRESOS, convierte todo a EUR.
    """
    df = df_raw.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    # Renombrar fecha UTC
    if 'date(utc)' in df.columns and 'utc_time' not in df.columns:
        df.rename(columns={'date(utc)': 'utc_time'}, inplace=True)
    if 'utc_time' not in df.columns:
        raise ValueError("Binance CSV requiere columna 'UTC_Time' o 'Date(UTC)'.")

    # Preparar fechas y filtrar 2024
    df['fecha_dt'] = pd.to_datetime(df['utc_time'], errors='coerce')
    df['fecha'] = df['fecha_dt'].dt.date
    df = df[df['fecha_dt'].dt.year == 2024]

    if df.empty:
        cols = ['fecha','tipo','cripto','cantidad','valor_eur','fee_eur']
        return pd.DataFrame(columns=cols), []

    procesos = []
    errores = []
    processed = set()

    for ts, group in df.groupby('utc_time'):
        fecha_obj = group['fecha'].iloc[0]

        # VENTAS
        sold = group[group['operation'].str.lower() == "transaction sold"]
        if not sold.empty:
            for _, row in sold.iterrows():
                idx = row.name
                if idx in processed: continue
                processed.add(idx)

                cripto = normalizar_simbolo_cripto_legacy(row['coin'])
                cantidad = abs(pd.to_numeric(row['change'], errors='coerce'))
                if not cripto or pd.isna(cantidad) or cantidad <= 0:
                    continue

                # revenue = valor bruto de venta
                rev = group[group['operation'].str.lower() == "transaction revenue"]
                valor_eur = None
                if not rev.empty:
                    r = rev.iloc[0]
                    processed.add(r.name)
                    valor = pd.to_numeric(r['change'], errors='coerce')
                    valor_eur = _convertir_a_eur_si_necesario(
                        valor, r['coin'], fecha_obj, fn_obtener_precio, errores, cripto
                    )

                # fee
                fee_eur = 0.0
                fee_rows = group[group['operation'].str.lower() == "transaction fee"]
                if not fee_rows.empty:
                    f = fee_rows.iloc[0]
                    processed.add(f.name)
                    amt = abs(pd.to_numeric(f['change'], errors='coerce'))
                    moneda_fee = normalizar_simbolo_cripto_legacy(f['coin'])
                    fee_conv = fn_obtener_precio(moneda_fee, fecha_obj)
                    if fee_conv is not None:
                        fee_eur = amt * fee_conv
                    else:
                        conv = _convertir_a_eur_si_necesario(
                            amt, f['coin'], fecha_obj, fn_obtener_precio, errores
                        )
                        fee_eur = conv or 0.0

                # fallback si valor_eur no calculado
                if valor_eur is None:
                    precio_unit = fn_obtener_precio(cripto, fecha_obj)
                    if precio_unit is not None:
                        valor_eur = cantidad * precio_unit
                    else:
                        errores.append((cripto, fecha_obj))

                procesos.append({
                    "fecha": fecha_obj, "tipo": "Venta", "cripto": cripto,
                    "cantidad": cantidad, "valor_eur": valor_eur, "fee_eur": fee_eur
                })
            continue

        # COMPRAS
        buys = group[group['operation'].str.lower() == "transaction buy"]
        if not buys.empty:
            for _, row in buys.iterrows():
                idx = row.name
                if idx in processed: continue
                processed.add(idx)

                cripto = normalizar_simbolo_cripto_legacy(row['coin'])
                cantidad = pd.to_numeric(row['change'], errors='coerce')
                if not cripto or pd.isna(cantidad) or cantidad <= 0:
                    continue

                spend = group[group['operation'].str.lower() == "transaction spend"]
                valor_eur = None
                if not spend.empty:
                    s = spend.iloc[0]
                    processed.add(s.name)
                    amt = abs(pd.to_numeric(s['change'], errors='coerce'))
                    valor_eur = _convertir_a_eur_si_necesario(
                        amt, s['coin'], fecha_obj, fn_obtener_precio, errores, cripto
                    )

                if valor_eur is None:
                    precio_unit = fn_obtener_precio(cripto, fecha_obj)
                    if precio_unit is not None:
                        valor_eur = cantidad * precio_unit
                    else:
                        errores.append((cripto, fecha_obj))

                procesos.append({
                    "fecha": fecha_obj, "tipo": "Compra", "cripto": cripto,
                    "cantidad": cantidad, "valor_eur": valor_eur, "fee_eur": 0.0
                })
            continue

        # INGRESOS / DONACIONES y otros
        for _, row in group.iterrows():
            idx = row.name
            if idx in processed:
                continue
            op = str(row['operation']).lower()
            cripto = normalizar_simbolo_cripto_legacy(row['coin'])
            change = pd.to_numeric(row['change'], errors='coerce')
            processed.add(idx)

            if not cripto or pd.isna(change) or abs(change) <= 0:
                continue

            tipo = None
            valor_eur = None
            fee_eur = 0.0

            if any(x in op for x in ["airdrop","reward","interest","staking","mining","distribution"]):
                tipo = "Ingreso"
                precio = fn_obtener_precio(cripto, fecha_obj)
                if precio is not None:
                    valor_eur = abs(change) * precio
                else:
                    errores.append((cripto, fecha_obj))

            elif op == "deposit":
                tipo = "Compra"
                precio = fn_obtener_precio(cripto, fecha_obj)
                if precio is not None:
                    valor_eur = change * precio
                else:
                    errores.append((cripto, fecha_obj))

            elif op == "withdraw":
                tipo = "Venta"
                precio = fn_obtener_precio(cripto, fecha_obj)
                if precio is not None:
                    valor_eur = abs(change) * precio
                else:
                    errores.append((cripto, fecha_obj))

            if tipo:
                procesos.append({
                    "fecha": fecha_obj, "tipo": tipo, "cripto": cripto,
                    "cantidad": abs(change), "valor_eur": valor_eur, "fee_eur": fee_eur
                })

    df_out = pd.DataFrame(procesos)
    cols = ['fecha','tipo','cripto','cantidad','valor_eur','fee_eur']
    df_out = df_out[cols] if not df_out.empty else pd.DataFrame(columns=cols)
    return df_out, list({(c,d) for (c,d) in errores})


def transformar_koinly_adaptado(df_raw: pd.DataFrame, fn_obtener_precio):
    """
    Transformador para Koinly CSV.
    Extrae INGRESOS y TRADES (Compra/Venta), convierte todo a EUR.
    """
    df = df_raw.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    if 'date' not in df.columns:
        raise ValueError("Koinly CSV requiere columna 'Date'.")

    # 1) Crear columna datetime para filtrado
    df['fecha_dt'] = pd.to_datetime(df['date'], errors='coerce')
    # 2) Filtrar sólo año 2024 usando fecha_dt
    df = df[df['fecha_dt'].dt.year == 2024]
    # 3) Extraer fecha como date
    df['fecha'] = df['fecha_dt'].dt.date

    if df.empty:
        cols = ['fecha','tipo','cripto','cantidad','valor_eur','fee_eur']
        return pd.DataFrame(columns=cols), []

    procesos = []
    errores = []

    for _, row in df.iterrows():
        tipo_koinly = str(row.get('type','')).lower()
        label = str(row.get('label','')).lower()
        fecha = row['fecha']

        sent_amt = pd.to_numeric(row.get('sent amount'), errors='coerce')
        sent_cur = normalizar_simbolo_cripto_legacy(row.get('sent currency'))
        recv_amt = pd.to_numeric(row.get('received amount'), errors='coerce')
        recv_cur = normalizar_simbolo_cripto_legacy(row.get('received currency'))
        fee_amt = pd.to_numeric(row.get('fee amount'), errors='coerce')
        fee_cur = normalizar_simbolo_cripto_legacy(row.get('fee currency'))

        # Fee
        fee_eur = 0.0
        if pd.notna(fee_amt) and fee_amt > 0 and fee_cur:
            precio_fee = fn_obtener_precio(fee_cur, fecha)
            if precio_fee is not None:
                fee_eur = fee_amt * precio_fee
            else:
                conv = _convertir_a_eur_si_necesario(fee_amt, fee_cur, fecha, fn_obtener_precio, errores)
                fee_eur = conv or 0.0

        # INGRESOS
        if tipo_koinly == "receive" and any(x in label for x in ("reward","staking","interest","airdrop","mining","n/a")):
            if recv_cur and pd.notna(recv_amt) and recv_amt > 0:
                precio = fn_obtener_precio(recv_cur, fecha)
                if precio is not None:
                    valor = recv_amt * precio
                    procesos.append({
                        "fecha": fecha, "tipo": "Ingreso", "cripto": recv_cur,
                        "cantidad": recv_amt, "valor_eur": valor, "fee_eur": fee_eur
                    })
                else:
                    errores.append((recv_cur, fecha))

        # TRADES
        if tipo_koinly == "trade":
            # Venta
            if pd.notna(sent_amt) and sent_amt > 0 and sent_cur:
                precio = fn_obtener_precio(sent_cur, fecha)
                valor = sent_amt * precio if precio is not None else None
                if valor is not None:
                    procesos.append({
                        "fecha": fecha, "tipo": "Venta", "cripto": sent_cur,
                        "cantidad": sent_amt, "valor_eur": valor, "fee_eur": fee_eur
                    })
                else:
                    errores.append((sent_cur, fecha))
            # Compra
            if pd.notna(recv_amt) and recv_amt > 0 and recv_cur:
                precio = fn_obtener_precio(recv_cur, fecha)
                valor = recv_amt * precio if precio is not None else None
                if valor is not None:
                    procesos.append({
                        "fecha": fecha, "tipo": "Compra", "cripto": recv_cur,
                        "cantidad": recv_amt, "valor_eur": valor, "fee_eur": 0.0
                    })
                else:
                    errores.append((recv_cur, fecha))

    cols = ['fecha','tipo','cripto','cantidad','valor_eur','fee_eur']
    df_out = pd.DataFrame(procesos)
    if not df_out.empty:
        df_out = df_out[cols]
    else:
        df_out = pd.DataFrame(columns=cols)
    return df_out, list({(c,d) for (c,d) in errores})


def transformar_coinbase_placeholder_adaptado(df_raw, fn_obtener_precio):
    print("ADVERTENCIA: Transformador Coinbase no implementado todavía.")
    cols = ['fecha','tipo','cripto','cantidad','valor_eur','fee_eur']
    return pd.DataFrame(columns=cols), []


def transformar_kraken_placeholder_adaptado(df_raw, fn_obtener_precio):
    print("ADVERTENCIA: Transformador Kraken no implementado todavía.")
    cols = ['fecha','tipo','cripto','cantidad','valor_eur','fee_eur']
    return pd.DataFrame(columns=cols), []


def transformar_kucoin_placeholder_adaptado(df_raw, fn_obtener_precio):
    print("ADVERTENCIA: Transformador KuCoin no implementado todavía.")
    cols = ['fecha','tipo','cripto','cantidad','valor_eur','fee_eur']
    return pd.DataFrame(columns=cols), []

