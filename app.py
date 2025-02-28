import streamlit as st
import pandas as pd
import requests
from pmdarima import auto_arima
import matplotlib.pyplot as plt
from datetime import datetime

# Configuración inicial de Airtable
AIRTABLE_API_KEY = st.secrets["airtable_api_key"]  # Reemplaza con tu Personal Access Token (PAT)
AIRTABLE_BASE_ID = st.secrets["airtable_base_id"]  # Reemplaza con tu Base ID
AIRTABLE_TABLE_NAME = "Inventory"  # Nombre de la tabla en Airtable
AIRTABLE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"

# Función para realizar solicitudes HTTP a Airtable
def airtable_request(method, url, data=None):
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif method == "PATCH":
            response = requests.patch(url, json=data, headers=headers)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        
        response.raise_for_status()  # Lanza una excepción si hay un error HTTP
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectarse a Airtable: {e}")
        return None

# Función para cargar datos desde Airtable
def load_data_from_airtable():
    records = []
    offset = None
    while True:
        params = {"offset": offset} if offset else {}
        response = airtable_request("GET", AIRTABLE_URL, params=params)
        if not response:
            return None
        
        records.extend(response.get("records", []))
        offset = response.get("offset")
        if not offset:
            break
    
    # Convertir los datos de Airtable a un DataFrame
    data = [
        {
            "Fecha": record["fields"].get("Fecha"),
            "Producto": record["fields"].get("Producto"),
            "Ventas": record["fields"].get("Ventas"),
            "Stock": record["fields"].get("Stock"),
            "Fecha_Vencimiento": record["fields"].get("Fecha_Vencimiento"),
        }
        for record in records
    ]
    df = pd.DataFrame(data)
    
    if df.empty:
        st.warning("No hay datos disponibles en Airtable.")
        return None
    
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df['Fecha_Vencimiento'] = pd.to_datetime(df['Fecha_Vencimiento'], errors='coerce')
    return df

# Función para añadir nuevos registros a Airtable
def add_record_to_airtable(fecha, producto, ventas, stock, fecha_vencimiento):
    payload = {
        "records": [
            {
                "fields": {
                    "Fecha": fecha,
                    "Producto": producto,
                    "Ventas": ventas,
                    "Stock": stock,
                    "Fecha_Vencimiento": fecha_vencimiento
                }
            }
        ]
    }
    response = airtable_request("POST", AIRTABLE_URL, data=payload)
    if response and "records" in response:
        st.success("Datos guardados correctamente en Airtable.")
        return True
    else:
        st.error("Error al guardar los datos en Airtable.")
        return False

# Función para obtener el stock actual de un producto
def get_current_stock(producto):
    response = airtable_request("GET", AIRTABLE_URL, params={"filterByFormula": f"{{Producto}} = '{producto}'"})
    if not response or "records" not in response:
        return None
    
    records = response["records"]
    if not records:
        return None
    
    # Obtener el último registro del producto ordenado por fecha
    sorted_records = sorted(records, key=lambda x: x["fields"].get("Fecha", ""), reverse=True)
    return sorted_records[0]["fields"].get("Stock")

# Pronóstico de demanda
def forecast_demand(data, product, days=30):
    sales = data[data['Producto'] == product]['Ventas'].values
    if len(sales) < 30:
        return None, None, f"Se recomiendan al menos 30 días de datos históricos para un pronóstico fiable (disponibles: {len(sales)})."
    try:
        model = auto_arima(sales, seasonal=False, suppress_warnings=True, stepwise=True)
        forecast = model.predict(n_periods=days, return_conf_int=True)
        predictions, conf_int = forecast[0], forecast[1]
        return predictions, conf_int, None
    except ValueError as e:
        return None, None, f"Error en el modelo: datos no estacionarios o insuficientes. Prueba con más datos históricos. ({e})"
    except Exception as e:
        return None, None, f"Error en el modelo de pronóstico: {e}"

# Recomendaciones de reabastecimiento
def suggest_restock(current_stock, predicted_demand, threshold, buffer=1.2):
    predicted_stock = current_stock - predicted_demand
    if predicted_stock < threshold:
        restock_amount = (predicted_demand * buffer) - current_stock
        return max(restock_amount, 0)
    return 0

# Configuración inicial de Streamlit
st.set_page_config(page_title="Inventory Insight - Farmacia Galeno", layout="wide")

# Gestión de estado de sesión
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Login (opcional, puedes integrar autenticación externa si es necesario)
if not st.session_state.logged_in:
    st.sidebar.header("Iniciar Sesión")
    username = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Login"):
        # Aquí puedes implementar lógica de autenticación si lo deseas
        st.session_state.logged_in = True
        st.sidebar.success("¡Inicio de sesión exitoso!")
else:
    st.title("Inventory Insight - Gestión Inteligente de Inventarios")
    st.sidebar.header("Configuración")
    
    # Formulario para añadir nueva venta
    with st.sidebar.expander("Añadir Nueva Venta"):
        fecha = st.date_input("Fecha", value=datetime.today())
        producto = st.text_input("Producto")
        ventas = st.number_input("Ventas", min_value=0, value=0)
        
        current_stock = get_current_stock(producto)
        if current_stock is not None:
            st.write(f"Stock actual de {producto}: {current_stock}")
            stock_inicial = current_stock
        else:
            stock_inicial = st.number_input("Stock Inicial (solo para productos nuevos)", min_value=0, value=100)
        
        fecha_vencimiento = st.date_input("Fecha de Vencimiento", value=datetime.today().replace(year=datetime.today().year + 1))
        
        if st.button("Guardar Venta"):
            success = add_record_to_airtable(
                fecha.strftime('%Y-%m-%d'),
                producto,
                ventas,
                stock_inicial - ventas,
                fecha_vencimiento.strftime('%Y-%m-%d')
            )
            if success:
                st.experimental_rerun()

    # Cargar datos desde Airtable
    data = load_data_from_airtable()

    if data is not None:
        st.sidebar.success("Datos cargados correctamente desde Airtable")
        products = data['Producto'].unique()
        selected_product = st.sidebar.selectbox("Selecciona un Producto", products)

        # Filtrar datos del producto
        product_data = data[data['Producto'] == selected_product]

        # Pronóstico de demanda
        st.subheader(f"Análisis para: {selected_product}")
        st.write("### Pronóstico de Demanda")
        with st.expander("¿Qué significa esto?"):
            st.write("Predice ventas futuras con un modelo estadístico (ARIMA). Línea azul: pasado; rojo punteado: futuro; sombra: intervalo de confianza.")

        forecast_days = st.sidebar.slider("Días de Pronóstico", 7, 90, 30)
        forecast, conf_int, error = forecast_demand(data, selected_product, forecast_days)
        if forecast is not None:
            forecast_dates = pd.date_range(start=product_data['Fecha'].max() + pd.Timedelta(days=1), periods=forecast_days, freq='D')
            forecast_df = pd.DataFrame({'Fecha': forecast_dates, 'Pronóstico': forecast, 'Lower_CI': conf_int[:, 0], 'Upper_CI': conf_int[:, 1]})

            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(product_data['Fecha'], product_data['Ventas'], label='Ventas Históricas', color='blue')
            ax.plot(forecast_df['Fecha'], forecast_df['Pronóstico'], label='Pronóstico', color='red', linestyle='--')
            ax.fill_between(forecast_df['Fecha'], forecast_df['Lower_CI'], forecast_df['Upper_CI'], color='red', alpha=0.1, label='Intervalo de Confianza')
            ax.legend()
            ax.set_title(f"Pronóstico de Demanda para {selected_product}")
            ax.set_xlabel("Fecha")
            ax.set_ylabel("Ventas")
            st.pyplot(fig)
        else:
            st.warning(error)

        # Gestión de inventario
        st.write("### Gestión de Inventario")
        with st.expander("¿Qué significa esto?"):
            st.write("Muestra stock actual, demanda futura, stock esperado y cuánto reabastecer.")

        current_stock = product_data['Stock'].iloc[-1] if not product_data.empty else 0
        predicted_demand = forecast.sum() if forecast is not None else 0
        predicted_stock = current_stock - predicted_demand
        stock_threshold = st.sidebar.number_input("Umbral de Stock Mínimo", min_value=0, value=10)
        restock_amount = suggest_restock(current_stock, predicted_demand, stock_threshold)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Stock Actual", int(current_stock))
        col2.metric("Demanda Pronosticada", int(predicted_demand))
        col3.metric("Stock Esperado", int(predicted_stock))
        col4.metric("Recomendación de Reabastecimiento", int(restock_amount))

        if predicted_stock < stock_threshold:
            st.warning(f"¡Alerta! Stock esperado ({int(predicted_stock)}) por debajo del umbral ({stock_threshold}). Reabastece {int(restock_amount)} unidades.")

        # Control de vencimientos
        st.write("### Control de Vencimientos")
        with st.expander("¿Qué significa esto?"):
            expiration_days = st.sidebar.slider("Días para Alerta de Vencimiento", 7, 90, 30)
            st.write(f"Identifica productos que vencerán en {expiration_days} días para priorizar acciones.")

        expiration_data = product_data[['Fecha_Vencimiento', 'Stock']].dropna()
        expiration_threshold = pd.Timestamp.today() + pd.Timedelta(days=expiration_days)

        if not expiration_data.empty:
            expiring_soon = expiration_data[
                expiration_data['Fecha_Vencimiento'] <= expiration_threshold
            ]
            if not expiring_soon.empty:
                st.write("Productos próximos a vencer:")
                st.dataframe(expiring_soon)
            else:
                st.info("No hay productos próximos a vencer en el período seleccionado.")
        else:
            st.info("No hay datos de vencimiento disponibles para este producto.")

    # Botón para cerrar sesión
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.sidebar.success("Sesión cerrada")
        st.experimental_rerun()
