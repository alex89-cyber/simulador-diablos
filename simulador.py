"""Lógica del simulador de pitcheo Diablos Rojos (sin Streamlit, para poder probarla en Colab).

Recibe el Trackman de un pitch tal cual lo teclea el coach, lo convierte en las features del modelo,
lo califica con Stuff+, Location+ y Pitching+, y lo lleva entre Harp Helú y el nivel del mar.
Las funciones `predecir_final` y `armar` son copia exacta de Stuff_Final_v2.ipynb (secciones 5 y 13).
"""
import numpy as np
import pandas as pd
import joblib

ARCHIVOS = {"Stuff+": "modelo_final.pkl", "Location+": "modelo_location.pkl", "Pitching+": "modelo_pitching.pkl"}
PARQUES = {"Harp Helú": "Extreme Altitude", "Nivel del mar": "No Altitude"}
RECTAS = ["Four-Seam", "Sinker"]
CONTEOS = [f"{b}-{s}" for b in range(4) for s in range(3)]


def cargar(carpeta="modelos"):
    """Los tres modelos guardados y las razones de movimiento por tipo de pitch (sección 12 del cuaderno)."""
    modelos = {capa: joblib.load(f"{carpeta}/{archivo}") for capa, archivo in ARCHIVOS.items()}
    razones = pd.read_csv(f"{carpeta}/razones_altitud.csv", index_col=0)
    return modelos, razones


def categorias(modelos):
    """Tipos de pitch como los vio el modelo al entrenar."""
    return list(modelos["Stuff+"]["clf"].booster_.pandas_categorical[0])


def predecir_final(m, test):
    """xRV, baselines y probabilidades para lanzamientos nuevos."""
    test = test[list(dict.fromkeys(m["features"] + ["count", "altitude_category"]))].copy()
    test["clave"] = test["count"].astype(str) + "_" + test["altitude_category"].astype(str)
    pred_conteo = test["count"].map(m["base_conteo"]).astype(float)
    pred_base2 = test["clave"].map(m["base2"]).fillna(pred_conteo)
    X = test[m["features"]]
    probs = pd.DataFrame(m["clf"].predict_proba(X), columns=m["clf"].classes_, index=test.index)
    otros = ["bola", "foul", "strike_cantado", "whiff"]
    V_test = m["V"].loc[test["count"].astype(str), otros].values
    p_tipo = pd.DataFrame(m["clf_tipo"].predict_proba(X),
                          columns=["p_" + c for c in m["clf_tipo"].classes_], index=test.index)
    D_test = m["D"].reindex(test["altitude_category"].astype(str)).fillna(m["general"]).values
    contacto_base = test["clave"].map(m["base_contacto"]).fillna(
        test["count"].map(m["base_contacto_conteo"]).astype(float))
    contacto = contacto_base.values + (p_tipo.values * D_test).sum(axis=1)
    xrv = (probs[otros].values * V_test).sum(axis=1) + probs["en_juego"].values * contacto
    salida = pd.DataFrame({"xrv": xrv, "base2": pred_base2.values, "conteo": pred_conteo.values},
                          index=test.index)
    return salida.join(probs.add_prefix("p_")).join(p_tipo)


def calificar(m, x):
    """Calificación 100 + 10·z por lanzamiento y carreras que ahorra cada 100 pitches contra el promedio del conteo."""
    pred = predecir_final(m, x)
    media, sd = m["escala"]["lanzamiento"]
    nota = 100 + 10 * (pred["base2"] - pred["xrv"] - media) / sd
    carreras = -(pred["xrv"] - pred["conteo"]) * 100
    return nota, carreras, pred


def armar(e, cats):
    """e: tabla con el Trackman del pitch, su recta principal, el conteo, la ubicación y el parque."""
    zurdo = e["mano"] == "Left"
    signo = np.where(zurdo, -1, 1)
    x = pd.DataFrame(index=e.index)
    x["RelSpeed"] = e["velo"]
    x["InducedVertBreak"] = e["ivb"]
    x["HorzBreak_norm"] = e["hb"] * signo
    x["SpinRate"] = e["spin"]
    x["RelHeight"] = e["alto"]
    x["RelSide_norm"] = e["lado"] * signo
    x["Extension"] = e["extension"]
    x["pitch_type"] = pd.Categorical(e["tipo"], categories=cats)
    x["mismo_lado"] = (e["mano"] == e["bateador"]).astype(int)
    x["SpinAxis_norm"] = np.where(zurdo, 360 - e["eje"], e["eje"])
    x["angulo_brazo"] = np.degrees(np.arctan2(e["alto"], x["RelSide_norm"].abs()))
    x["bolas"] = e["conteo"].str[0].astype(int)
    x["strikes"] = e["conteo"].str[2].astype(int)
    x["dif_velo_p"] = e["velo"] - e["recta_velo"]
    x["dif_ivb_p"] = e["ivb"] - e["recta_ivb"]
    x["dif_hb_p"] = x["HorzBreak_norm"] - e["recta_hb"] * signo
    x["loc_altura"] = e["loc_alto"]
    x["loc_adentro"] = np.where(e["bateador"] == "Right", e["loc_lado"], -e["loc_lado"])
    x["count"] = e["conteo"]
    x["altitude_category"] = e["parque"]
    return x


def mover(e, razones, destino):
    """Lleva el Trackman de un parque al otro: en la altura el movimiento se escala por tipo de pitch.

    Es la misma transformación que `a_la_altura` del cuaderno, pero sobre los números que teclea el coach.
    Del nivel del mar a Harp Helú multiplica por la razón; de Harp Helú al nivel del mar divide.
    La velocidad y el giro no cambian (sus razones son 1.00).
    """
    n = e.copy()
    rt = razones.reindex(n["tipo"]).fillna(razones.mean())
    rt.index = n.index
    r_fb = razones.loc[RECTAS].mean()
    sentido = 1 if destino == PARQUES["Harp Helú"] else -1
    potencia = pd.Series(np.where(n["parque"] == destino, 0, sentido), index=n.index)
    n["ivb"] = n["ivb"] * rt["InducedVertBreak"] ** potencia
    n["hb"] = n["hb"] * rt["HorzBreak_norm"] ** potencia
    n["recta_ivb"] = n["recta_ivb"] * r_fb["InducedVertBreak"] ** potencia
    n["recta_hb"] = n["recta_hb"] * r_fb["HorzBreak_norm"] ** potencia
    n["parque"] = destino
    return n


def evaluar(modelos, razones, e):
    """Las tres capas del pitch en Harp Helú y al nivel del mar. e es una tabla de una fila."""
    cats = categorias(modelos)
    filas, versiones = [], {}
    for nombre, codigo in PARQUES.items():
        n = mover(e, razones, codigo)
        versiones[nombre] = n
        x = armar(n, cats)
        fila = {"parque": nombre, "IVB": n["ivb"].iloc[0], "HB": n["hb"].iloc[0]}
        for capa, m in modelos.items():
            nota, carreras, pred = calificar(m, x)
            fila[capa] = nota.iloc[0]
            fila[f"carreras_{capa}"] = carreras.iloc[0]
            if capa == "Stuff+":
                fila["p_whiff"] = pred["p_whiff"].iloc[0] * 100
                fila["p_en_juego"] = pred["p_en_juego"].iloc[0] * 100
        filas.append(fila)
    return pd.DataFrame(filas).set_index("parque"), versiones


def mapa_movimiento(m, e, cats, rango=10, paso=1.0):
    """Calificación en una rejilla de IVB y HB alrededor del pitch, con todo lo demás igual."""
    ivbs = np.arange(e["ivb"].iloc[0] - rango, e["ivb"].iloc[0] + rango + paso / 2, paso)
    hbs = np.arange(e["hb"].iloc[0] - rango, e["hb"].iloc[0] + rango + paso / 2, paso)
    g = e.loc[e.index.repeat(len(ivbs) * len(hbs))].reset_index(drop=True)
    I, H = np.meshgrid(ivbs, hbs, indexing="ij")
    g["ivb"], g["hb"] = I.ravel(), H.ravel()
    nota, _, _ = calificar(m, armar(g, cats))
    return pd.DataFrame(nota.values.reshape(len(ivbs), len(hbs)), index=ivbs, columns=hbs)


def mapa_zona(m, e, cats, paso=0.25):
    """Calificación en una rejilla de ubicación (altura y adentro-afuera para el bateador), con la física igual."""
    alturas = np.arange(0.5, 4.5 + paso / 2, paso)
    adentro = np.arange(-2.0, 2.0 + paso / 2, paso)
    g = e.loc[e.index.repeat(len(alturas) * len(adentro))].reset_index(drop=True)
    A, D = np.meshgrid(alturas, adentro, indexing="ij")
    g["loc_alto"] = A.ravel()
    lado = np.where(g["bateador"] == "Right", 1, -1)
    g["loc_lado"] = D.ravel() * lado   # loc_adentro positivo = pegado al bateador, de los dos lados
    nota, _, _ = calificar(m, armar(g, cats))
    return pd.DataFrame(nota.values.reshape(len(alturas), len(adentro)), index=alturas, columns=adentro)
