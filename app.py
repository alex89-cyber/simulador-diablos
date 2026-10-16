"""Simulador de pitcheo Diablos Rojos: Stuff+, Location+ y Pitching+ en Harp Helú contra el nivel del mar.

Correr en local:  streamlit run app.py
Necesita la carpeta modelos/ con los tres pkl y razones_altitud.csv que guarda Stuff_Final_v2.ipynb (sección 16a).
Los colores rojo y blanco salen de .streamlit/config.toml y el logo de logo.svg; sin ellos la app corre igual.
"""
import base64
import os

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import streamlit as st

import simulador as sim

AQUI = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(AQUI, "logo.svg")
ROJO = "#C8102E"

st.set_page_config(page_title="Simulador de pitcheo Diablos Rojos",
                   page_icon=LOGO if os.path.isfile(LOGO) else "⚾", layout="wide")

# Valores típicos de un derecho por tipo de pitch, solo para arrancar el formulario (medianas redondeadas de la liga)
TIPICOS = {
    "Four-Seam": dict(velo=92.0, ivb=15.0, hb=8.0, spin=2340.0, eje=211.0, alto=5.9, lado=1.6, ext=6.1),
    "Sinker": dict(velo=91.5, ivb=9.5, hb=14.0, spin=2270.0, eje=237.0, alto=5.6, lado=1.9, ext=5.9),
    "Cutter": dict(velo=89.0, ivb=9.0, hb=-0.5, spin=2460.0, eje=177.0, alto=5.9, lado=1.7, ext=5.8),
    "Slider": dict(velo=84.0, ivb=3.0, hb=-3.5, spin=2450.0, eje=118.0, alto=5.7, lado=1.8, ext=5.7),
    "Curveball": dict(velo=78.5, ivb=-7.5, hb=-8.0, spin=2550.0, eje=42.0, alto=5.8, lado=1.7, ext=5.5),
    "Changeup": dict(velo=84.0, ivb=6.0, hb=11.5, spin=1770.0, eje=246.0, alto=5.7, lado=1.7, ext=5.9),
    "Splitter": dict(velo=83.5, ivb=3.0, hb=6.0, spin=1100.0, eje=250.0, alto=5.9, lado=1.8, ext=5.8),
}
# Divergente azul (peor que el promedio) a gris (100) a rojo Diablos (mejor que el promedio)
ESCALA = [[0.0, "#184f95"], [0.25, "#6da7ec"], [0.5, "#f0efec"], [0.75, "#ec8a89"], [1.0, ROJO]]
TINTA = "#0b0b0b"
SUPERFICIE = "#fcfcfb"
MANOS = {"Right": "Derecho", "Left": "Zurdo"}


def tipico(tipo, mano):
    """Valores de arranque; para un zurdo se voltean el HB, el lado de salida y el eje, como en Trackman."""
    t = dict(TIPICOS.get(tipo, TIPICOS["Four-Seam"]))
    if mano == "Left":
        t["hb"], t["lado"], t["eje"] = -t["hb"], -t["lado"], 360.0 - t["eje"]
    return t


@st.cache_resource
def cargar_modelos():
    return sim.cargar(os.path.join(AQUI, "modelos"))


def logo_html():
    """El logo como imagen incrustada para la banda roja; vacío si no está logo.svg."""
    if not os.path.isfile(LOGO):
        return ""
    with open(LOGO, encoding="utf-8") as f:
        svg = base64.b64encode(f.read().encode("utf-8")).decode("ascii")
    return f'<img src="data:image/svg+xml;base64,{svg}" alt="Logo Diablos">'


modelos, razones = cargar_modelos()
cats = sim.categorias(modelos)

# Banda roja con logo, tarjetas con borde rojo y títulos de la barra lateral en rojo
st.markdown(f"""<style>
.dr-banda {{display: flex; align-items: center; gap: 16px; background: {ROJO}; border-radius: 12px;
            padding: 14px 22px; margin-bottom: 8px;}}
.dr-banda img {{width: 56px; height: 56px; background: #FFFFFF; border-radius: 50%; padding: 5px; flex-shrink: 0;}}
.dr-titulo {{color: #FFFFFF; font-size: 1.7rem; font-weight: 700; line-height: 1.2;}}
.dr-sub {{color: #FFFFFF; opacity: 0.92; font-size: 1rem;}}
[data-testid="stMetric"] {{background: #FFFFFF; border: 1px solid #E6C9CD; border-left: 6px solid {ROJO};
                          border-radius: 10px; padding: 12px 16px;}}
[data-testid="stMetricValue"] {{color: {ROJO}; font-weight: 700;}}
[data-testid="stSidebar"] {{border-right: 4px solid {ROJO};}}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{color: {ROJO};}}
</style>""", unsafe_allow_html=True)
st.markdown(f"""<div class="dr-banda">{logo_html()}<div>
<div class="dr-titulo">Simulador de pitcheo Diablos Rojos</div>
<div class="dr-sub">Harp Helú contra el nivel del mar</div></div></div>""", unsafe_allow_html=True)
st.caption("Teclea el Trackman de un pitch y ve sus tres calificaciones en los dos parques. "
           "100 es el promedio de la liga y cada 10 puntos es una desviación estándar.")

# ---------- Entrada del coach ----------
with st.sidebar:
    st.header("El pitch")
    medido = st.radio("¿Dónde se midió este Trackman?", list(sim.PARQUES), horizontal=True)
    mano = st.radio("Mano del pitcher", list(MANOS), format_func=MANOS.get, horizontal=True)
    bateador = st.radio("Bateador", list(MANOS), format_func=MANOS.get, horizontal=True)
    tipo = st.selectbox("Tipo de pitch", cats, index=cats.index("Slider") if "Slider" in cats else 0)
    t, k = tipico(tipo, mano), f"{tipo}_{mano}"
    velo = st.number_input("Velocidad de salida (mph)", 60.0, 105.0, t["velo"], 0.5, key="velo_" + k)
    ivb = st.number_input("IVB (pulgadas)", -30.0, 30.0, t["ivb"], 0.5, key="ivb_" + k)
    hb = st.number_input("HB de Trackman (pulgadas)", -30.0, 30.0, t["hb"], 0.5, key="hb_" + k)
    spin = st.number_input("Giro (rpm)", 500.0, 3800.0, t["spin"], 10.0, key="spin_" + k)
    eje = st.number_input("Eje de giro de Trackman (grados)", 0.0, 360.0, t["eje"], 1.0, key="eje_" + k)
    alto = st.number_input("Altura de salida (pies)", 3.0, 8.0, t["alto"], 0.1, key="alto_" + k)
    lado = st.number_input("Lado de salida de Trackman (pies)", -4.5, 4.5, t["lado"], 0.1, key="lado_" + k)
    extension = st.number_input("Extensión (pies)", 4.0, 8.0, t["ext"], 0.1, key="ext_" + k)

    st.subheader("Su recta principal")
    r = tipico("Four-Seam", mano)
    recta_velo = st.number_input("Velocidad de la recta (mph)", 60.0, 105.0, r["velo"], 0.5, key="rvelo_" + mano)
    recta_ivb = st.number_input("IVB de la recta (pulgadas)", -30.0, 30.0, r["ivb"], 0.5, key="rivb_" + mano)
    recta_hb = st.number_input("HB de la recta (pulgadas)", -30.0, 30.0, r["hb"], 0.5, key="rhb_" + mano)

    st.subheader("Situación")
    conteo = st.selectbox("Conteo (bolas-strikes)", sim.CONTEOS)
    loc_alto = st.slider("Altura al cruzar el home (pies)", 0.5, 4.5, 2.5, 0.1)
    loc_adentro = st.slider("Adentro (+) o afuera (-) para el bateador (pies)", -2.0, 2.0, 0.0, 0.1)

e = pd.DataFrame([{
    "tipo": tipo, "mano": mano, "bateador": bateador, "velo": velo, "ivb": ivb, "hb": hb, "spin": spin,
    "eje": eje, "alto": alto, "lado": lado, "extension": extension,
    "recta_velo": recta_velo, "recta_ivb": recta_ivb, "recta_hb": recta_hb, "conteo": conteo,
    "loc_alto": loc_alto, "loc_lado": loc_adentro if bateador == "Right" else -loc_adentro,
    "parque": sim.PARQUES[medido]}])

res, versiones = sim.evaluar(modelos, razones, e)
hh, nm = res.loc["Harp Helú"], res.loc["Nivel del mar"]

# ---------- Calificaciones ----------
columnas = st.columns(3)
explicacion = {"Stuff+": "Solo la física del pitch, sin importar dónde se tiró.",
               "Location+": "Solo la ubicación, el conteo y el bateador.",
               "Pitching+": "Física y ubicación juntas: lo más cercano al resultado."}
for col, capa in zip(columnas, ["Stuff+", "Location+", "Pitching+"]):
    col.metric(f"{capa} en Harp Helú", f"{hh[capa]:.0f}", f"{hh[capa] - nm[capa]:+.1f} contra el nivel del mar")
    col.caption(f"Al nivel del mar: {nm[capa]:.0f}. {explicacion[capa]}")

st.markdown(
    f"En Harp Helú este pitch tiene **{hh['IVB']:.1f}** pulgadas de IVB y **{hh['HB']:.1f}** de HB; "
    f"al nivel del mar, **{nm['IVB']:.1f}** y **{nm['HB']:.1f}**. "
    f"El aire de la Ciudad de México tiene cerca del 80% de la densidad del nivel del mar, así que el pitch se mueve menos.")

detalle = pd.DataFrame({
    "IVB (pulg.)": res["IVB"], "HB (pulg.)": res["HB"],
    "Stuff+": res["Stuff+"], "Location+": res["Location+"], "Pitching+": res["Pitching+"],
    "Carreras ahorradas cada 100 (Stuff+)": res["carreras_Stuff+"],
    "Whiff esperado (%)": res["p_whiff"], "En juego esperado (%)": res["p_en_juego"]}).round(1)
st.dataframe(detalle, use_container_width=True)
st.caption("Las carreras se miden contra el promedio de la liga en ese conteo, así que sí se comparan entre parques. "
           "Los puntos de cada capa se comparan contra el promedio de su propio parque, y no se suman entre capas.")


def dos_mapas(mapas, marcas, titulo_x, titulo_y, capa, zona=False):
    """Dos mapas de calor lado a lado con la misma escala centrada en 100 y el pitch marcado."""
    fig = make_subplots(rows=1, cols=2, subplot_titles=list(mapas), horizontal_spacing=0.08)
    dev = max(abs(m.values - 100).max() for m in mapas.values())
    dev = min(max(dev, 5), 30)
    for i, (nombre, m) in enumerate(mapas.items(), start=1):
        fig.add_trace(go.Heatmap(
            z=m.values, x=m.columns, y=m.index, colorscale=ESCALA, zmid=100, zmin=100 - dev, zmax=100 + dev,
            showscale=(i == 2), colorbar=dict(title=capa),
            hovertemplate=f"{titulo_x}: %{{x:.2f}}<br>{titulo_y}: %{{y:.2f}}<br>{capa}: %{{z:.0f}}<extra></extra>"),
            row=1, col=i)
        x, y = marcas[nombre]
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers", name="Tu pitch", showlegend=False,
            marker=dict(size=12, color=TINTA, line=dict(color=SUPERFICIE, width=2)),
            hovertemplate=f"Tu pitch<br>{titulo_x}: %{{x:.2f}}<br>{titulo_y}: %{{y:.2f}}<extra></extra>"),
            row=1, col=i)
        if zona:   # zona de strike aproximada
            fig.add_shape(type="rect", x0=-0.83, x1=0.83, y0=1.5, y1=3.5, line=dict(color=TINTA, width=1.5),
                          row=1, col=i)
        fig.update_xaxes(title_text=titulo_x, row=1, col=i)
        fig.update_yaxes(title_text=titulo_y, row=1, col=i)
    fig.update_layout(height=460, margin=dict(l=10, r=10, t=40, b=10))
    return fig


tab_mov, tab_zona, tab_leer = st.tabs(["Mapa de movimiento (Stuff+)", "Mapa de zona (Pitching+)", "Cómo leerlo"])

with tab_mov:
    st.write("Cómo cambiaría el Stuff+ si el pitch tuviera otro movimiento, con todo lo demás igual. "
             "Rojo: más efectivo que el promedio. Azul: menos efectivo. El punto negro es tu pitch.")
    mapas = {nombre: sim.mapa_movimiento(modelos["Stuff+"], v, cats) for nombre, v in versiones.items()}
    marcas = {nombre: (v["hb"].iloc[0], v["ivb"].iloc[0]) for nombre, v in versiones.items()}
    st.plotly_chart(dos_mapas(mapas, marcas, "HB de Trackman (pulg.)", "IVB (pulg.)", "Stuff+"),
                    use_container_width=True)

with tab_zona:
    st.write("Dónde conviene tirar este pitch en este conteo, contra este bateador. "
             "El rectángulo es la zona de strike aproximada; a la derecha es adentro para el bateador.")
    mapas = {nombre: sim.mapa_zona(modelos["Pitching+"], v, cats) for nombre, v in versiones.items()}
    marcas = {nombre: (loc_adentro, loc_alto) for nombre in versiones}
    st.plotly_chart(dos_mapas(mapas, marcas, "Adentro (+) o afuera (-) (pies)", "Altura (pies)", "Pitching+",
                              zona=True), use_container_width=True)

with tab_leer:
    st.markdown("""
- **Stuff+** califica solo la física del pitch al salir de la mano: velocidad, movimiento, giro, punto de salida,
  extensión y la diferencia contra su recta. No ve dónde cruzó el home.
- **Location+** califica solo la ubicación, con el conteo y el lado del bateador.
- **Pitching+** junta las dos. Es la capa que mejor predice las carreras que va a permitir un pitcher.
- **Harp Helú contra el nivel del mar:** el movimiento del pitch se escala por tipo de pitch con lo que medimos en
  pitchers que lanzaron en los dos parques. Por ejemplo, la recta conserva cerca del 78% de su IVB en la altura,
  casi lo mismo que la densidad del aire (80%). La velocidad y el giro no cambian.
- Cada capa se mide contra el promedio de su parque. Para comparar parques en carreras, usa la columna de
  carreras ahorradas.
- **Límites:** los datos solo dicen si un parque es de altitud extrema, media o sin altitud, así que "Harp Helú"
  es la categoría de altitud extrema. El simulador muestra calificaciones del modelo; no contiene datos de lanzamientos.
""")
