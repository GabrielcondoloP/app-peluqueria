import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from PIL import Image
import io
import base64

# --- 1. CONFIGURACIÓN DE PÁGINA (SIEMPRE LO PRIMERO) ---
st.set_page_config(page_title="Peluquería Canina", page_icon="🐾", layout="wide")

# Estilos CSS para mejorar la apariencia
st.markdown("""
    <style>
    .stApp {background-color: #0e1117;}
    div[data-testid="stExpander"] div[role="button"] p {font-size: 1.1rem; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# --- 2. SISTEMA DE LOGIN (NATIVO Y ROBUSTO) ---
def check_password():
    """Retorna True si el usuario está logueado correctamente."""
    
    # Si no hay contraseña configurada en secrets, avisar
    if "admin_password" not in st.secrets:
        st.error("⚠️ Error: No has configurado 'admin_password' en los Secrets de Streamlit.")
        st.stop()

    def password_entered():
        """Verifica la contraseña introducida."""
        if st.session_state["password_input"] == st.secrets["admin_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]  # Borrar por seguridad
        else:
            st.session_state["password_correct"] = False

    # Si ya está logueado, devolver True
    if st.session_state.get("password_correct", False):
        return True

    # Mostrar formulario de login
    st.title("🔐 Acceso Peluquería")
    st.text_input("Introduce la contraseña:", type="password", on_change=password_entered, key="password_input")
    
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("❌ Contraseña incorrecta")

    return False

def cerrar_sesion():
    st.session_state["password_correct"] = False
    st.rerun()

# --- 3. FUNCIONES DE GOOGLE SHEETS E IMÁGENES ---
def conectar_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("Gestion_Peluqueria").sheet1
        return sheet
    except Exception as e:
        st.error(f"❌ Error conectando con Google Drive: {e}")
        return None

def imagen_a_base64(img_file):
    """Convierte la imagen subida a texto para guardarla en Excel."""
    if img_file is None: return ""
    try:
        image = Image.open(img_file).convert('RGB')
        # Reducimos tamaño para no saturar la hoja de cálculo (max 400x400)
        image.thumbnail((400, 400)) 
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=70)
        return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        st.error(f"Error procesando imagen: {e}")
        return ""

def base64_a_imagen(base64_str):
    """Convierte el texto del Excel de vuelta a imagen."""
    if not base64_str or len(str(base64_str)) < 10: return None
    try:
        return Image.open(io.BytesIO(base64.b64decode(base64_str)))
    except:
        return None

# --- 4. APP PRINCIPAL ---
def main():
    # Bloqueo de seguridad: Si no hay login, se detiene aquí
    if not check_password():
        st.stop()

    # Barra lateral con menú y logout
    with st.sidebar:
        st.title("🐶 Menú")
        st.success("✅ Sesión Iniciada")
        if st.button("Cerrar Sesión"):
            cerrar_sesion()
        st.divider()
        st.info("Peluquería Canina v2.0")

    # Título principal
    st.title("🐾 Gestión de Peluquería")

    # Conexión
    sheet = conectar_google_sheet()
    if not sheet: st.stop()

    # Pestañas
    tab1, tab2, tab3 = st.tabs(["📋 Ver Fichas", "➕ Nuevo Cliente", "📊 Estadísticas"])

    # --- PESTAÑA 1: VER FICHAS (CON TARJETAS Y FOTOS) ---
    with tab1:
        st.header("Listado de Clientes")
        
        # Obtener datos
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        if not df.empty:
            busqueda = st.text_input("🔍 Buscar perro, raza o teléfono:", placeholder="Escribe aquí...")
            
            # Filtro inteligente
            if busqueda:
                mask = df.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)
                df_filtrado = df[mask]
            else:
                df_filtrado = df
            
            st.caption(f"Mostrando {len(df_filtrado)} resultados")

            # Mostrar tarjetas
            for index, row in df_filtrado.iterrows():
                with st.container(border=True):
                    col_img, col_info = st.columns([1, 3])
                    
                    # Imagen
                    with col_img:
                        foto_str = row.get("Foto", "")
                        img = base64_a_imagen(foto_str)
                        if img:
                            st.image(img, use_container_width=True)
                        else:
                            st.markdown("## 🐕")
                            st.caption("Sin foto")

                    # Información
                    with col_info:
                        st.subheader(f"{row['Nombre']} ({row['Raza']})")
                        st.markdown(f"**📞 Tlf:** `{row['Telefono']}`")
                        st.markdown(f"**✂️ Servicio:** {row['Servicio']} | **💶 Precio:** {row['Precio']}€")
                        
                        with st.expander("📝 Ver observaciones y fecha"):
                            st.write(f"**Carácter:** {row['Caracter']}")
                            st.write(f"**Fecha última visita:** {row['Fecha']}")
                            st.info(f"Observaciones: {row['Observaciones']}")
        else:
            st.info("📭 La base de datos está vacía. Añade el primer perro en la siguiente pestaña.")

    # --- PESTAÑA 2: NUEVO PERRO ---
    with tab2:
        st.header("Registrar Nuevo Cliente")
        with st.form("form_nuevo_perro", clear_on_submit=True):
            c1, c2 = st.columns(2)
            
            with c1:
                nombre = st.text_input("Nombre del Perro *")
                raza = st.text_input("Raza")
                sexo = st.selectbox("Sexo", ["Macho", "Hembra"])
                telefono = st.text_input("Teléfono Dueño")
                foto_upload = st.file_uploader("📸 Subir Foto", type=['jpg', 'jpeg', 'png'])

            with c2:
                servicio = st.selectbox("Servicio", ["Corte", "Baño", "Corte + Baño", "Deslanado", "Solo Uñas", "Otro"])
                precio = st.number_input("Precio (€)", min_value=0.0, step=5.0)
                fecha = st.date_input("Fecha Visita", datetime.today())
                caracter = st.text_input("Carácter (Ej: Bueno, Miedoso)")
                obs = st.text_area("Observaciones y Cuidados")

            btn_enviar = st.form_submit_button("💾 GUARDAR FICHA")

            if btn_enviar:
                if not nombre:
                    st.warning("⚠️ El nombre es obligatorio")
                else:
                    with st.spinner("Guardando en la nube..."):
                        foto_base64 = imagen_a_base64(foto_upload)
                        
                        # El orden debe coincidir con tus columnas de Excel:
                        # Nombre, Raza, Sexo, Telefono, Servicio, Precio, Fecha, Caracter, Observaciones, Foto
                        nueva_fila = [
                            nombre, raza, sexo, telefono, servicio, 
                            precio, str(fecha), caracter, obs, foto_base64
                        ]
                        
                        try:
                            sheet.append_row(nueva_fila)
                            st.success(f"✅ ¡{nombre} registrado con éxito!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error guardando: {e}")

    # --- PESTAÑA 3: ESTADÍSTICAS ---
    with tab3:
        st.header("Resumen del Negocio")
        # Volvemos a pedir los datos para tenerlos actualizados
        data_stats = sheet.get_all_records()
        df_stats = pd.DataFrame(data_stats)

        if not df_stats.empty:
            c1, c2, c3 = st.columns(3)
            
            # 1. Total Perros
            c1.metric("Total Clientes", len(df_stats))
            
            # 2. Total Dinero (Limpiando errores de texto)
            if "Precio" in df_stats.columns:
                # Convierte a números, si hay error pone 0
                df_stats["Precio"] = pd.to_numeric(df_stats["Precio"], errors='coerce').fillna(0)
                total_euros = df_stats["Precio"].sum()
                c2.metric("Ingresos Totales", f"{total_euros:,.2f} €")
            
            # 3. Raza más común
            if "Raza" in df_stats.columns:
                top_raza = df_stats["Raza"].mode()
                raza_txt = top_raza[0] if not top_raza.empty else "N/A"
                c3.metric("Raza Frecuente", raza_txt)
            
            st.divider()
            st.subheader("Servicios más solicitados")
            if "Servicio" in df_stats.columns:
                st.bar_chart(df_stats["Servicio"].value_counts())

if __name__ == "__main__":
    main()
