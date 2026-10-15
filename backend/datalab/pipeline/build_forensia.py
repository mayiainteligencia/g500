#!/usr/bin/env python3
"""Forensia electoral — detección de desviaciones estadísticas, 2024.

    backend/datalab/venv/bin/python backend/datalab/pipeline/build_forensia.py
    backend/datalab/venv/bin/python backend/datalab/pipeline/build_forensia.py --autocomprobar

Séptimo pipeline. Salida: frontend/data/electoral/forensia_2024.json

LO PRIMERO, PORQUE CONDICIONA TODO LO DEMÁS
───────────────────────────────────────────
Una desviación estadística NO es una acusación. Este pipeline mide distancia
respecto a la mediana de secciones comparables; eso es todo lo que mide. Una
sección puede estar lejos de la mediana por geografía, por composición, por el
día que hizo, o por nada en particular: en 542 secciones, unas cuantas caen
lejos por puro azar.

Por eso el semáforo tiene una regla estructural, no de redacción:

    El nivel ROJO no se puede alcanzar por estadística.
    Sólo lo activa evidencia documental — una resolución del Tribunal.

Si el rojo se pudiera alcanzar con un umbral, tarde o temprano alguien leería
un |z| alto como prueba de algo. Cerrarlo por diseño es más fiable que
cerrarlo por advertencia.

LA VERDAD-TERRENO NO CALIBRA EL DETECTOR, Y ESO ES UN HALLAZGO
──────────────────────────────────────────────────────────────
El Tribunal Electoral del Estado anuló casillas en tres distritos
(TEEC/JIN/DIP/1, 2 y 5/2024). Parecía el caso de prueba ideal: si el detector
no marca esas secciones, está mal calibrado. Al revisarlo:

  · Las sentencias anulan casillas identificadas por SECCIÓN: 50B, 68B, 78B
    (distrito 4), 99B (distrito 5), 1B y 122S (distrito 7).
  · CINCO de esas seis secciones —1, 50, 68, 78 y 99— NO TIENEN RESULTADO
    PUBLICADO. Sus votos se anularon, así que no hay patrón que analizar. El
    detector no puede marcarlas porque la evidencia se removió.
  · La única que sobrevive es la 122, y es estadísticamente ordinaria:
    |z| < 1 en los tres indicadores. Participación 70.1% (percentil 68),
    voto nulo 2.3% (percentil 26), ganador 44.6% (percentil 28).

Conclusión: NINGÚN umbral, por bien calibrado que esté, marcaría la 122. Su
casilla especial se anuló por causa documental, no por su patrón de voto.

Eso no invalida el detector: dice que **anomalía estadística y anulación
jurídica miden cosas distintas**. Una casilla se anula por irregularidades de
procedimiento, y el procedimiento no deja huella en el reparto de votos.

Lo que sí aporta la verdad-terreno es un detector aparte y exacto: una sección
que está en el catálogo del INE y no tiene resultado es una sección cuyos
votos se anularon. Ése es el canal documental, con precisión del 100%.

LO QUE NO SE MIDE, Y POR QUÉ
────────────────────────────
La página de forensia prometía "variabilidad PREP vs Cómputos". NO HAY DATOS
DE PREP en el repositorio: ni un archivo, ni una columna. Ese indicador se
retira en vez de rellenarse. Es, además, el más útil de todos para esto —
queda pedido en la salida.

Tampoco se hace análisis de dígitos (Benford, último dígito). Requiere los
votos por CASILLA y sólo tenemos agregado por sección: aplicarlo a 542 sumas
de tres o cuatro casillas daría una prueba sin potencia y con apariencia de
rigor.
"""

import argparse
import json
import pathlib
import re
import statistics

RAIZ = pathlib.Path(__file__).resolve().parents[3]
ELECTORAL = RAIZ / "frontend/data/electoral"
GEO = RAIZ / "frontend/data/geo"
SALIDA = ELECTORAL / "forensia_2024.json"
SALIDA_GEO = GEO / "casillas_anuladas_2024.geojson"

# LA CAUSAL NO ESTÁ EN LA FUENTE. Las notas del cómputo dicen "anuladas por el
# Tribunal bajo la sentencia X" y nada más. El motivo —presión al electorado,
# violencia, recepción por persona no facultada, error en el cómputo— sólo vive
# en el texto de la sentencia, que no está en el repositorio. Se publica el
# hueco: un punto rojo que insinúe un motivo que nadie leyó es peor que no
# tener el punto.
CAUSAL = ("No documentada en esta fuente. La nota del cómputo cita la "
          "sentencia pero no su motivo; para saber por qué se anuló hay que "
          "leer el expediente en el Tribunal Electoral del Estado.")

# ── Criterio de "atípico" ───────────────────────────────────────────────────
# Todo sale de la distribución de las 542 secciones. Ningún número redondo.
#
# 1. ESTRATIFICAR POR TAMAÑO. Las secciones chicas varían mucho más que las
#    grandes: la desviación de participación es 14.2 en el quintil más chico y
#    9.5 en el más grande. Un umbral único marcaría a las chicas por pequeñas,
#    no por atípicas. Se compara cada sección contra las de su propio tamaño.
#
# 2. MEDIANA Y MAD, NO MEDIA Y DESVIACIÓN. La desviación estándar la inflan
#    los propios valores extremos que se buscan — es el efecto de
#    enmascaramiento: unos pocos atípicos ensanchan la vara con la que se los
#    mide y dejan de parecer atípicos. La mediana y la desviación absoluta
#    mediana (MAD) no se mueven con ellos.
#
# 3. EL FACTOR 0.6745. Para datos normales, MAD × 1/0.6745 ≈ desviación
#    estándar. Multiplicar por 0.6745 deja el z robusto en la misma escala que
#    un z de toda la vida, así que "|z| > 3" significa lo mismo de siempre.
QUINTILES = 5
FACTOR_MAD = 0.6745

# Los cortes salen de mirar la distribución del |z| resultante: con 2.5 y 3.5
# el reparto queda en ~91% / ~5% / ~3%. No son redondos por casualidad — son
# el punto donde la cola se separa del cuerpo en estos datos.
CORTE_AMARILLO = 2.5
CORTE_NARANJA = 3.5

# El copy de cada nivel. Describe LO QUE SE MIDIÓ, no lo que podría significar.
# Ninguno insinúa intención, irregularidad ni delito: el rojo es el único que
# afirma algo, y sólo porque lo respalda una sentencia.
NIVELES = {
    "verde": {
        "etiqueta": "Dentro de lo esperado",
        "descripcion": "Los tres indicadores caen donde caen las secciones de "
                       "su mismo tamaño.",
        "color": "--status-success",
    },
    "amarillo": {
        "etiqueta": "Desviación moderada",
        "descripcion": "Algún indicador se aparta de la mediana de su estrato "
                       "más de lo habitual. En 542 secciones esto ocurre por "
                       "azar en varias decenas: es un dato de contexto, no un "
                       "hallazgo.",
        "color": "--sev-media",
    },
    "naranja": {
        "etiqueta": "Desviación pronunciada",
        "descripcion": "Algún indicador está lejos de la mediana de su "
                       "estrato. Señala dónde mirar si se va a revisar algo; "
                       "no dice que haya nada que encontrar.",
        "color": "--sev-alta",
    },
    "rojo": {
        "etiqueta": "Con resolución del Tribunal",
        "descripcion": "Tiene casillas anuladas por sentencia firme. Esto es "
                       "un hecho documental, no un resultado del análisis "
                       "estadístico.",
        "color": "--sev-critica",
        "solo_documental": True,
    },
}

INDICADORES = {
    "participacion": "Participación: votación total ÷ lista nominal",
    "nulos_pct": "Voto nulo: votos nulos ÷ votación total",
    "pct_ganador": "Concentración: votos del primer lugar ÷ votos válidos",
}


def cargar():
    sec = json.loads((ELECTORAL / "resultados_seccion_2024.json").read_text())
    cat_p = ELECTORAL / "secciones_catalogo_2026.json"
    cat = json.loads(cat_p.read_text()) if cat_p.exists() else None
    return sec, cat


def sentencias(meta):
    """Secciones con casillas anuladas, leídas de las notas del Tribunal.

    Las notas traen las casillas como '50B, 68B y 78B': el número es la
    SECCIÓN y la letra el tipo de casilla. Se extraen con expresión regular
    porque el texto viene tal cual del cómputo, sin estructura.
    """
    fuera = {}
    for n in meta.get("notas_tribunal", []):
        nota = n.get("nota", "")
        exp = re.search(r"TEEC/JIN/DIP/\d+/\d+", nota)
        # 'Casillas 50B, 68B y 78B anuladas' -> 50, 68, 78
        tramo = re.search(r"Casillas?\s+(.+?)\s+anuladas", nota)
        casillas = re.findall(r"\b(\d+)([A-Z])\b", tramo.group(1)) if tramo else []
        for num, tipo in casillas:
            fuera.setdefault(num, {
                "seccion": num,
                "distrito_local": n.get("distrito_local"),
                "casillas_anuladas": [],
                "expediente": exp.group(0) if exp else None,
                "nota": nota.strip(),
            })["casillas_anuladas"].append(num + tipo)
    return fuera


def geo_anuladas(anuladas):
    """Sitúa las casillas anuladas para poder pintarlas en rojo en el mapa.

    El encarte del INE publica un punto por SITIO —un inmueble puede alojar
    varias casillas—, así que el cruce es por sección Y por tipo: la 122 tiene
    dos sitios y sólo se anuló el de la casilla especial.

    No todas caen en el mapa. El encarte no trae coordenadas: se geolocalizan
    cruzando el inmueble contra el catálogo CCT, y 170 de 585 sitios no cruzan.
    Las secciones que quedan fuera se declaran en la metadata en vez de
    ubicarse a ojo; un punto rojo en el lugar equivocado es peor que ninguno.
    """
    sitios = json.loads((GEO / "casillas_2024.geojson").read_text())["features"]
    feats = []
    for ft in sitios:
        p = ft["properties"]
        d = anuladas.get(p["seccion"])
        if not d:
            continue
        tipos = [t.strip() for t in (p.get("tipos") or "").split(",") if t.strip()]
        aqui = [c for c in d["casillas_anuladas"] if c[len(p["seccion"]):] in tipos]
        if not aqui:
            continue
        feats.append({
            "type": "Feature",
            "geometry": ft["geometry"],
            "properties": {
                "seccion": p["seccion"],
                "casillas_anuladas": ", ".join(sorted(aqui)),
                "expediente": d["expediente"],
                "distrito_local": d["distrito_local"],
                "causal": CAUSAL,
                "nota_computo": d["nota"],
                "inmueble": p.get("inmueble"),
                "ubicacion": p.get("ubicacion"),
                "nombre_municipio": p.get("nombre_municipio"),
                "nombre_localidad": p.get("nombre_localidad"),
                "estatus_ubicacion": p.get("estatus_ubicacion"),
            },
        })

    ubicadas = {f["properties"]["seccion"] for f in feats}
    sin_coordenada = sorted(set(anuladas) - ubicadas, key=int)
    return {
        "type": "FeatureCollection",
        "metadata": {
            "que_es": "Casillas anuladas por sentencia firme del Tribunal "
                      "Electoral del Estado de Campeche en el proceso 2024, "
                      "situadas en el sitio donde se instalaron.",
            "no_es": "Un mapa de riesgo ni de violencia. Marca dónde el "
                     "Tribunal anuló una casilla, no dónde ocurrió un "
                     "incidente: la nota del cómputo no dice qué pasó.",
            "causal": CAUSAL,
            "secciones_citadas": sorted(anuladas, key=int),
            "secciones_sin_coordenada": sin_coordenada,
            "por_que_faltan":
                "El encarte del INE no publica coordenadas. El sitio que no "
                "cruza contra el catálogo CCT se queda sin geometría, y esas "
                "secciones no se pueden dibujar.",
            "advertencia": "Ubicaciones del proceso 2024. NO son las casillas "
                           "de 2027.",
            "fuente": "IEEC — Cómputos distritales, diputaciones locales MR "
                      "2024 (notas del Tribunal) · INE — Encarte del Proceso "
                      "Electoral Federal 2023-2024 (ubicación)",
            "fecha_corte": "2024-06",
            "procedencia": "dato",
            "generado_por": "backend/datalab/pipeline/build_forensia.py",
        },
        "features": feats,
    }


def z_robusto(valores, indices):
    """z robusto dentro de un estrato: (x − mediana) / MAD, escalado."""
    sub = [valores[i] for i in indices]
    med = statistics.median(sub)
    mad = statistics.median([abs(x - med) for x in sub])
    if mad == 0:
        # Sin dispersión no hay atípicos que medir. Devolver ceros es correcto:
        # dividir entre cero daría infinitos que luego se leerían como alarma.
        return {i: 0.0 for i in indices}
    return {i: FACTOR_MAD * (valores[i] - med) / mad for i in indices}


def estratos(lista_nominal):
    """Índices agrupados por quintil de lista nominal."""
    orden = sorted(range(len(lista_nominal)), key=lambda i: lista_nominal[i])
    tam = len(orden) / QUINTILES
    grupos = [[] for _ in range(QUINTILES)]
    for pos, i in enumerate(orden):
        grupos[min(QUINTILES - 1, int(pos // tam))].append(i)
    return grupos


def analizar(sec, anuladas):
    claves = sorted(sec["secciones"], key=int)
    reg = [sec["secciones"][k] for k in claves]

    ln = [r["lista_nominal"] for r in reg]
    vals = {
        "participacion": [r["participacion"] or 0.0 for r in reg],
        "nulos_pct": [r["nulos_pct"] or 0.0 for r in reg],
        "pct_ganador": [(r["ganador_votos"] / r["validos"] * 100)
                        if r["validos"] else 0.0 for r in reg],
    }

    grupos = estratos(ln)
    z = {k: [0.0] * len(reg) for k in vals}
    for g in grupos:
        for k, v in vals.items():
            for i, zz in z_robusto(v, g).items():
                z[k][i] = zz

    filas, conteo = [], {n: 0 for n in NIVELES}
    for i, clave in enumerate(claves):
        zmax = max(abs(z[k][i]) for k in vals)
        if clave in anuladas:
            nivel = "rojo"
        elif zmax >= CORTE_NARANJA:
            nivel = "naranja"
        elif zmax >= CORTE_AMARILLO:
            nivel = "amarillo"
        else:
            nivel = "verde"
        conteo[nivel] += 1

        # Cero votos con casilla instalada NO es "participación baja": es
        # ausencia de votación. Meterlo en el mismo saco que una sección de
        # 17% de participación mezcla dos fenómenos distintos — uno es un
        # patrón de voto y el otro es un hueco en el dato. Se marca aparte.
        sin_votacion = reg[i]["total"] == 0

        estrato = next(e for e, g in enumerate(grupos) if i in g)
        filas.append({
            "seccion": clave,
            "cve_mun": reg[i].get("cve_mun"),
            "distrito_local": reg[i].get("distrito_local"),
            "lista_nominal": ln[i],
            "estrato": estrato + 1,
            "nivel": nivel,
            "z_max": round(zmax, 2),
            "valores": {k: round(vals[k][i], 2) for k in vals},
            "z": {k: round(z[k][i], 2) for k in vals},
            "documental": anuladas.get(clave),
            "sin_votacion_registrada": sin_votacion,
            "nota_dato": ("La sección tiene lista nominal y casilla, y cero "
                          "votos registrados. No es participación baja: es "
                          "ausencia de votación. Puede ser una casilla que no "
                          "se instaló o un hueco en el cómputo; con estos "
                          "archivos no se puede distinguir.") if sin_votacion else None,
        })

    return filas, conteo, grupos, ln, vals


def calibracion(filas, anuladas, sec):
    """Qué dice la verdad-terreno sobre el detector. Se publica entero."""
    con_datos = {f["seccion"] for f in filas}
    citadas = set(anuladas)
    sin_datos = sorted(citadas - con_datos, key=int)
    presentes = sorted(citadas & con_datos, key=int)

    detalle = []
    for s in presentes:
        f = next(x for x in filas if x["seccion"] == s)
        detalle.append({
            "seccion": s, "z_max": f["z_max"], "z": f["z"],
            "valores": f["valores"],
            "seria_atipica_por_estadistica": f["z_max"] >= CORTE_AMARILLO,
        })

    return {
        "secciones_citadas_en_sentencias": sorted(citadas, key=int),
        "sin_resultado_publicado": sin_datos,
        "con_resultado_publicado": presentes,
        "detalle": detalle,
        "el_detector_las_marcaria": any(
            d["seria_atipica_por_estadistica"] for d in detalle),
        "lectura":
            "De las secciones con casillas anuladas, la mayoría no tiene "
            "resultado publicado: sus votos se anularon, así que no hay patrón "
            "que analizar. La que sí lo tiene es estadísticamente ordinaria. "
            "Ningún umbral la marcaría, y eso NO significa que el umbral esté "
            "mal: significa que una casilla se anula por irregularidades de "
            "procedimiento, y el procedimiento no deja huella en el reparto de "
            "votos. Anomalía estadística y anulación jurídica miden cosas "
            "distintas.",
        "consecuencia_de_diseno":
            "Por eso el canal documental es independiente del estadístico y es "
            "el único que puede encender el rojo.",
    }


def verificar(filas, conteo, anuladas):
    if sum(conteo.values()) != len(filas):
        raise SystemExit("El conteo por nivel no suma el total de secciones.")

    # El rojo SÓLO por evidencia documental. Es la regla estructural del
    # semáforo: si alguna vez se enciende por estadística, el diseño se rompió.
    for f in filas:
        if f["nivel"] == "rojo" and not f["documental"]:
            raise SystemExit(
                f"Sección {f['seccion']} en rojo sin respaldo documental. El "
                f"rojo no se puede alcanzar por estadística.")
        if f["documental"] and f["nivel"] != "rojo":
            raise SystemExit(
                f"Sección {f['seccion']} tiene casillas anuladas y no está en "
                f"rojo.")

    # Los cortes tienen que estar ordenados y ser coherentes con el nivel.
    for f in filas:
        if f["nivel"] == "verde" and f["z_max"] >= CORTE_AMARILLO:
            raise SystemExit(f"Sección {f['seccion']}: verde con z alto.")
        if f["nivel"] == "naranja" and f["z_max"] < CORTE_NARANJA:
            raise SystemExit(f"Sección {f['seccion']}: naranja con z bajo.")

    # La mayoría tiene que quedar en verde. Si un detector marca a la mitad
    # del universo, no está detectando: está describiendo lo normal.
    if conteo["verde"] / len(filas) < 0.80:
        raise SystemExit(
            f"Sólo {conteo['verde']/len(filas)*100:.1f}% en verde. Con estos "
            f"cortes el detector marca demasiado: revisa los umbrales.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--autocomprobar", action="store_true")
    args = ap.parse_args()
    if args.autocomprobar:
        return autocomprobar()

    sec, cat = cargar()
    anuladas = sentencias(sec["metadata"])
    filas, conteo, grupos, ln, vals = analizar(sec, anuladas)
    verificar(filas, conteo, anuladas)
    cal = calibracion(filas, anuladas, sec)
    sin_vot = [f["seccion"] for f in filas if f["sin_votacion_registrada"]]
    geo = geo_anuladas(anuladas)

    print(f"{len(filas)} secciones · {QUINTILES} estratos por lista nominal")
    for n, c in conteo.items():
        print(f"  {NIVELES[n]['etiqueta']:28} {c:3} ({c/len(filas)*100:5.1f}%)")

    print(f"\nVERDAD-TERRENO — {len(cal['secciones_citadas_en_sentencias'])} "
          f"secciones citadas en sentencias del TEEC")
    print(f"  sin resultado publicado (votos anulados): {cal['sin_resultado_publicado']}")
    print(f"  con resultado publicado: {cal['con_resultado_publicado']}")
    for d in cal["detalle"]:
        print(f"    sección {d['seccion']}: |z| max {d['z_max']} → "
              f"{'la marcaría' if d['seria_atipica_por_estadistica'] else 'NO la marcaría'}")

    if sin_vot:
        print(f"\nSIN VOTACIÓN REGISTRADA: {sin_vot} — no es participación "
              f"baja, es ausencia de votación. Se declara aparte.")

    top = sorted(filas, key=lambda f: -f["z_max"])[:5]
    print("\nLAS CINCO MÁS ALEJADAS DE SU ESTRATO")
    for f in top:
        peor = max(f["z"], key=lambda k: abs(f["z"][k]))
        print(f"  sección {f['seccion']:5} Q{f['estrato']} · {NIVELES[f['nivel']]['etiqueta']:24} "
              f"|z| {f['z_max']:5.2f} por {peor} = {f['valores'][peor]}")

    SALIDA.write_text(json.dumps({
        "metadata": {
            "procedencia": "calculo",
            "que_es": "Distancia de cada sección respecto a la mediana de las "
                      "secciones de su mismo tamaño, en tres indicadores.",
            "no_es": "Una acusación. Una desviación estadística no implica "
                     "irregularidad, y menos aún intención. En 542 secciones, "
                     "varias decenas caen lejos de la mediana por azar.",
            "metodo": {
                "estratificacion": f"{QUINTILES} quintiles de lista nominal",
                "por_que_estratificar":
                    "Las secciones chicas varían mucho más (sd de participación "
                    "14.2 en el quintil menor contra 9.5 en el mayor). Un "
                    "umbral único las marcaría por pequeñas, no por atípicas.",
                "estadistico": "z robusto = 0.6745 × (x − mediana) ÷ MAD",
                "por_que_mad":
                    "La desviación estándar la inflan los propios valores "
                    "extremos que se buscan (enmascaramiento). La mediana y la "
                    "desviación absoluta mediana no se mueven con ellos.",
                "factor": FACTOR_MAD,
                "cortes": {"amarillo": CORTE_AMARILLO, "naranja": CORTE_NARANJA},
                "por_que_esos_cortes":
                    "Salen de mirar dónde se separa la cola del cuerpo en esta "
                    "distribución: dejan ~91% en verde, ~5% en amarillo y ~3% "
                    "en naranja.",
            },
            "regla_del_rojo":
                "El nivel rojo NO se puede alcanzar por estadística: sólo lo "
                "activa una resolución del Tribunal. Está cerrado por diseño y "
                "verificado en cada corrida, no por redacción.",
            "indicadores": INDICADORES,
            "secciones_sin_votacion": sin_vot,
            "nota_sin_votacion":
                "Secciones con lista nominal y casilla pero cero votos. No es "
                "participación baja sino ausencia de votación, que es un "
                "fenómeno distinto: se declara aparte para no mezclarlo con "
                "los patrones de voto.",
            "no_medido": {
                "prep_vs_computos":
                    "NO HAY DATOS DE PREP en el repositorio. El indicador se "
                    "retira en vez de rellenarse. Es el más útil para esto: "
                    "queda pedido.",
                "analisis_de_digitos":
                    "Benford y último dígito requieren votos por CASILLA. Sólo "
                    "hay agregado por sección; aplicarlo a sumas de tres o "
                    "cuatro casillas daría una prueba sin potencia.",
            },
            "niveles": NIVELES,
            "calibracion_verdad_terreno": cal,
            "fuente": sec["metadata"]["fuente"],
            "fecha_corte": sec["metadata"]["fecha_corte"],
            "generado_por": "backend/datalab/pipeline/build_forensia.py",
        },
        "conteo": conteo,
        "secciones": filas,
    }, ensure_ascii=False), encoding="utf-8")
    SALIDA_GEO.write_text(json.dumps(geo, ensure_ascii=False), encoding="utf-8")

    print(f"\nCASILLAS ANULADAS EN EL MAPA — {len(geo['features'])} sitios de "
          f"{len(anuladas)} secciones citadas")
    for f in geo["features"]:
        pr = f["properties"]
        print(f"  {pr['casillas_anuladas']:12} {pr['inmueble']} · {pr['expediente']}")
    if geo["metadata"]["secciones_sin_coordenada"]:
        print(f"  sin coordenada (no se pueden dibujar): "
              f"{geo['metadata']['secciones_sin_coordenada']}")
    print("  causal: no documentada en la fuente — la nota cita la sentencia, "
          "no el motivo.")

    print(f"\nListo. {SALIDA.relative_to(RAIZ)}")
    print(f"       {SALIDA_GEO.relative_to(RAIZ)}")


def autocomprobar():
    sec, cat = cargar()
    anuladas = sentencias(sec["metadata"])
    filas, conteo, grupos, ln, vals = analizar(sec, anuladas)
    verificar(filas, conteo, anuladas)

    # Las sentencias se leen bien: seis secciones, con su expediente.
    assert set(anuladas) == {"1", "50", "68", "78", "99", "122"}, sorted(anuladas)
    assert all(a["expediente"] for a in anuladas.values())

    # Los estratos reparten a todos y ninguno queda vacío.
    assert sum(len(g) for g in grupos) == len(filas)
    assert all(g for g in grupos)

    # El z robusto de la mediana de un estrato es 0 por construcción.
    z = z_robusto([1, 2, 3, 4, 5], [0, 1, 2, 3, 4])
    assert abs(z[2]) < 1e-9, z

    # Sin dispersión no hay atípicos: todos ceros, no infinitos.
    z = z_robusto([7.0] * 9, list(range(9)))
    assert all(v == 0.0 for v in z.values())

    # El MAD resiste lo que la desviación estándar no: un valor extremo no
    # cambia la vara con la que se mide al resto.
    base = [10.0] * 20 + [10.5] * 20
    con_extremo = base + [1000.0]
    idx = list(range(len(con_extremo)))
    zz = z_robusto(con_extremo, idx)
    assert abs(zz[len(con_extremo) - 1]) > 100, "el extremo debería destacar"
    assert all(abs(zz[i]) < 5 for i in range(40)), "el resto no debería moverse"

    # Cero votos se marca aparte y no se confunde con participación baja.
    ceros = [f for f in filas if f["sin_votacion_registrada"]]
    assert all(f["valores"]["participacion"] == 0 for f in ceros)
    assert all(f["nota_dato"] for f in ceros)

    # La regla estructural: ninguna sección llega a rojo sin documento.
    rojos = [f for f in filas if f["nivel"] == "rojo"]
    assert rojos and all(f["documental"] for f in rojos)

    # El mapa: cada punto lleva expediente, y ninguno inventa una causal. El
    # motivo no está en la fuente; si algún día aparece, tendrá que entrar por
    # el texto de la sentencia y no por deducción.
    geo = geo_anuladas(anuladas)
    props = [f["properties"] for f in geo["features"]]
    assert props, "ninguna casilla anulada se pudo situar"
    assert all(pr["expediente"] for pr in props)
    assert all(pr["causal"] == CAUSAL for pr in props)
    assert {pr["seccion"] for pr in props} | set(
        geo["metadata"]["secciones_sin_coordenada"]) == set(anuladas)

    print(f"OK · {len(filas)} secciones · "
          + " · ".join(f"{n} {c}" for n, c in conteo.items())
          + f" · {len(anuladas)} con sentencia")
    print(f"     {len(props)} sitios anulados situados en el mapa · "
          f"{len(geo['metadata']['secciones_sin_coordenada'])} secciones sin coordenada")


if __name__ == "__main__":
    main()
