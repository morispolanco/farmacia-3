import streamlit as st
import requests

# Título de la aplicación
st.title("SmartPharma Management System")

# Descripción de la aplicación
st.write("""
Bienvenido al sistema de gestión de farmacias SmartPharma. 
Esta aplicación te permite gestionar inventarios, interactuar con clientes y asegurar el cumplimiento normativo.
""")

# Cargar la API Key desde los secrets
api_key = st.secrets["api_key"]

# Función para hacer la solicitud a la API externa
def call_external_api(prompt):
    url = "https://dashscope-intl.aliyuncs.com"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-SSE": "enable"
    }
    data = {
        "model": "qwen-max",
        "input": {
            "messages": [
                {"role": "system", "content": "Eres un asistente de farmacia."},
                {"role": "user", "content": prompt}
            ]
        },
        "parameters": {
            "result_format": "message",
            "top_p": 0.8,
            "temperature": 1
        }
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# Interfaz de usuario
st.header("Consulta sobre Medicamentos")
user_input = st.text_input("Escribe tu pregunta sobre medicamentos o gestión de farmacia:")

if st.button("Enviar"):
    if user_input.strip() == "":
        st.error("Por favor, ingresa una pregunta válida.")
    else:
        with st.spinner("Procesando tu solicitud..."):
            api_response = call_external_api(user_input)
        
        # Mostrar la respuesta de la API
        if "output" in api_response and "choices" in api_response["output"]:
            response_text = api_response["output"]["choices"][0]["message"]["content"]
            st.success("Respuesta:")
            st.write(response_text)
        else:
            st.error("Error al procesar la solicitud. Por favor, intenta nuevamente.")

# Sección de características clave
st.header("Características Clave")
st.markdown("""
- **Gestión de Inventario**: Seguimiento en tiempo real de niveles de stock, reorden automático y alertas de vencimiento.
- **Compromiso con el Cliente**: Programas de lealtad, recordatorios de recargas y planes personalizados de adherencia a medicamentos.
- **Cumplimiento Normativo**: Actualizaciones automáticas sobre regulaciones de prescripción, cambios en el calendario de medicamentos y envío electrónico de informes necesarios.
- **Gestión de Recetas**: Recetas digitales, recargas automáticas y almacenamiento seguro de registros de pacientes.
- **Capacidades de Integración**: Integración perfecta con sistemas POS existentes y EHR (Registros Electrónicos de Salud).
""")

# Sección de modelo de monetización
st.header("Modelo de Monetización")
st.markdown("""
- **Modelo de Suscripción**: Planes de suscripción escalonados que van desde funciones básicas hasta premium, dirigidos tanto a farmacias individuales como a cadenas de farmacias.
- **Tarifas de Personalización e Integración**: Cargos adicionales por integraciones personalizadas con otros sistemas y por el desarrollo de funciones personalizadas.
- **Capacitación y Soporte**: Sesiones de capacitación pagadas y servicios de soporte continuo para los usuarios.
""")
