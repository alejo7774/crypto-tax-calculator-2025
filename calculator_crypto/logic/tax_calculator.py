# logic/tax_calculator.py

import pandas as pd
from collections import deque
from datetime import timedelta

def calcular_fifo(df_operaciones: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula las ganancias/pérdidas patrimoniales usando FIFO para cada cripto.
    Columnas de entrada:
      - fecha (date o convertible)
      - tipo: "Compra", "Venta", "Donacion", "Ingreso"
      - cripto: str
      - cantidad: float
      - valor_eur: float (coste o valor de mercado)
      - fee_eur: float (opcional)
    Devuelve DataFrame con:
      ['fecha_venta','cripto','tipo_operacion','cantidad_vendida',
       'valor_transmision_neto_eur','coste_adquisicion_total_eur',
       'ganancia_perdida_eur',…]
    """
    df = df_operaciones.copy()
    df['fecha'] = pd.to_datetime(df['fecha']).dt.date
    df = df.sort_values('fecha')

    colas: dict[str, deque] = {}
    ventas = []

    for _, f in df.iterrows():
        tipo = f['tipo']
        cripto = str(f['cripto']).lower()
        cantidad = float(f['cantidad'])
        valor = float(f['valor_eur'])
        fee   = float(f.get('fee_eur', 0.0))
        fecha = f['fecha']

        if cantidad <= 0 or not cripto:
            continue

        if cripto not in colas:
            colas[cripto] = deque()

        # Registro de compra: añadimos lote
        if tipo == "Compra":
            coste_total = valor + fee
            coste_unit = coste_total / cantidad if cantidad else 0.0
            colas[cripto].append({
                'cantidad_disponible': cantidad,
                'coste_unit': coste_unit,
                'fecha_compra': fecha
            })
            continue

        # Venta o Donacion: consumimos FIFO
        if tipo in ("Venta", "Donacion"):
            valor_neto = valor - fee
            restante  = cantidad
            coste_adq  = 0.0
            lotes_info = []

            while restante > 0 and colas[cripto]:
                lote = colas[cripto][0]
                tomados = min(restante, lote['cantidad_disponible'])
                coste_adq += tomados * lote['coste_unit']
                lotes_info.append(f"{tomados:.8f}@{lote['fecha_compra']}@{lote['coste_unit']:.2f}")
                lote['cantidad_disponible'] -= tomados
                restante -= tomados
                if lote['cantidad_disponible'] <= 1e-9:
                    colas[cripto].popleft()

            nota = ""
            if restante > 1e-9:
                nota = f"Sin histórico para {restante:.8f} {cripto}"
                restante = 0.0

            ganancia = valor_neto - coste_adq

            ventas.append({
                'fecha_venta': fecha,
                'cripto': cripto,
                'tipo_operacion': tipo,
                'cantidad_vendida': cantidad,
                'valor_transmision_bruto_eur': valor,
                'comision_venta_eur': fee,
                'valor_transmision_neto_eur': valor_neto,
                'coste_adquisicion_total_eur': coste_adq,
                'ganancia_perdida_eur': ganancia,
                'nota': nota,
                'lotes_origen_info': "; ".join(lotes_info) or "N/A"
            })

    return pd.DataFrame(ventas)


def calcular_irpf_ingresos(df_ingresos: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula el IRPF estimado para ingresos (rendimientos del capital mobiliario).
    - Suma todos los 'valor_eur' y aplica un tipo fijo (p.ej. 19%).
    Devuelve DataFrame:
      ['total_ingresos_eur','irpf_ingresos_eur']
    """
    if df_ingresos.empty or 'valor_eur' not in df_ingresos.columns:
        return pd.DataFrame([{'total_ingresos_eur': 0.0, 'irpf_ingresos_eur': 0.0}])

    total = df_ingresos['valor_eur'].sum()
    tipo = 0.19  # Tipo fijo para rendimientos (ajústalo si cambia)
    return pd.DataFrame([{
        'total_ingresos_eur': total,
        'irpf_ingresos_eur': round(total * tipo, 2)
    }])


def calcular_irpf_ganancias(df_ganancias: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica la escala progresiva de IRPF sobre ganancias patrimoniales.
    Tramos ejemplo (2024):
      - Hasta 6.000€: 19%
      - 6.000€–50.000€: 21%
      - 50.000€–200.000€: 23%
      - Más de 200.000€: 26%
    Devuelve DataFrame con:
      ['base_imponible_eur','irpf_ganancias_eur']
    """
    total_gan = df_ganancias['ganancia_perdida_eur'].sum() if not df_ganancias.empty else 0.0
    restante = total_gan
    irpf = 0.0

    # Definición de tramos
    tramos = [
        (6000.0, 0.19),
        (50000.0 - 6000.0, 0.21),
        (200000.0 - 50000.0, 0.23),
        (float('inf'), 0.26)
    ]

    for limite, tipo in tramos:
        if restante <= 0:
            break
        aplicable = min(restante, limite)
        irpf += aplicable * tipo
        restante -= aplicable

    return pd.DataFrame([{
        'base_imponible_eur': round(total_gan, 2),
        'irpf_ganancias_eur': round(irpf, 2)
    }])


