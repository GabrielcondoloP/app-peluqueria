import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from PIL import Image
import io
import base64

# --- CONFIGURACIÓN DE PÁGINA (COLORES Y TÍTULO) ---
st.set_page_config(page_title="Peluquería Canina", page_icon="🐾", layout="wide")

# --- ESTILOS CSS PERSONALIZADOS (PARA QUE SE VEA MÁS BONITO) ---
st.markdown("""
    <style>
    .stApp {background-color: #0e1117;}
    .block-container {padding-top: 2rem;}
    div[data-testid="stExpander"] div[role="button"] p {font-size: 1.2rem; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES ---
def conectar_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("Gestion_Peluqueria").sheet1
        return sheet
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

# Función para convertir foto subida a texto (Base64) para guardarla en Excel
def imagen_a_base64(img_file):
    if img_file is None: return ""
    # Abrimos la imagen y la reducimos para que no pese mucho en el Excel
    image = Image.open(img_file)
    image = image.convert('RGB')
    image.thumbnail((400, 400)) # Reducir tamaño
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=70)
    return base64.b64encode(buffered.getvalue()).decode()

# Función para leer el texto del Excel y mostrarlo como foto
def base64_a_imagen(base64_str):
    if not base64_str or len(str(base64_str)) < 10: return None
    try:
        return Image.open(io.BytesIO(base64.b64decode(base64_str)))
    except:
        return None

def main():
    st.title("🐾 Gestión de Peluquería Canina")
    
    sheet = conectar_google_sheet()
    if not sheet: st.stop()

    # --- MENÚ SUPERIOR ---
    tabs = st.tabs(["🐶 Ver Fichas (Con Fotos)", "➕ Nuevo Cliente", "📊 Estadísticas"])

    # ==========================
    # PESTAÑA 1: VISUALIZADOR TIPO APP
    # ==========================
    with tabs[0]:
        st.header("Mis Clientes Peludos")
        
        # Cargar datos
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        if not df.empty:
            # Buscador
            busqueda = st.text_input("🔍 Buscar por Nombre, Raza o Teléfono:", placeholder="Escribe aquí...")
            
            if busqueda:
                mask = df.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)
                df_filtrado = df[mask]
            else:
                df_filtrado = df

            st.caption(f"Mostrando {len(df_filtrado)} perros.")

            # --- AQUÍ ESTÁ EL DISEÑO "BONITO" (GRID DE TARJETAS) ---
            # Iteramos por cada perro y creamos una "tarjeta" visual
            for index, row in df_filtrado.iterrows():
                # Creamos un contenedor con borde
                with st.container(border=True):
                    col_foto, col_info, col_acciones = st.columns([1, 3, 1])
                    
                    # Columna 1: La Foto
                    with col_foto:
                        img = base64_a_imagen(row.get("Foto", ""))
                        if img:
                            st.image(img, use_container_width=True)
                        else:
                            # Si no tiene foto, mostramos un icono genérico
                            st.markdown("## 🐕")
                            st.write("(Sin foto)")

                    # Columna 2: La Info Principal
                    with col_info:
                        st.subheader(f"{row['Nombre']} ({row['Raza']})")
                        st.markdown(f"**📞 Teléfono:** `{row['Telefono']}`")
                        st.markdown(f"**✂️ Servicio:** {row['Servicio']} | **💰 Precio:** {row['Precio']}€")
                        
                        # Usamos un desplegable para detalles menos importantes
                        with st.expander("Ver observaciones y carácter"):
                            st.write(f"**Carácter:** {row['Caracter']}")
                            st.info(f"📝 {row['Observaciones']}")
                            st.caption(f"Última visita: {row['Fecha']}")

                    # Columna 3: Botones
                    with col_acciones:
                        st.write("") # Espacio
                        st.write("") 
                        # Aquí podrías poner lógica para borrar (calculando el ID de fila real)
                        st.button("✏️ Editar", key=f"btn_edit_{index}", disabled=True, help="Función en desarrollo")

        else:
            st.info("Aún no tienes clientes registrados.")

    # ==========================
    # PESTAÑA 2: NUEVO REGISTRO (CON FOTO)
    # ==========================
    with tabs[1]:
        st.header("📸 Nuevo Registro")
        with st.form("ficha_entry", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                nombre = st.text_input("Nombre*")
                raza = st.text_input("Raza")
                sexo = st.selectbox("Sexo", ["Macho", "Hembra"])
                telefono = st.text_input("Teléfono")
                
                # CAMPO PARA SUBIR FOTO
                foto_upload = st.file_uploader("Subir Foto del Perro", type=['jpg', 'png', 'jpeg'])

            with col2:
                servicio = st.selectbox("Servicio", ["Corte", "Baño", "Corte+Baño", "Deslanado", "Uñas"])
                precio = st.number_input("Precio (€)", min_value=0.0, step=5.0)
                fecha = st.date_input("Fecha", datetime.today())
                caracter = st.text_input("Carácter")
                obs = st.text_area("Observaciones")

            btn_guardar = st.form_submit_button("💾 GUARDAR FICHA COMPLETA")

            if btn_guardar:
                if not nombre:
                    st.warning("El nombre es obligatorio.")
                else:
                    with st.spinner("Guardando foto y datos..."):
                        # Convertir foto a texto
                        foto_str = imagen_a_base64(foto_upload)
                        
                        fila = [
                            nombre, raza, sexo, telefono, servicio, 
                            precio, str(fecha), caracter, obs, foto_str
                        ]
                        try:
                            sheet.append_row(fila)
                            st.success(f"¡{nombre} guardado con foto!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")

    # ==========================
    # PESTAÑA 3: ESTADÍSTICAS (ARREGLADO EL ERROR)
    # ==========================
    with tabs[2]:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            # --- AQUÍ ESTÁ LA SOLUCIÓN A TU ERROR ---
            # 1. Convertimos la columna Precio a números.
            # 2. Si hay texto que no es número (ej: "20€"), lo convierte en NaN (vacío).
            # 3. Luego rellenamos los vacíos con 0.
            if "Precio" in df.columns:
                df["Precio"] = pd.to_numeric(df["Precio"], errors='coerce').fillna(0)
                total_ingresos = df["Precio"].sum()
            else:
                total_ingresos = 0

            # Métricas grandes y bonitas
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Perros", len(df), delta="Clientes")
            col2.metric("Ingresos Totales", f"{total_ingresos:,.2f} €", delta="Euros")
            
            # Gráfico simple de razas
            st.subheader("Razas más frecuentes")
            st.bar_chart(df["Raza"].value_counts())
        else:
            st.write("Sin datos aún.")

if __name__ == "__main__":
    main()
