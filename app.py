import streamlit as st
import pandas as pd
import numpy as np
from pmdarima import auto_arima
import matplotlib.pyplot as plt
import sqlite3
import os
from datetime import datetime
import plotly.express as px
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from io import BytesIO
import bcrypt

# Configuración inicial
st.set_page_config(page_title="Inventory Insight - Ferretería Galeno", layout="wide")
st.title("Inventory Insight - Ferretería Galeno")

# Archivos y base de datos
CSV_FILE = "inventario_ferreteria.csv"
HISTORIAL_FILE = "historial_cambios.csv"
VENTAS_FILE = "ventas.csv"
DB_FILE = "inventory.db"

# Datos de demostración para el CSV inicial
DEMO_DATA = pd.DataFrame({
    "ID": ["001", "002", "003", "004", "005"],
    "Producto": ["Taladro Eléctrico", "Pintura Blanca", "Tornillos 1/4", "Martillo", "Cable 10m"],
    "Categoría": ["Herramientas", "Pinturas", "Materiales", "Herramientas", "Electricidad"],
    "Cantidad": [10, 5, 100, 8, 15],
    "Precio": [150.50, 25.75, 0.10, 12.00, 8.90],
    "Proveedor": ["Bosch", "Sherwin", "Genérico", "Truper", "Voltex"],
    "Última Actualización": ["2025-03-02 10:00:00", "2025-03-01 15:30:00", "2025-02-28 09:15:00", 
                            "2025-03-01 12:00:00", "2025-03-02 14:20:00"]
})

# Función para conectar a la base de datos SQLite
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Función para inicializar la base de datos SQLite
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Crear tabla de inventario
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            Fecha TEXT,
            Producto TEXT, 
            Ventas INTEGER,
            Stock INTEGER,
            Fecha_Vencimiento TEXT
        )
    ''')
    
    # Crear tabla de usuarios
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    ''')
    
    # Crear usuario administrador por defecto si no existe
    default_user = 'admin'
    default_password = 'admin123'
    hashed_pw = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt())
    c.execute("SELECT COUNT(*) FROM users WHERE username = ?", (default_user,))
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (default_user, hashed_pw))
    
    # Insertar datos de muestra si la tabla está vacía
    c.execute("SELECT COUNT(*) FROM inventory")
    if c.fetchone()[0] == 0:
        today = pd.Timestamp.today()
        dates = pd.date_range(start=today - pd.Timedelta(days=30), end=today - pd.Timedelta(days=1), freq='D')
        products = ['Paracetamol', 'Ibuprofeno']
        sample_data = []
        for i, date in enumerate(dates):
            for product in products:
                ventas = [10, 12, 15, 8, 9, 11, 14, 13, 10, 12, 15, 8, 9, 11, 14, 13, 10, 12, 15, 8, 9, 11, 14, 13, 10, 12, 15, 8, 9, 11][i] if product == 'Paracetamol' else [5, 6, 7, 4, 5, 6, 8, 7, 5, 6, 7, 4, 5, 6, 8, 7, 5, 6, 7, 4, 5, 6, 8, 7, 5, 6, 7, 4, 5, 6][i]
                stock = [100, 90, 78, 63, 55, 46, 35, 21, 11, 1, 91, 76, 68, 59, 48, 34, 24, 14, 2, 87, 79, 70, 59, 45, 35, 25, 13, 5, 96, 87][i] if product == 'Paracetamol' else [80, 75, 69, 65, 60, 55, 47, 40, 35, 30, 74, 70, 65, 60, 52, 45, 40, 35, 29, 75, 70, 65, 57, 50, 43, 38, 31, 27, 72, 67][i]
                fecha_venc = '2025-06-01' if product == 'Paracetamol' else '2025-07-15'
                sample_data.append((date.strftime('%Y-%m-%d'), product, ventas, stock, fecha_venc))
        
        c.executemany("INSERT INTO inventory (Fecha, Producto, Ventas, Stock, Fecha_Vencimiento) VALUES (?, ?, ?, ?, ?)", sample_data)
    
    conn.commit()
    conn.close()

# Función para verificar login con bcrypt
def check_login(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result:
        stored_password = result['password']
        return bcrypt.checkpw(password.encode('utf-8'), stored_password)
    return False

# Funciones para manejar el inventario en CSV
def cargar_inventario():
    if not os.path.exists(CSV_FILE):
        DEMO_DATA.to_csv(CSV_FILE, index=False)
        return DEMO_DATA.copy()
    df = pd.read_csv(CSV_FILE)
    df["Precio"] = df["Precio"].round(2)
    return df

def guardar_inventario(df):
    df["Precio"] = df["Precio"].round(2)
    df.to_csv(CSV_FILE, index=False)

def cargar_ventas():
    if os.path.exists(VENTAS_FILE):
        df = pd.read_csv(VENTAS_FILE)
        df["Precio Unitario"] = df["Precio Unitario"].round(2)
        df["Total"] = df["Total"].round(2)
        return df
    return pd.DataFrame(columns=["Fecha", "ID", "Producto", "Cantidad Vendida", "Precio Unitario", "Total", "Usuario"])

def guardar_ventas(df):
    df["Precio Unitario"] = df["Precio Unitario"].round(2)
    df["Total"] = df["Total"].round(2)
    df.to_csv(VENTAS_FILE, index=False)

def registrar_cambio(accion, id_producto, usuario):
    historial = pd.DataFrame({
        "Fecha": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Acción": [accion],
        "ID Producto": [id_producto],
        "Usuario": [usuario]
    })
    if os.path.exists(HISTORIAL_FILE):
        historial_existente = pd.read_csv(HISTORIAL_FILE)
        historial = pd.concat([historial_existente, historial], ignore_index=True)
    historial.to_csv(HISTORIAL_FILE, index=False)

# Funciones para datos SQLite
def load_data_from_db():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM inventory", conn)
    conn.close()
    if df.empty:
        st.warning("No hay datos en la base de datos.")
        return None
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    df['Fecha_Vencimiento'] = pd.to_datetime(df['Fecha_Vencimiento'], errors='coerce')
    original_len = len(df)
    df.dropna(subset=['Fecha', 'Ventas', 'Stock', 'Fecha_Vencimiento'], inplace=True)
    if len(df) < original_len:
        st.warning(f"Se eliminaron {original_len - len(df)} filas con fechas o datos clave inválidos.")
    return df

def get_current_stock(producto):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT Stock FROM inventory WHERE Producto = ? ORDER BY Fecha DESC LIMIT 1", (producto,))
    result = c.fetchone()
    conn.close()
    return result['Stock'] if result else None

def add_sale(fecha, producto, ventas, stock_inicial, fecha_vencimiento, is_restock=False):
    conn = get_db_connection()
    c = conn.cursor()
    current_stock = get_current_stock(producto)
    if is_restock:
        new_stock = (current_stock or 0) + stock_inicial
        ventas = 0
    else:
        if current_stock is None:
            new_stock = stock_inicial - ventas
        else:
            new_stock = current_stock - ventas
        if new_stock < 0:
            st.warning(f"No se puede registrar la venta: las ventas ({ventas}) exceden el stock disponible ({current_stock or stock_inicial}).")
            conn.close()
            return False
    c.execute("INSERT INTO inventory (Fecha, Producto, Ventas, Stock, Fecha_Vencimiento) VALUES (?, ?, ?, ?, ?)",
              (fecha, producto, ventas, new_stock, fecha_vencimiento))
    conn.commit()
    conn.close()
    return True

def preprocess_data(df):
    return {product: group for product, group in df.groupby('Producto')}

def forecast_demand(data, product, days=30):
    sales = data[product]['Ventas'].values
    if len(sales) < 30:
        return None, None, f"Se recomiendan al menos 30 días de datos históricos para un pronóstico fiable (disponibles: {len(sales)})."
    try:
        model = auto_arima(sales, seasonal=False, suppress_warnings=True, stepwise=True)
        forecast = model.predict(n_periods=days, return_conf_int=True)
        predictions, conf_int = forecast[0], forecast[1]
        return predictions, conf_int, None
    except Exception as e:
        return None, None, f"Error en el modelo de pronóstico: {e}"

def suggest_restock(current_stock, predicted_demand, threshold, buffer=1.2):
    predicted_stock = current_stock - predicted_demand
    if predicted_stock < threshold:
        restock_amount = (predicted_demand * buffer) - current_stock
        return max(restock_amount, 0)
    return 0

# Inicializar la base de datos
init_db()

# Gestión de estado de sesión
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.sidebar.header("Iniciar Sesión")
    username = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type="password")
    if st.sidebar.button("Login"):
        if check_login(username, password):
            st.session_state.logged_in = True
            st.sidebar.success("¡Inicio de sesión exitoso!")
        else:
            st.sidebar.error("Usuario o contraseña incorrectos")
else:
    # Cargar datos
    inventario = cargar_inventario()
    ventas_csv = cargar_ventas()
    data_db = load_data_from_db()

    # Barra lateral con menú y configuraciones
    menu = st.sidebar.selectbox(
        "Menú",
        ["Ver Inventario", "Registrar Ventas", "Cargar CSV", "Agregar Producto", "Buscar Producto", 
         "Editar Producto", "Eliminar Producto", "Reporte", "Historial", "Análisis de Demanda"]
    )
    st.sidebar.write(f"Usuario: {st.session_state.username if 'username' in st.session_state else 'admin'}")

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.session_state.pop("username", None)
        st.sidebar.success("Sesión cerrada")
        st.experimental_rerun()

    # Configuraciones para análisis de demanda
    if menu == "Análisis de Demanda":
        st.sidebar.header("Configuración de Análisis")
        forecast_days = st.sidebar.slider("Días de Pronóstico", 7, 90, 30)
        stock_threshold = st.sidebar.number_input("Umbral de Stock Mínimo", min_value=0, value=10)
        expiration_days = st.sidebar.slider("Días para Alerta de Vencimiento", 7, 90, 30)

    # Formularios para añadir venta y reabastecimiento
    with st.sidebar.expander("Añadir Nueva Venta"):
        fecha = st.date_input("Fecha", value=datetime.today(), key="venta_fecha")
        producto = st.text_input("Producto", key="venta_producto")
        ventas = st.number_input("Ventas", min_value=0, value=0, key="venta_ventas")
        current_stock = get_current_stock(producto)
        if current_stock is not None:
            st.write(f"Stock actual de {producto}: {current_stock}")
            stock_inicial = current_stock
        else:
            stock_inicial = st.number_input("Stock Inicial (solo para productos nuevos)", min_value=0, value=100, key="venta_stock")
        fecha_vencimiento = st.date_input("Fecha de Vencimiento", value=datetime.today().replace(year=datetime.today().year + 1), key="venta_vencimiento")
        if st.button("Guardar Venta"):
            if producto.strip() == "":
                st.error("El campo 'Producto' no puede estar vacío.")
            elif ventas > (current_stock if current_stock is not None else stock_inicial):
                st.error(f"Las ventas ({ventas}) no pueden exceder el stock disponible ({current_stock if current_stock is not None else stock_inicial}).")
            else:
                success = add_sale(fecha.strftime('%Y-%m-%d'), producto, ventas, stock_inicial, fecha_vencimiento.strftime('%Y-%m-%d'), is_restock=False)
                if success:
                    st.success(f"Venta de {producto} guardada. Stock restante: {get_current_stock(producto)}")
                    st.experimental_rerun()

    with st.sidebar.expander("Reabastecer Stock"):
        producto_restock = st.text_input("Producto a reabastecer", key="restock_producto")
        cantidad = st.number_input("Cantidad a añadir", min_value=0, value=0, key="restock_cantidad")
        fecha_restock = st.date_input("Fecha de Reabastecimiento", value=datetime.today(), key="restock_fecha")
        fecha_venc_restock = st.date_input("Nueva Fecha de Vencimiento", value=datetime.today().replace(year=datetime.today().year + 1), key="restock_vencimiento")
        if st.button("Reabastecer"):
            if producto_restock.strip() == "":
                st.error("El campo 'Producto' no puede estar vacío.")
            else:
                success = add_sale(fecha_restock.strftime('%Y-%m-%d'), producto_restock, 0, cantidad, fecha_venc_restock.strftime('%Y-%m-%d'), is_restock=True)
                if success:
                    st.success(f"Stock de {producto_restock} aumentado a {get_current_stock(producto_restock)}")
                    st.experimental_rerun()

    # Opciones del menú
    if menu == "Ver Inventario":
        st.subheader("Inventario Actual")
        if inventario.empty:
            st.warning("El inventario está vacío.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                categoria_filtro = st.selectbox("Filtrar por Categoría", ["Todas"] + inventario["Categoría"].unique().tolist())
            with col2:
                proveedor_filtro = st.selectbox("Filtrar por Proveedor", ["Todos"] + inventario["Proveedor"].unique().tolist())
            
            inventario_filtrado = inventario
            if categoria_filtro != "Todas":
                inventario_filtrado = inventario_filtrado[inventario_filtrado["Categoría"] == categoria_filtro]
            if proveedor_filtro != "Todos":
                inventario_filtrado = inventario_filtrado[inventario_filtrado["Proveedor"] == proveedor_filtro]
            
            def color_stock(row):
                if row["Cantidad"] == 0:
                    return ['background-color: red'] * len(row)
                elif row["Cantidad"] < 5:
                    return ['background-color: yellow'] * len(row)
                return [''] * len(row)
            
            st.dataframe(inventario_filtrado.style.apply(color_stock, axis=1).format({"Precio": "{:.2f}"}))
            st.download_button(
                label="Descargar Inventario como CSV",
                data=inventario_filtrado.to_csv(index=False),
                file_name=f"inventario_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    elif menu == "Registrar Ventas":
        st.subheader("Registrar Ventas del Día")
        inventario["ID"] = inventario["ID"].astype(str)
        productos_disponibles = [f"{row['Producto']} (ID: {row['ID']}, Stock: {row['Cantidad']})" 
                                for _, row in inventario.iterrows() if row['Cantidad'] > 0]
        
        with st.form(key="ventas_form"):
            if productos_disponibles:
                producto_seleccionado = st.selectbox("Selecciona un Producto", productos_disponibles)
                cantidad_vendida = st.number_input("Cantidad Vendida", min_value=1, step=1)
                submit_venta = st.form_submit_button(label="Registrar Venta")

                if submit_venta:
                    try:
                        id_venta = producto_seleccionado.split("ID: ")[1].split(",")[0].strip()
                        if id_venta in inventario["ID"].values:
                            producto = inventario[inventario["ID"] == id_venta].iloc[0]
                            if producto["Cantidad"] >= cantidad_vendida:
                                inventario.loc[inventario["ID"] == id_venta, "Cantidad"] -= cantidad_vendida
                                inventario.loc[inventario["ID"] == id_venta, "Última Actualización"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                guardar_inventario(inventario)

                                total_venta = cantidad_vendida * producto["Precio"]
                                nueva_venta = pd.DataFrame({
                                    "Fecha": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                    "ID": [id_venta],
                                    "Producto": [producto["Producto"]],
                                    "Cantidad Vendida": [cantidad_vendida],
                                    "Precio Unitario": [producto["Precio"]],
                                    "Total": [total_venta],
                                    "Usuario": [st.session_state.username if 'username' in st.session_state else 'admin']
                                })
                                ventas_csv = pd.concat([ventas_csv, nueva_venta], ignore_index=True)
                                guardar_ventas(ventas_csv)

                                registrar_cambio("Venta", id_venta, st.session_state.username if 'username' in st.session_state else 'admin')
                                st.success(f"Venta registrada: {cantidad_vendida} de '{producto['Producto']}' por ${total_venta:.2f}")
                                inventario = cargar_inventario()
                            else:
                                st.error(f"No hay suficiente stock. Disponible: {producto['Cantidad']}")
                        else:
                            st.error(f"El ID '{id_venta}' no se encontró en el inventario.")
                    except IndexError:
                        st.error("Error al procesar el producto seleccionado.")
            else:
                st.warning("No hay productos en stock para vender.")

        st.subheader("Ventas Registradas Hoy")
        hoy = datetime.now().strftime("%Y-%m-%d")
        ventas_hoy = ventas_csv[ventas_csv["Fecha"].str.startswith(hoy)]
        if not ventas_hoy.empty:
            st.dataframe(ventas_hoy.style.format({"Precio Unitario": "{:.2f}", "Total": "{:.2f}"}))
            total_dia = ventas_hoy["Total"].sum()
            st.write(f"**Total de Ventas del Día:** ${total_dia:.2f}")
        else:
            st.info("No hay ventas registradas para hoy.")

    elif menu == "Cargar CSV":
        st.subheader("Cargar Inventario desde CSV")
        uploaded_file = st.file_uploader("Selecciona un archivo CSV", type=["csv"])
        if uploaded_file is not None:
            try:
                nuevo_inventario = pd.read_csv(uploaded_file)
                columnas_esperadas = ["ID", "Producto", "Categoría", "Cantidad", "Precio", "Proveedor", "Última Actualización"]
                if not all(col in nuevo_inventario.columns for col in columnas_esperadas):
                    st.error("El CSV debe contener las columnas: ID, Producto, Categoría, Cantidad, Precio, Proveedor, Última Actualización")
                else:
                    if nuevo_inventario["ID"].duplicated().any():
                        st.error("El CSV contiene IDs duplicados.")
                    elif nuevo_inventario["Cantidad"].lt(0).any() or nuevo_inventario["Precio"].lt(0).any():
                        st.error("Cantidad y Precio no pueden ser negativos.")
                    else:
                        nuevo_inventario["Precio"] = nuevo_inventario["Precio"].round(2)
                        st.write("Vista previa del CSV:")
                        st.dataframe(nuevo_inventario.style.format({"Precio": "{:.2f}"}))
                        if st.button("Confirmar Carga"):
                            inventario = nuevo_inventario.copy()
                            guardar_inventario(inventario)
                            registrar_cambio("Cargar CSV", "Todos", st.session_state.username if 'username' in st.session_state else 'admin')
                            st.success("Inventario actualizado desde el CSV con éxito!")
            except Exception as e:
                st.error(f"Error al procesar el archivo: {str(e)}")
        st.info("Asegúrate de que el CSV tenga el formato correcto.")

    elif menu == "Agregar Producto":
        st.subheader("Agregar Productos desde CSV")
        uploaded_file = st.file_uploader("Selecciona un archivo CSV con nuevos productos", type=["csv"])
        if uploaded_file is not None:
            try:
                nuevos_productos = pd.read_csv(uploaded_file)
                columnas_esperadas = ["ID", "Producto", "Categoría", "Cantidad", "Precio", "Proveedor", "Última Actualización"]
                if not all(col in nuevos_productos.columns for col in columnas_esperadas):
                    st.error("El CSV debe contener las columnas: ID, Producto, Categoría, Cantidad, Precio, Proveedor, Última Actualización")
                else:
                    if nuevos_productos["ID"].duplicated().any():
                        st.error("El CSV contiene IDs duplicados entre sí.")
                    elif nuevos_productos["ID"].isin(inventario["ID"]).any():
                        st.error("Algunos IDs en el CSV ya existen en el inventario.")
                    elif nuevos_productos["Cantidad"].lt(0).any() or nuevos_productos["Precio"].lt(0).any():
                        st.error("Cantidad y Precio no pueden ser negativos.")
                    else:
                        nuevos_productos["Precio"] = nuevos_productos["Precio"].round(2)
                        st.write("Vista previa de los nuevos productos:")
                        st.dataframe(nuevos_productos.style.format({"Precio": "{:.2f}"}))
                        if st.button("Confirmar Agregado"):
                            inventario = pd.concat([inventario, nuevos_productos], ignore_index=True)
                            guardar_inventario(inventario)
                            for id_prod in nuevos_productos["ID"]:
                                registrar_cambio("Agregar", id_prod, st.session_state.username if 'username' in st.session_state else 'admin')
                            st.success(f"{len(nuevos_productos)} producto(s) agregado(s) con éxito!")
            except Exception as e:
                st.error(f"Error al procesar el archivo: {str(e)}")
        st.info("Asegúrate de que el CSV tenga el formato correcto y IDs únicos.")

    elif menu == "Buscar Producto":
        st.subheader("Buscar Producto")
        busqueda = st.text_input("Ingrese ID, Nombre o Proveedor")
        if busqueda:
            resultado = inventario[
                inventario["ID"].str.contains(busqueda, case=False, na=False) |
                inventario["Producto"].str.contains(busqueda, case=False, na=False) |
                inventario["Proveedor"].str.contains(busqueda, case=False, na=False)
            ]
            if not resultado.empty:
                st.dataframe(resultado.style.format({"Precio": "{:.2f}"}))
            else:
                st.warning("No se encontraron productos con ese criterio.")

    elif menu == "Editar Producto":
        st.subheader("Editar Producto")
        id_editar = st.text_input("Ingrese el ID del producto a editar")
        if id_editar and id_editar in inventario["ID"].values:
            producto = inventario[inventario["ID"] == id_editar].iloc[0]
            with st.form(key="editar_form"):
                nombre = st.text_input("Nombre del Producto", value=producto["Producto"])
                categoria = st.selectbox("Categoría", ["Herramientas", "Materiales", "Pinturas", "Electricidad", "Otros"], 
                                       index=["Herramientas", "Materiales", "Pinturas", "Electricidad", "Otros"].index(producto["Categoría"]))
                cantidad = st.number_input("Cantidad", min_value=0, step=1, value=int(producto["Cantidad"]))
                precio = st.number_input("Precio Unitario", min_value=0.0, step=0.01, value=float(producto["Precio"]), format="%.2f")
                proveedor = st.text_input("Proveedor", value=producto["Proveedor"])
                submit_edit = st.form_submit_button(label="Guardar Cambios")

                if submit_edit:
                    inventario.loc[inventario["ID"] == id_editar, ["Producto", "Categoría", "Cantidad", "Precio", "Proveedor", "Última Actualización"]] = \
                        [nombre, categoria, cantidad, round(precio, 2), proveedor, datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                    guardar_inventario(inventario)
                    registrar_cambio("Editar", id_editar, st.session_state.username if 'username' in st.session_state else 'admin')
                    st.success(f"Producto con ID '{id_editar}' actualizado con éxito!")
        elif id_editar:
            st.error("ID no encontrado en el inventario.")

    elif menu == "Eliminar Producto":
        st.subheader("Eliminar Producto")
        id_eliminar = st.text_input("Ingrese el ID del producto a eliminar")
        if id_eliminar and id_eliminar in inventario["ID"].values:
            producto = inventario[inventario["ID"] == id_eliminar].iloc[0]
            st.write(f"Producto a eliminar: {producto['Producto']} (Cantidad: {producto['Cantidad']})")
            confirmar = st.button("Confirmar Eliminación")
            if confirmar:
                inventario = inventario[inventario["ID"] != id_eliminar]
                guardar_inventario(inventario)
                registrar_cambio("Eliminar", id_eliminar, st.session_state.username if 'username' in st.session_state else 'admin')
                st.success(f"Producto con ID '{id_eliminar}' eliminado con éxito!")
        elif id_eliminar:
            st.error("ID no encontrado en el inventario.")

    elif menu == "Reporte":
        st.subheader("Reporte del Inventario")
        if inventario.empty:
            st.warning("No hay datos para generar un reporte.")
        else:
            total_valor = (inventario["Cantidad"] * inventario["Precio"]).sum()
            bajo_stock = inventario[inventario["Cantidad"] < 5]
            st.write(f"**Valor Total del Inventario:** ${total_valor:.2f}")
            st.write(f"**Productos con Bajo Stock (menos de 5 unidades):** {len(bajo_stock)}")
            if not bajo_stock.empty:
                st.dataframe(bajo_stock.style.format({"Precio": "{:.2f}"}))
            
            fig = px.bar(inventario.groupby("Categoría")["Cantidad"].sum().reset_index(), 
                        x="Categoría", y="Cantidad", title="Cantidad por Categoría")
            st.plotly_chart(fig)

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            elements = []
            title_style = ParagraphStyle(
                name='Title',
                fontSize=14,
                leading=16,
                alignment=1,
                spaceAfter=12
            )
            elements.append(Paragraph("Reporte de Inventario", title_style))
            data = [inventario.columns.tolist()] + inventario.values.tolist()
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            doc.build(elements)
            st.download_button(
                label="Descargar Reporte como PDF",
                data=buffer.getvalue(),
                file_name=f"reporte_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="application/pdf"
            )

    elif menu == "Historial":
        st.subheader("Historial de Cambios")
        if os.path.exists(HISTORIAL_FILE):
            historial = pd.read_csv(HISTORIAL_FILE)
            st.dataframe(historial.sort_values("Fecha", ascending=False))
        else:
            st.info("No hay historial de cambios registrado aún.")

    elif menu == "Análisis de Demanda" and data_db is not None:
        st.subheader("Análisis de Demanda")
        preprocessed_data = preprocess_data(data_db)
        products = list(preprocessed_data.keys())
        selected_product = st.selectbox("Selecciona un Producto", products)

        product_data = preprocessed_data[selected_product]

        st.write("### Pronóstico de Demanda")
        with st.expander("¿Qué significa esto?"):
            st.write("Predice ventas futuras con un modelo estadístico (ARIMA). Línea azul: pasado; rojo punteado: futuro; sombra: intervalo de confianza.")
        
        forecast, conf_int, error = forecast_demand(preprocessed_data, selected_product, forecast_days)
        if forecast is not None:
            if product_data.empty or pd.isna(product_data['Fecha'].max()):
                st.warning(f"No hay datos históricos válidos para {selected_product}.")
            else:
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

        st.write("### Gestión de Inventario")
        with st.expander("¿Qué significa esto?"):
            st.write("Muestra stock actual, demanda futura, stock esperado y cuánto reabastecer.")
        
        current_stock = product_data['Stock'].iloc[-1] if not product_data.empty else 0
        predicted_demand = forecast.sum() if forecast is not None else 0
        predicted_stock = current_stock - predicted_demand
        restock_amount = suggest_restock(current_stock, predicted_demand, stock_threshold)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Stock Actual", int(current_stock))
        col2.metric("Demanda Pronosticada", int(predicted_demand))
        col3.metric("Stock Esperado", int(predicted_stock))
        col4.metric("Recomendación de Reabastecimiento", int(restock_amount))

        if predicted_stock < stock_threshold:
            st.warning(f"¡Alerta! Stock esperado ({int(predicted_stock)}) por debajo del umbral ({stock_threshold}). Reabastece {int(restock_amount)} unidades.")

        st.write("### Control de Vencimientos")
        with st.expander("¿Qué significa esto?"):
            st.write(f"Identifica productos que vencerán en {expiration_days} días.")
        
        expiration_data = product_data[['Fecha_Vencimiento', 'Stock']].dropna()
        expiration_threshold = pd.Timestamp.today() + pd.Timedelta(days=expiration_days)

        if expiration_data.empty:
            expiring_soon = pd.DataFrame(columns=['Fecha_Vencimiento', 'Stock'])
        else:
            expiring_soon = expiration_data[expiration_data['Fecha_Vencimiento'] <= expiration_threshold]

        if not expiring_soon.empty:
            st.write("Productos próximos a vencer:")
            st.dataframe(expiring_soon)
        else:
            st.success("No hay productos próximos a vencer en los próximos días.")
