# app.py
import streamlit as st
import pandas as pd
from io import BytesIO
import time

from logic.transformers import transformar_csv_exchange
from logic.tax_calculator import (
    calcular_fifo,
    calcular_irpf_ingresos,
    calcular_irpf_ganancias
)
from logic.report_generator import exportar_excel

def extraer_cuota(irpf_ret):
    """
    Dado el retorno de calcular_irpf_* (tuple o DataFrame),
    devuelve siempre un float con la cuota de IRPF.
    """
    if isinstance(irpf_ret, tuple):
        _, cuota = irpf_ret
        return float(cuota)
    if isinstance(irpf_ret, pd.DataFrame) and not irpf_ret.empty:
        for col in irpf_ret.columns:
            if 'irpf' in col.lower():
                return float(irpf_ret[col].iloc[0])
        first_val = pd.to_numeric(irpf_ret.iloc[0, 0], errors='coerce')
        return float(first_val) if not pd.isna(first_val) else 0.0
    return 0.0

def main():
    st.set_page_config(page_title="Calculadora Impuestos Cripto 2024", layout="wide")
    st.title("📊 Calculadora de Ganancias/Pérdidas Cripto 2024")

    # 1) Selección de exchange
    exchange = st.selectbox("Selecciona el exchange", ["Binance", "Koinly"])

    # 2) Subida de CSVs
    archivos = st.file_uploader("Sube tus CSVs", type="csv", accept_multiple_files=True)
    if not archivos:
        st.info("Por favor, sube al menos un CSV.")
        return

    # Barra de progreso
    total = len(archivos)
    progress = st.progress(0)
    step = 0

    # 3) Transformar y recopilar errores
    dfs, errores_precio = [], []
    for f in archivos:
        df_raw = pd.read_csv(f)
        try:
            df_std, errs = transformar_csv_exchange(df_raw, exchange)
        except ValueError as e:
            st.error(f"«{f.name}»: {e}")
            continue
        dfs.append(df_std)
        errores_precio.extend(errs)

        # Actualizar progreso
        step += 1
        progress.progress(step / total)

    if not dfs:
        st.warning("No hay CSVs válidos.")
        return

    # 4–6) Conversión USD→EUR y limpieza
    df_ops = pd.concat(dfs, ignore_index=True)
    df_ops['fecha'] = pd.to_datetime(df_ops['fecha']).dt.date
    df_ops = df_ops.sort_values('fecha')

    # 7) FIFO solo sobre ventas/pérdidas
    df_resultados = calcular_fifo(df_ops)
    if 'fecha_venta' in df_resultados.columns:
        df_resultados = df_resultados.rename(columns={'fecha_venta': 'fecha'})

    # 7b) Ingresos cripto
    df_ingresos = pd.concat(dfs, ignore_index=True)
    df_ingresos = (
        df_ingresos[df_ingresos['tipo']=="Ingreso"]
                   .dropna(subset=['cripto','valor_eur'])
                   .reset_index(drop=True)
    )

    # 8a) Ganancias patrimoniales
    st.subheader("🔍 Detalle de ventas con lotes origen (FIFO)")
    cols_detalle = [
        "fecha", "cripto", "cantidad_vendida",
        "precio_unitario_compra_eur", "precio_unitario_venta_eur",
        "ganancia_perdida_eur", "lotes_origen_info"
    ]
    cols_existentes = [c for c in cols_detalle if c in df_resultados.columns]
    st.dataframe(df_resultados[cols_existentes].fillna(""))

    st.markdown("---")

    # 8a-b) Análisis de ganancias patrimoniales (resumen)
    st.subheader("📈 Análisis de ganancias patrimoniales (resumen)")
    df_gan = (
        df_resultados[['fecha', 'cripto', 'ganancia_perdida_eur']]
        .rename(columns={'ganancia_perdida_eur':'ganancia'})
    )
    totales = df_gan.groupby("cripto")["ganancia"].sum()
    validas = totales[totales != 0].index
    df_gan = df_gan[df_gan["cripto"].isin(validas)]
    st.table(df_gan.fillna(""))

    ganancia_neta = df_gan['ganancia'].sum()
    cuota_irpf_gan = extraer_cuota(calcular_irpf_ganancias(df_resultados))

    st.metric("💰 Ganancia neta 2024", f"{ganancia_neta:.2f} €")
    st.metric("📌 IRPF estimado 2025", f"{cuota_irpf_gan:.2f} €")

    st.markdown("---")

    # 8b) Ingresos cripto (staking, airdrops, intereses)
    st.subheader("🤑 Ingresos cripto (staking, airdrops, intereses)")
    st.table(df_ingresos.fillna(""))

    total_ingresos = df_ingresos['valor_eur'].sum()
    cuota_irpf_ing = extraer_cuota(calcular_irpf_ingresos(df_ingresos))

    st.metric("📊 Total ingresos 2024", f"{total_ingresos:.2f} €")
    st.metric("📌 IRPF ingresos estimado 2025", f"{cuota_irpf_ing:.2f} €")

    st.markdown("---")

    # 11) Exportar reporte
    excel_io: BytesIO = exportar_excel(df_resultados, df_ingresos)
    # Aseguramos barra al 100%
    progress.progress(1.0)
    time.sleep(0.1)

    st.download_button(
        "📥 Descargar reporte (.xlsx)",
        data=excel_io.getvalue(),
        file_name="reporte_cripto_2024.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    main()








