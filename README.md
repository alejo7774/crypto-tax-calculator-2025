# 📊 Calculadora de Ganancias/Pérdidas Cripto 2024

Esta aplicación permite calcular automáticamente tus **ganancias y pérdidas patrimoniales** por operaciones con criptomonedas y generar un informe fiscal compatible con el **IRPF en España** (modelo 100).

Está diseñada para **Binance y Koinly**, y genera un **archivo Excel con instrucciones, importes y casillas** preparadas para declarar en 2025 (ejercicio 2024).

---

## 🚀 Funcionalidades principales

✅ Carga de archivos CSV desde Binance o Koinly  
✅ Análisis de ganancias patrimoniales (método FIFO)  
✅ Cálculo de ingresos por staking, airdrops, intereses  
✅ Estimación del IRPF (base del ahorro + capital mobiliario)  
✅ Generación automática de un Excel con:
- Detalle de operaciones
- Totales
- Hoja de observaciones fiscales

---

## 📁 Estructura del proyecto

calculator_crypto/
│
├── app.py # App principal con Streamlit
├── requirements.txt # Dependencias necesarias
│
├── logic/ # Módulo con la lógica
│ ├── init.py
│ ├── transformers.py # Estándar de importación CSV
│ ├── tax_calculator.py # FIFO + cálculo IRPF
│ ├── api_pricing.py # Precios históricos
│ ├── report_generator.py # Generación de Excel
│ └── _legacy_transformers_adapted.py # Soporte extra
│
└── .gitignore # Ignora .venv, pycache, .pyc, etc.

---

## ⚙️ Requisitos y dependencias

Instala Python 3.10+ y luego usa:

```bash
pip install -r requirements.txt

Contenido sugerido en requirements.txt:

streamlit
pandas
xlsxwriter
yfinance

🧪 Instalación y ejecución
1. Clona el repositorio:
git clone https://github.com/tu_usuario/crypto-tax-calculator-2024.git
cd crypto-tax-calculator-2024

2. Instala las dependencias:
pip install -r requirements.txt

3. Ejecuta la app:
streamlit run app.py

📷 Capturas de pantalla
A continuación, algunos ejemplos de funcionamiento:

➕ Carga del CSV

📈 Ganancias patrimoniales (resumen)
🧾 Informe fiscal en Excel


📝 Resultado final
Se genera un archivo .xlsx con:
Detalle de ventas con ganancias/pérdidas
Ingresos cripto declarables
Totales y estimación IRPF
Instrucciones claras para el IRPF español

⚖️ Licencia
MIT License – Puedes usar, modificar o adaptarlo libremente.



