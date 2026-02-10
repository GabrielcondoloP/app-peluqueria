import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Configuración de página
st.set_page_config(page_title="Peluquería Canina", page_icon="🐾", layout="wide")

# Función para conectar con Google Sheets
def conectar_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # Usamos st.secrets para leer la llave de forma segura en la nube
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # Abre la hoja por nombre
        sheet = client.open("Gestion_Peluqueria").sheet1
        return sheet
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

def main():
    st.title("🐾 Gestión Peluquería")
    
    sheet = conectar_google_sheet()
    if not sheet: st.stop()

    # Menú de navegación
    opcion = st.sidebar.radio("Ir a:", ["🔍 Buscar / Editar", "➕ Nuevo Perro", "📊 Resumen"])

    # --- PESTAÑA: BUSCAR Y VER ---
    if opcion == "🔍 Buscar / Editar":
        st.header("Base de Datos de Clientes")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        if not df.empty:
            busqueda = st.text_input("Filtrar por nombre, raza o teléfono:")
            
            if busqueda:
                mask = df.astype(str).apply(lambda x: x.str.contains(busqueda, case=False)).any(axis=1)
                df_filtrado = df[mask]
            else:
                df_filtrado = df

            st.dataframe(df_filtrado, use_container_width=True)
            st.caption(f"Mostrando {len(df_filtrado)} registros.")
            
            st.divider()
            st.subheader("🗑️ Borrar Perro (Cuidado)")
            fila_borrar = st.number_input("Número de fila a borrar (ver en Excel, empieza en 2)", min_value=2, step=1)
            if st.button("Eliminar Fila Definitivamente"):
                try:
                    sheet.delete_rows(fila_borrar)
                    st.success("Fila eliminada. Recarga la página.")
                    st.rerun()
                except:
                    st.error("Error al borrar. Verifica el número de fila.")
        else:
            st.info("La base de datos está vacía.")

    # --- PESTAÑA: NUEVO PERRO ---
    elif opcion == "➕ Nuevo Perro":
        st.header("Registrar Nuevo Cliente")
        with st.form("ficha_entry", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre*")
                raza = st.text_input("Raza")
                sexo = st.selectbox("Sexo", ["Macho", "Hembra"])
                telefono = st.text_input("Teléfono (Móvil)")
            with col2:
                servicio = st.selectbox("Servicio", ["Corte", "Baño", "Corte+Baño", "Deslanado", "Uñas"])
                precio = st.number_input("Precio (€)", min_value=0.0, step=5.0)
                fecha = st.date_input("Fecha", datetime.today())
                caracter = st.text_input("Carácter")
            
            obs = st.text_area("Observaciones")
            btn_guardar = st.form_submit_button("GUARDAR FICHA")

            if btn_guardar:
                if not nombre:
                    st.warning("El nombre es obligatorio.")
                else:
                    fila = [nombre, raza, sexo, telefono, servicio, precio, str(fecha), caracter, obs]
                    sheet.append_row(fila)
                    st.success(f"¡{nombre} guardado correctamente!")

    # --- PESTAÑA: RESUMEN ---
    elif opcion == "📊 Resumen":
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            total_ingresos = df["Precio"].sum() if "Precio" in df.columns else 0
            col1, col2 = st.columns(2)
            col1.metric("Total Perros", len(df))
            col2.metric("Ingresos Totales", f"{total_ingresos} €")
        else:
            st.write("Sin datos aún.")

if __name__ == "__main__":
    main()
