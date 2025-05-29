# logic/report_generator.py

import pandas as pd
from io import BytesIO
import xlsxwriter
from datetime import datetime

def exportar_excel(df_resultados: pd.DataFrame, df_ingresos: pd.DataFrame = None) -> BytesIO:
    output = BytesIO()

    # Totales para observaciones
    total_ganancias = (
        df_resultados["ganancia_perdida_eur"].sum()
        if not df_resultados.empty and "ganancia_perdida_eur" in df_resultados.columns
        else 0.0
    )
    total_ingresos = (
        df_ingresos["valor_eur"].sum()
        if df_ingresos is not None and not df_ingresos.empty and "valor_eur" in df_ingresos.columns
        else 0.0
    )

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook  = writer.book

        # --- Formatos comunes ---
        bold        = workbook.add_format({"bold": True})
        header_fmt  = workbook.add_format({"bold": True, "bg_color": "#DDEBF7", "border": 1})
        curr_fmt    = workbook.add_format({"num_format": "#,##0.00 €"})
        date_fmt    = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align': 'left'})
        wrap_fmt    = workbook.add_format({'text_wrap': True, 'valign': 'top'})
        total_text  = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'top': 1, 'bottom': 1})
        total_curr  = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'num_format': '#,##0.00 €', 'top': 1, 'bottom': 1})

       
        # === Hoja 1: Ganancias 2024 ===
        sheet_gan = "Ganancias 2024"
        if not df_resultados.empty:
            # Seleccionamos sólo las columnas realmente disponibles
            desired_cols = [
                "fecha", "cripto", "cantidad_vendida",
                "precio_unitario_compra_eur", "precio_unitario_venta_eur",
                "ganancia_perdida_eur"
            ]
            available_cols = [c for c in desired_cols if c in df_resultados.columns]
            df_g = df_resultados[available_cols].copy()
            # Seleccionar solo las columnas disponibles, en el orden ideal
            desired_cols = [
                "fecha", "cripto", "cantidad_vendida",
                "precio_unitario_compra_eur", "precio_unitario_venta_eur",
                "ganancia_perdida_eur"
            ]
            available_cols = [c for c in desired_cols if c in df_resultados.columns]
            df_g = df_resultados[available_cols].copy()


            # Convertir fecha si viene como string
            df_g['fecha'] = df_g['fecha'].apply(
                lambda d: datetime.strptime(d, '%Y-%m-%d').date() if isinstance(d, str)
                          else (d.date() if hasattr(d, 'date') else d)
            )

            df_g.to_excel(writer, sheet_name=sheet_gan, index=False,
                          startrow=1, header=False, na_rep="")

            ws = writer.sheets[sheet_gan]
            # Encabezados
            for col, name in enumerate(df_g.columns):
                ws.write(0, col, name, header_fmt)
            # Ancho y formatos
            for col, name in enumerate(df_g.columns):
                col_data = df_g[name]
                max_len = max(col_data.astype(str).map(len).max(), len(name)) + 2
                if 'fecha' in name.lower():
                    ws.set_column(col, col, max(max_len, 12), date_fmt)
                elif 'valor' in name.lower() or 'fee' in name.lower() or 'ganancia' in name.lower():
                    ws.set_column(col, col, max(max_len, 15), curr_fmt)
                else:
                    ws.set_column(col, col, max_len)
            ws.autofilter(0, 0, len(df_g), len(df_g.columns)-1)
            ws.freeze_panes(1, 0)
            # Fila totales
            idx = df_g.columns.get_loc("ganancia_perdida_eur")
            last = len(df_g) + 1
            ws.write_string(last, idx-1, "TOTAL:", total_text)
            col_letter = xlsxwriter.utility.xl_col_to_name(idx)
            ws.write_formula(last, idx, f"=SUM({col_letter}2:{col_letter}{last})", total_curr)
        else:
            ws = workbook.add_worksheet(sheet_gan)
            ws.write("A1", "No se generaron ganancias o pérdidas patrimoniales.", bold)

        # === Hoja 2: Ingresos 2024 ===
        sheet_ing = "Ingresos 2024"
        if df_ingresos is not None and not df_ingresos.empty:
            df_i = df_ingresos[[
                "fecha", "tipo", "cripto", "cantidad", "valor_eur", "fee_eur"
            ]].copy()
            df_i['fecha'] = df_i['fecha'].apply(
                lambda d: datetime.strptime(d, '%Y-%m-%d').date() if isinstance(d, str)
                          else (d.date() if hasattr(d, 'date') else d)
            )

            df_i.to_excel(writer, sheet_name=sheet_ing, index=False,
                          startrow=1, header=False, na_rep="")

            ws2 = writer.sheets[sheet_ing]
            for col, name in enumerate(df_i.columns):
                ws2.write(0, col, name, header_fmt)
            for col, name in enumerate(df_i.columns):
                col_data = df_i[name]
                max_len = max(col_data.astype(str).map(len).max(), len(name)) + 2
                if 'fecha' in name.lower():
                    ws2.set_column(col, col, max(max_len, 12), date_fmt)
                elif 'valor_eur' in name.lower() or 'fee_eur' in name.lower():
                    ws2.set_column(col, col, max(max_len, 15), curr_fmt)
                else:
                    ws2.set_column(col, col, max_len)
            ws2.autofilter(0, 0, len(df_i), len(df_i.columns)-1)
            ws2.freeze_panes(1, 0)
            # Fila totales ingresos
            idx2 = df_i.columns.get_loc("valor_eur")
            last2 = len(df_i) + 1
            ws2.write_string(last2, idx2-1, "TOTAL:", total_text)
            col2 = xlsxwriter.utility.xl_col_to_name(idx2)
            ws2.write_formula(last2, idx2, f"=SUM({col2}2:{col2}{last2})", total_curr)
        else:
            ws2 = workbook.add_worksheet(sheet_ing)
            ws2.write("A1", "No se detectaron ingresos (staking, airdrops, intereses).", bold)

        # === Hoja 3: Observaciones ===
        sheet_obs = "Observaciones"
        ws3 = workbook.add_worksheet(sheet_obs)
        ws3.set_column("A:A", 70, wrap_fmt)
        ws3.set_column("B:B", 20, curr_fmt)

        # Título principal
        ws3.merge_range(0, 0, 0, 1,
            "📝 Instrucciones fiscales para IRPF – Modelo 100 (España, 2025)",
            header_fmt
        )

        # 1) Ganancias patrimoniales
        row = 2
        ws3.write(row,   0, "1. Ganancias patrimoniales (ventas de criptomonedas):", bold)
        ws3.write(row+1, 0, "- Declarar en: Casillas 180 a 185 (base del ahorro)")
        ws3.write(row+2, 0, f"- Importe: {total_ganancias:.2f} €",        bold)

        # 2) Ingresos cripto
        row += 4
        ws3.write(row,   0, "2. Ingresos cripto (staking, airdrops, intereses):", bold)
        ws3.write(row+1, 0, "- Declarar en: Casilla 24 o 030/031 (rendimientos del capital mobiliario)")
        ws3.write(row+2, 0, f"- Importe: {total_ingresos:.2f} €",         bold)

        # 3) Notas adicionales
        row += 5
        ws3.write(row, 0, "3. Notas adicionales:", bold)
        notes = [
            "• Las pérdidas se pueden compensar solo con ganancias del mismo tipo.",
            "• Las comisiones han sido deducidas automáticamente (si están en el CSV).",
            "• Se ha aplicado el método FIFO según normativa fiscal española.",
            "• Informe orientativo, consulte con un asesor fiscal.",
            "• Guarde este informe y justificantes al menos 4 años."
        ]
        for i, note in enumerate(notes, start=1):
            ws3.write(row+i, 0, note, wrap_fmt)

        # Pie de página
        ws3.write(row+len(notes)+2, 0,
            "Generado automáticamente por tu App Fiscal Cripto.", bold)

        

    output.seek(0)
    return output


