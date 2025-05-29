# logic/transformers.py

import pandas as pd
from .api_pricing import obtener_precio_historico_eur, normalizar_simbolo_app

# Mapa de exchanges a sus funciones de transformación adaptadas
TRANSFORMERS = {
    "Binance": "transformar_binance_adaptado",
    "Koinly":  "transformar_koinly_adaptado",
    "Coinbase": "transformar_coinbase_placeholder_adaptado",
    "Kraken":  "transformar_kraken_placeholder_adaptado",
    "KuCoin":  "transformar_kucoin_placeholder_adaptado",
}

def transformar_csv_exchange(df_raw: pd.DataFrame, exchange_name: str):
    """
    Recibe un DataFrame crudo de un CSV y el nombre del exchange, 
    retorna (df_estandarizado, lista_errores_precio).
    Usa el transformador legacy correspondiente, pasándole
    obtener_precio_historico_eur para USD→EUR.
    """
    # 1) Normalizar columnas a minúsculas sin espacios
    df = df_raw.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    # 2) Normalizar símbolos en columna 'symbol' o 'cripto' si existiera
    #    (algunos legados esperan ya una columna 'cripto' homogénea)
    if 'symbol' in df.columns and 'cripto' not in df.columns:
        df = df.rename(columns={'symbol': 'cripto'})

    # 3) Escoger el transformador según exchange_name
    func_name = TRANSFORMERS.get(exchange_name)
    if not func_name:
        # Exchange no soportado
        columnas = ['fecha', 'tipo', 'cripto', 'cantidad', 'valor_eur', 'fee_eur']
        return pd.DataFrame(columns=columnas), []

    # 4) Import dinámico de la función del módulo legacy
    module = __import__('logic._legacy_transformers_adapted', fromlist=[func_name])
    transform_fn = getattr(module, func_name, None)
    if not transform_fn:
        raise ImportError(f"No se encontró la función {func_name} en _legacy_transformers_adapted.py")

    # 5) Llamada al transformador, pasándole la función real de pricing
    df_std, errores = transform_fn(df, obtener_precio_historico_eur)

    # 6) Asegurar que la columna 'cripto' está normalizada
    if 'cripto' in df_std.columns:
        df_std['cripto'] = df_std['cripto'].apply(normalizar_simbolo_app)

    return df_std, errores
