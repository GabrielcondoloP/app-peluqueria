import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from PIL import Image
import io
import base64

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Peluquería Canina", page_icon="🐾", layout="wide")

st.markdown("""
    <style>
    .stApp {background-color: #0e1117;}
    div[data-testid="stExpander"] div[role="button"] p {font-size: 1.1rem; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIN ---
def check_password():
    if "admin_password" not in st.secrets:
        st.error("⚠️ Error: Configura 'admin_password' en los Secrets.")
        st.stop()

    def password_entered():
        if st.session_state["password_input"] == st.secrets["admin_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.title("🔐 Acceso Peluquería")
    st.text_input("Contraseña:", type="password", on_change=password_entered, key="password_input")
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("❌ Incorrecta")
    return False

def cerrar_sesion():
    st.session_state["password_correct"] = False
    st.rerun()

# --- 3. CONEXIONES ---
def conectar_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("Gestion_Peluqueria").sheet1
        return sheet
    except Exception as e:
        st.error(f"❌ Error Drive: {e}")
        return None

def imagen_a_base64(img_file):
    if img_file is None: return ""
    try:
        image = Image.open(img_file).convert('RGB')
        image.thumbnail((400, 400))
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=70)
        return base64.b64encode(buffered.getvalue()).decode()
    except: return ""

def base64_a_imagen(base64_str):
    if not base64_str or len(str(base64_str)) < 10: return None
    try:
        return Image.open(io.BytesIO(base64.b64decode(base64_str)))
    except: return None

# --- 4. APP PRINCIPAL ---
def main():
    if not check_password(): st.stop()

    with st.sidebar:
        st.title("🐶 Menú")
        if st.button("Cerrar Sesión"): cerrar_sesion()
        st.divider()
        st.info("Sistema v4.0 (Selector Inteligente)")

    st.title("🐾 Gestión de Peluquería")
    sheet = conectar_google_sheet()
    if not sheet: st.stop()

    # Carga de datos inicial
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Índice de filas para poder editar (Empieza en 2 porque Excel tiene cabecera)
    if not df.empty:
        df["_row_index"] = range(2, len(df) + 2)
        # --- TRUCO DEL SELECTOR INTELIGENTE ---
        # Creamos una columna "Etiqueta" que combina Nombre + Raza + Telefono
        # Así al buscar "Toby" salen todos los Tobys diferenciados
        df["_etiqueta"] = df["Nombre"] + " (" + df["Raza"] + ") - 📞 " + df["Telefono"].astype(str)

    # PESTAÑAS
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Buscar y Editar", "🔄 Nueva Visita (Cliente)", "➕ Nuevo (Primerizo)", "📊 Caja"])

    # ==========================================
    # PESTAÑA 1: BUSCAR Y EDITAR TODO
    # ==========================================
    with tab1:
        st.header("Base de Datos (Edición Completa)")
        
        if df.empty:
            st.info("No hay datos.")
        else:
            busqueda = st.text_input("🔍 Buscar:", placeholder="Escribe Nombre, Teléfono o Raza...")
            
            if busqueda:
                mask = df.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)
                df_filtrado = df[mask]
            else:
                df_filtrado = df

            st.caption(f"{len(df_filtrado)} fichas encontradas.")

            for index, row in df_filtrado.iterrows():
                # Título del desplegable
                titulo_expander = f"🐶 {row['Nombre']} ({row['Raza']}) - {row['Fecha']}"
                
                with st.expander(titulo_expander):
                    # --- MODO LECTURA ---
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        img = base64_a_imagen(row.get("Foto", ""))
                        if img: st.image(img, use_container_width=True)
                        else: st.write("🐕 Sin foto")
                    with c2:
                        st.info(f"📞 **{row['Telefono']}** | 💰 **{row['Precio']}€** | ✂️ **{row['Servicio']}**")
                        st.write(f"**Obs:** {row['Observaciones']}")
                        st.write(f"**Carácter:** {row['Caracter']}")
                    
                    st.divider()
                    
                    # --- MODO EDICIÓN TOTAL ---
                    st.write("✏️ **Editar Ficha Completa:**")
                    with st.form(f"edit_full_{row['_row_index']}"):
                        col_e1, col_e2 = st.columns(2)
                        
                        # Precargamos los valores actuales
                        new_nom = col_e1.text_input("Nombre", row['Nombre'])
                        new_raz = col_e2.text_input("Raza", row['Raza'])
                        
                        new_sex = col_e1.selectbox("Sexo", ["Macho", "Hembra"], index=0 if row['Sexo']=="Macho" else 1)
                        new_tel = col_e2.text_input("Teléfono", row['Telefono'])
                        
                        new_srv = col_e1.selectbox("Servicio", ["Corte", "Baño", "Corte + Baño", "Deslanado", "Solo Uñas", "Otro"], index=0) # Index 0 por defecto, mejorar si coincide
                        new_pre = col_e2.number_input("Precio (€)", value=float(row['Precio']) if row['Precio']!='' else 0.0)
                        
                        # Fecha complicada: intentamos convertirla, si falla ponemos hoy
                        try:
                            fecha_val = datetime.strptime(str(row['Fecha']), "%Y-%m-%d").date()
                        except:
                            fecha_val = datetime.today()
                        new_fec = col_e1.date_input("Fecha Visita", fecha_val)
                        
                        new_car = col_e2.text_input("Carácter", row['Caracter'])
                        new_obs = st.text_area("Observaciones", row['Observaciones'])
                        
                        if st.form_submit_button("💾 Guardar Cambios"):
                            idx = row['_row_index']
                            # Actualizamos celda a celda (Columnas 1 a 9)
                            # Orden: Nombre(1), Raza(2), Sexo(3), Tlf(4), Servicio(5), Precio(6), Fecha(7), Caracter(8), Obs(9)
                            try:
                                sheet.update_cell(idx, 1, new_nom)
                                sheet.update_cell(idx, 2, new_raz)
                                sheet.update_cell(idx, 3, new_sex)
                                sheet.update_cell(idx, 4, new_tel)
                                sheet.update_cell(idx, 5, new_srv)
                                sheet.update_cell(idx, 6, new_pre)
                                sheet.update_cell(idx, 7, str(new_fec))
                                sheet.update_cell(idx, 8, new_car)
                                sheet.update_cell(idx, 9, new_obs)
                                st.success("✅ Ficha actualizada correctamente.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error actualizando: {e}")

    # ==========================================
    # PESTAÑA 2: NUEVA VISITA (SELECTOR INTELIGENTE)
    # ==========================================
    with tab2:
        st.header("🔄 Registrar Visita a Cliente Habitual")
        st.caption("Busca por nombre o teléfono. El sistema diferencia si hay varios 'Tobys'.")

        if df.empty:
            st.warning("No hay clientes registrados.")
        else:
            # --- AQUÍ ESTÁ LA MAGIA ---
            # Usamos la columna "_etiqueta" que creamos al principio (Nombre + Raza + Tlf)
            # Streamlit permite escribir en este cuadro para filtrar
            etiquetas_unicas = df["_etiqueta"].unique().tolist()
            seleccion = st.selectbox("Selecciona al perro:", etiquetas_unicas, index=None, placeholder="Escribe 'Toby' o '666...'")

            if seleccion:
                # Recuperamos los datos originales buscando por esa etiqueta exacta
                datos_perro = df[df["_etiqueta"] == seleccion].iloc[-1]
                
                st.success(f"Has seleccionado a: **{datos_perro['Nombre']}** (Dueño tlf: {datos_perro['Telefono']})")
                
                with st.form("form_recurrente"):
                    c1, c2 = st.columns(2)
                    with c1:
                        # Mostramos datos fijos (Deshabilitados para no liarla, o editables si quieres)
                        st.text_input("Nombre", value=datos_perro['Nombre'], disabled=True)
                        st.text_input("Raza", value=datos_perro['Raza'], disabled=True)
                        st.text_input("Teléfono", value=datos_perro['Telefono'], disabled=True)
                        # Foto oculta
                        foto_hidden = datos_perro.get('Foto', "")
                    
                    with c2:
                        st.markdown("### 📅 Datos de la Visita de HOY")
                        servicio = st.selectbox("Servicio realizado", ["Corte", "Baño", "Corte + Baño", "Deslanado", "Solo Uñas", "Otro"])
                        precio = st.number_input("Precio (€)", min_value=0.0, step=5.0)
                        fecha = st.date_input("Fecha", datetime.today())
                        obs = st.text_area("Observaciones de hoy", value=datos_perro['Observaciones']) # Sugiere las anteriores

                    if st.form_submit_button("✅ CONFIRMAR VISITA"):
                        # Creamos fila nueva reciclando datos viejos + los de hoy
                        nueva_fila = [
                            datos_perro['Nombre'], 
                            datos_perro['Raza'], 
                            datos_perro['Sexo'], 
                            datos_perro['Telefono'], 
                            servicio, 
                            precio, 
                            str(fecha), 
                            datos_perro['Caracter'], 
                            obs, 
                            foto_hidden
                        ]
                        try:
                            sheet.append_row(nueva_fila)
                            st.success(f"Visita de {datos_perro['Nombre']} registrada en el historial.")
                            st.balloons()
                        except:
                            st.error("Error al guardar.")

    # ==========================================
    # PESTAÑA 3: NUEVO (PRIMERIZO)
    # ==========================================
    with tab3:
        st.header("🆕 Primer Registro (Perro Nuevo)")
        with st.form("form_nuevo", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nom = st.text_input("Nombre *")
                raz = st.text_input("Raza")
                sex = st.selectbox("Sexo", ["Macho", "Hembra"])
                tel = st.text_input("Teléfono (Importante)")
                foto = st.file_uploader("Foto", type=['jpg','png'])
            with c2:
                srv = st.selectbox("Servicio", ["Corte", "Baño", "Completo", "Otro"])
                pre = st.number_input("Precio", step=5.0)
                fec = st.date_input("Fecha", datetime.today())
                car = st.text_input("Carácter")
                obs = st.text_area("Observaciones")
            
            if st.form_submit_button("Guardar Nuevo Cliente"):
                if nom:
                    ft = imagen_a_base64(foto)
                    row = [nom, raz, sex, tel, srv, pre, str(fec), car, obs, ft]
                    sheet.append_row(row)
                    st.success("Cliente creado!")
                else:
                    st.warning("El nombre es obligatorio")

    # ==========================================
    # PESTAÑA 4: CAJA
    # ==========================================
    with tab4:
        st.header("📊 Finanzas")
        if not df.empty and "Precio" in df.columns:
            df["Precio"] = pd.to_numeric(df["Precio"], errors='coerce').fillna(0)
            st.metric("Total Facturado (Histórico)", f"{df['Precio'].sum():,.2f} €")
            st.bar_chart(df["Servicio"].value_counts())

if __name__ == "__main__":
    main()
