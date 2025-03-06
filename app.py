import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Configuración inicial de la aplicación
st.set_page_config(page_title="Sistema de Gestión de Inventario y Pedidos", layout="wide")

# Datos simulados del inventario
inventory_data = pd.DataFrame([
    {"Producto": "Paracetamol 500mg", "Stock": 20, "Stock Mínimo": 50, "Vencimiento": "2023-12-01"},
    {"Producto": "Ibuprofeno 400mg", "Stock": 120, "Stock Mínimo": 30, "Vencimiento": "2024-06-15"},
    {"Producto": "Amoxicilina 500mg", "Stock": 15, "Stock Mínimo": 20, "Vencimiento": "2023-10-05"}
])
inventory_data['Vencimiento'] = pd.to_datetime(inventory_data['Vencimiento'])

# Datos simulados de ventas mensuales
sales_data = pd.DataFrame({
    "Mes": ["Ene", "Feb", "Mar", "Abr", "May", "Jun"],
    "Ventas": [1200, 1500, 1700, 1600, 1800, 1900]
})

# Función para verificar alertas de stock bajo
def check_low_stock_alerts(data):
    low_stock_items = data[data['Stock'] < data['Stock Mínimo']]
    if not low_stock_items.empty:
        st.warning("⚠️ Alerta: Los siguientes productos están por debajo del stock mínimo:")
        st.dataframe(low_stock_items)
    else:
        st.success("✅ Todos los productos tienen stock suficiente.")

# Función para verificar alertas de vencimiento
def check_expiry_alerts(data):
    today = datetime.today()
    soon_expiry = data[(data['Vencimiento'] - today).dt.days <= 15]
    if not soon_expiry.empty:
        st.error("🚨 Alerta: Los siguientes productos están próximos a vencer en menos de 15 días:")
        st.dataframe(soon_expiry)
    else:
        st.success("📅 No hay productos próximos a vencer en menos de 15 días.")

# Función para generar pedidos automáticos
def generate_auto_order(data):
    low_stock_items = data[data['Stock'] < data['Stock Mínimo']]
    if not low_stock_items.empty:
        st.info(f"📦 Pedido generado para: {', '.join(low_stock_items['Producto'])}")
    else:
        st.info("📦 No hay productos por debajo del stock mínimo para generar un pedido.")

# Título de la aplicación
st.title("👨‍⚕️ PharmaInventory: Sistema de Gestión de Inventario y Pedidos Automatizados")

# Pestañas principales
tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Inventario", "Pedidos Automatizados", "Reportes"])

# Tablero General
with tab1:
    st.header("📊 Resumen General")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Stock Total", inventory_data['Stock'].sum())
    with col2:
        st.metric("Productos Bajo Stock", len(inventory_data[inventory_data['Stock'] < inventory_data['Stock Mínimo']]))
    with col3:
        st.metric("Productos Próximos a Vencer", len(inventory_data[(inventory_data['Vencimiento'] - datetime.today()).dt.days <= 15]))

# Gestión de Inventario
with tab2:
    st.header("📋 Inventario en Tiempo Real")
    check_low_stock_alerts(inventory_data)
    check_expiry_alerts(inventory_data)
    st.dataframe(inventory_data.style.applymap(
        lambda x: 'background-color: #ffebcc' if isinstance(x, int) and x < 50 else '',
        subset=['Stock']
    ))
    if st.button("Generar Pedido Automático"):
        generate_auto_order(inventory_data)

# Pedidos Automatizados
with tab3:
    st.header("🚚 Pedidos Automatizados")
    st.subheader("Historial de Pedidos")
    orders_history = pd.DataFrame({
        "Fecha": ["2023-10-01", "2023-09-15"],
        "Producto": ["Paracetamol 500mg", "Amoxicilina 500mg"],
        "Cantidad": [100, 50]
    })
    st.dataframe(orders_history)

# Reportes y Análisis
with tab4:
    st.header("📈 Reportes y Análisis")
    st.subheader("Ventas Mensuales")
    fig_sales = px.bar(sales_data, x="Mes", y="Ventas", title="Ventas Mensuales", color="Ventas", color_continuous_scale="blues")
    st.plotly_chart(fig_sales, use_container_width=True)

    st.subheader("Productos Más Vendidos")
    top_products = pd.DataFrame({
        "Producto": ["Paracetamol 500mg", "Ibuprofeno 400mg"],
        "Unidades Vendidas": [1200, 950]
    })
    fig_top_products = px.pie(top_products, names="Producto", values="Unidades Vendidas", title="Productos Más Vendidos")
    st.plotly_chart(fig_top_products, use_container_width=True)
