#!/usr/bin/env python3
"""Convierte los insumos electorales 2024 en JSON para el frontend.

    backend/datalab/venv/bin/python backend/datalab/pipeline/build_electoral.py

El código vive aquí, junto al crudo y al venv que lo lee. Las salidas se
escriben en frontend/data/ porque el frontend es estático: no hay servidor que
las sirva, las trae con fetch del propio repo.

Insumos (no se tocan), en backend/datalab/uploads/ResultadosYCasillas/:

  ubicacionCasillas.xlsx   Encarte del Proceso Electoral Federal 2023-2024.
                           Ubicación e integración de mesas directivas.
  DIP MR NN_SEC.xlsx (21)  Resultados a nivel sección de la elección de
                           diputaciones locales de mayoría relativa, uno por
                           distrito local.

Salidas:

  frontend/data/geo/casillas_2024.geojson       sitios de casilla geolocalizados
  frontend/data/electoral/resultados_seccion_2024.json
  frontend/data/electoral/resultados_municipio_2024.json

Dos advertencias que el archivo de salida repite y que no hay que perder:

1. Los nombres de los funcionarios de casilla del encarte se descartan. Son
   datos personales y no aportan nada al mapa.

2. El encarte NO trae coordenadas: sólo un domicilio en texto libre. Las
   coordenadas salen de cruzar el nombre del inmueble contra el catálogo CCT
   de la SEP (escuelas_campeche.geojson). Un sitio que no cruza se queda SIN
   geometría y se contabiliza aparte — no se inventa un punto ni se recorre al
   centroide del municipio.
"""

import argparse
import collections
import hashlib
import json
import pathlib
import re
import sys
import unicodedata
import zipfile
from xml.etree import ElementTree as ET

try:
    import openpyxl
except ImportError:
    sys.exit("Falta openpyxl. Usa backend/datalab/venv/bin/python.")

RAIZ = pathlib.Path(__file__).resolve().parents[3]
ENTRADA = RAIZ / "backend/datalab/uploads/ResultadosYCasillas"
SALIDA_GEO = RAIZ / "frontend/data/geo"
SALIDA = RAIZ / "frontend/data/electoral"

FUENTE_ENCARTE = "INE — Encarte del Proceso Electoral Federal 2023-2024"
FUENTE_RESULTADOS = "IEEC — Cómputos distritales, diputaciones locales MR 2024"
FECHA_CORTE = "2024-06"

# La fila de encabezado no dice qué partido es cada columna: son 16 logotipos
# PNG incrustados en la hoja. Y el número de columnas cambia entre distritos
# (el 20, Palizada, sólo trae 12 contendientes). Así que no se puede fijar el
# orden: cada archivo se lee por su propio dibujo, cruzando el md5 de cada
# logotipo contra esta tabla. Los hashes salieron de abrir las 16 imágenes del
# distrito 01 y verlas una por una.
LOGOS = {
    "53f6f0c774": "PAN", "9ed00dbd2a": "PRI", "dd760eb936": "PRD",
    "0a9b95bdc5": "PT", "218af52a33": "PVEM", "b5aa4ac150": "MC",
    "f48fc80378": "MORENA", "60336feb7f": "PES", "62aadc010f": "CL",
    "3f5509fec9": "EDC", "da00987c48": "MLC", "2d02467301": "PRI-PRD",
    "f73ed3791f": "PT-PVEM-MORENA", "34a09689b1": "PT-PVEM",
    "81336451bc": "PT-MORENA", "2d6a07c7db": "PVEM-MORENA",
}

PARTIDOS = [
    ("PAN", "Partido Acción Nacional"),
    ("PRI", "Partido Revolucionario Institucional"),
    ("PRD", "Partido de la Revolución Democrática"),
    ("PT", "Partido del Trabajo"),
    ("PVEM", "Partido Verde Ecologista de México"),
    ("MC", "Movimiento Ciudadano"),
    ("MORENA", "Morena"),
    ("PES", "Partido Encuentro Solidario Campeche"),
    ("CL", "Campeche Libre"),
    ("EDC", "Espacio Democrático de Campeche"),
    ("MLC", "Movimiento Laborista Campeche"),
    ("PRI-PRD", "Coalición PRI-PRD"),
    ("PT-PVEM-MORENA", "Coalición PT-PVEM-Morena"),
    ("PT-PVEM", "Coalición PT-PVEM"),
    ("PT-MORENA", "Coalición PT-Morena"),
    ("PVEM-MORENA", "Coalición PVEM-Morena"),
]

# Para leer el mapa por ganador hay que sumar el voto del partido y el de sus
# coaliciones. Un municipio pintado "PRI" cuando el PRI fue en coalición con el
# PRD es una lectura falsa del resultado.
BLOQUES = {
    "PAN": ["PAN"],
    "PRI-PRD": ["PRI", "PRD", "PRI-PRD"],
    "MC": ["MC"],
    "SHH": ["PT", "PVEM", "MORENA", "PT-PVEM-MORENA", "PT-PVEM",
            "PT-MORENA", "PVEM-MORENA"],
    "PES": ["PES"],
    "CL": ["CL"],
    "EDC": ["EDC"],
    "MLC": ["MLC"],
}
BLOQUE_NOMBRE = {
    "PAN": "PAN",
    "PRI-PRD": "PRI-PRD",
    "MC": "Movimiento Ciudadano",
    "SHH": "Sigamos Haciendo Historia (PT-PVEM-Morena)",
    "PES": "PES Campeche",
    "CL": "Campeche Libre",
    "EDC": "Espacio Democrático",
    "MLC": "Movimiento Laborista",
}

# El encarte numera los municipios con el orden del INE; el Marco
# Geoestadístico usa otro. Se cruza por nombre normalizado, nunca por número.
CVE_MUN = {
    "CALKINI": "04001", "CAMPECHE": "04002", "CARMEN": "04003",
    "CHAMPOTON": "04004", "HECELCHAKAN": "04005", "HOPELCHEN": "04006",
    "PALIZADA": "04007", "TENABO": "04008", "ESCARCEGA": "04009",
    "CALAKMUL": "04010", "CANDELARIA": "04011", "SEYBAPLAYA": "04012",
    "DZITBALCHE": "04013",
}

# Nombre de presentación. El encarte los trae en mayúsculas y sin acentos
# ("DZITBALCHE "); estos son los del catálogo INEGI y son los que se publican.
NOMBRE_MUN = {
    "04001": "Calkiní", "04002": "Campeche", "04003": "Carmen",
    "04004": "Champotón", "04005": "Hecelchakán", "04006": "Hopelchén",
    "04007": "Palizada", "04008": "Tenabo", "04009": "Escárcega",
    "04010": "Calakmul", "04011": "Candelaria", "04012": "Seybaplaya",
    "04013": "Dzitbalché",
}

ABREV = {"LIC": "LICENCIADO", "LICDA": "LICENCIADA", "PROFR": "PROFESOR",
         "PROF": "PROFESOR", "PROFRA": "PROFESORA", "GRAL": "GENERAL",
         "DR": "DOCTOR", "ING": "INGENIERO", "NUM": "NUMERO", "NO": "NUMERO"}

# Palabras que describen el tipo de plantel, no su nombre. Compararlas infla la
# similitud: dos primarias distintas comparten "ESCUELA PRIMARIA" y nada más.
GENERICAS = {"ESCUELA", "PRIMARIA", "SECUNDARIA", "PREESCOLAR", "JARDIN",
             "NINOS", "TECNICA", "ESTATAL", "FEDERAL", "TELESECUNDARIA",
             "COLEGIO", "INSTITUTO", "CENTRO", "ESCOLAR", "BACHILLERES",
             "DE", "DEL", "LA", "EL", "LOS", "LAS", "Y", "A", "EN"}

# Inmuebles que no son escuela: no tiene caso buscarlos en el catálogo CCT.
NO_ESCUELA = ("DOMICILIO PARTICULAR", "PARQUE", "CANCHA", "MERCADO",
              "CEMENTERIO", "EXPLANADA", "PLAZA", "CASA EJIDAL", "COMISARIA",
              "PALACIO", "SALON", "AUDITORIO", "CENTRO COMUNITARIO",
              "CENTRO SOCIAL", "LOCAL", "TERRENO", "PORTALES", "BODEGA",
              "OFICINA", "BIBLIOTECA", "IGLESIA", "CLINICA", "GIMNASIO",
              "CASA DE", "DELEGACION", "JUNTA", "UNIDAD DEPORTIVA", "DOMO",
              "PARADOR", "TIENDA", "ESTACIONAMIENTO", "ALBERGUE", "COMEDOR")

UMBRAL_CRUCE = 0.55


def norm(s):
    s = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9 ]", " ", s).upper()
    return " ".join(ABREV.get(t, t) for t in s.split())


def distintivo(s):
    """Tokens que identifican al inmueble, sin las palabras de tipo."""
    return frozenset(t for t in norm(s).split() if t not in GENERICAS)


def sin_indice(s):
    """'1) SAN FRANCISCO DE CAMPECHE' -> 'SAN FRANCISCO DE CAMPECHE'"""
    return str(s).split(")", 1)[-1].strip()


def indice(s):
    m = re.match(r"\s*(\d+)\)", str(s))
    return int(m.group(1)) if m else None


# ── Encarte ─────────────────────────────────────────────────────────────────

def leer_encarte():
    ws = openpyxl.load_workbook(ENTRADA / "ubicacionCasillas.xlsx",
                                read_only=True).active
    filas = []
    for i, r in enumerate(ws.iter_rows(values_only=True)):
        if i < 5 or not r[4]:
            continue
        filas.append({
            "distrito_federal": sin_indice(r[0]),
            "distrito_local": indice(r[1]),
            "distrito_local_cabecera": sin_indice(r[1]),
            "municipio": sin_indice(r[2]),
            "localidad": sin_indice(r[3]),
            "seccion": str(r[4]).strip(),
            "casilla": str(r[5]).strip(),
            "ubicacion": str(r[6]).strip(),
        })
    return filas


def catalogo_cct():
    geo = json.loads((SALIDA_GEO / "escuelas_campeche.geojson").read_text())
    por_mun = collections.defaultdict(list)
    for f in geo["features"]:
        p = f["properties"]
        por_mun[norm(p["nombre_municipio"])].append({
            "tokens": distintivo(p["nombre_centro_trabajo"]),
            "localidad": norm(p["nombre_localidad"]),
            "cct": p["cct"],
            "nombre": p["nombre_centro_trabajo"],
            "coords": f["geometry"]["coordinates"],
        })
    return por_mun


def cruzar(inmueble, municipio, localidad, cct):
    """Devuelve (escuela, similitud) o (None, motivo)."""
    n = norm(inmueble)
    if n.startswith(NO_ESCUELA):
        return None, "no es plantel escolar"

    tokens = distintivo(inmueble)
    if not tokens:
        return None, "el encarte no nombra el inmueble"

    mejor, puntaje = None, 0.0
    for e in cct.get(municipio, []):
        if not e["tokens"]:
            continue
        j = len(tokens & e["tokens"]) / len(tokens | e["tokens"])
        # Misma localidad rompe empates entre planteles homónimos, que en
        # Campeche abundan ("Benito Juárez" aparece en 9 municipios).
        if e["localidad"] == localidad:
            j += 0.15
        if j > puntaje:
            mejor, puntaje = e, j

    if puntaje < UMBRAL_CRUCE:
        return None, "sin coincidencia en el catálogo CCT"
    return mejor, round(min(puntaje, 1.0), 3)


def construir_casillas(filas, cct):
    """Un Feature por sitio físico, no por casilla: cuatro casillas en la misma
    escuela son cuatro urnas en un edificio."""
    sitios = collections.OrderedDict()
    for f in filas:
        clave = (f["seccion"], f["ubicacion"])
        s = sitios.setdefault(clave, {
            "seccion": f["seccion"],
            "ubicacion": f["ubicacion"],
            "municipio": f["municipio"],
            "localidad": f["localidad"],
            "distrito_local": f["distrito_local"],
            "distrito_local_cabecera": f["distrito_local_cabecera"],
            "distrito_federal": f["distrito_federal"],
            "casillas": [],
        })
        s["casillas"].append(f["casilla"])

    features, sin_geo = [], []
    for s in sitios.values():
        mun_n = norm(s["municipio"])
        # Sólo el nombre del inmueble: lo que sigue a la primera coma es calle,
        # colonia y referencias, y ahogaría la similitud.
        inmueble = s["ubicacion"].split(",")[0].strip()
        escuela, dato = cruzar(inmueble, mun_n, norm(s["localidad"]), cct)
        props = {
            "seccion": s["seccion"],
            "cve_mun": CVE_MUN.get(mun_n),
            "nombre_municipio": s["municipio"],
            "nombre_localidad": s["localidad"],
            "distrito_local": s["distrito_local"],
            "distrito_local_cabecera": s["distrito_local_cabecera"],
            "distrito_federal": s["distrito_federal"],
            "casillas": ", ".join(sorted(s["casillas"])),
            "n_casillas": len(s["casillas"]),
            "tipos": ", ".join(sorted({c[0] for c in s["casillas"]})),
            "ubicacion": s["ubicacion"],
            "inmueble": s["ubicacion"].split(",")[0].strip(),
            "estatus_ubicacion": "historica",
            "fuente": FUENTE_ENCARTE,
            "fecha_corte": FECHA_CORTE,
        }
        if escuela:
            props.update({
                "cct": escuela["cct"],
                "nombre_cct": escuela["nombre"],
                "metodo_geo": "cruce nominal contra catálogo CCT de la SEP",
                "similitud_cruce": dato,
            })
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": escuela["coords"]},
                "properties": props,
            })
        else:
            props["motivo_sin_geo"] = dato
            sin_geo.append(props)

    return features, sin_geo, len(sitios)


# ── Resultados ──────────────────────────────────────────────────────────────

# Columnas fijas en todas las hojas DIP MR NN_SEC. Las demás (partidos,
# válidos, nulos, total, lista nominal) se resuelven por archivo en
# `columnas()`, porque su posición depende de cuántos contendientes hubo.
COL_DISTRITO, COL_SECCION, COL_CASILLAS = 0, 1, 2

NS_DIBUJO = {
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
ATTR_EMBED = ("{http://schemas.openxmlformats.org/officeDocument/2006/"
              "relationships}embed")


def columnas_partido(ruta):
    """{columna de votos -> clave de partido}, leyendo los logotipos."""
    z = zipfile.ZipFile(ruta)
    rels = {r.get("Id"): r.get("Target") for r in
            ET.fromstring(z.read("xl/drawings/_rels/drawing1.xml.rels"))}
    dibujo = ET.fromstring(z.read("xl/drawings/drawing1.xml"))

    cols = {}
    for anclaje in dibujo:
        desde = anclaje.find("xdr:from", NS_DIBUJO)
        blip = anclaje.find(".//a:blip", NS_DIBUJO)
        if desde is None or blip is None:
            continue
        col = int(desde.find("xdr:col", NS_DIBUJO).text)
        destino = rels[blip.get(ATTR_EMBED)].replace("../", "xl/")
        h = hashlib.md5(z.read(destino)).hexdigest()[:10]
        if h not in LOGOS:
            raise SystemExit(
                f"{ruta.name}: logotipo desconocido en la columna {col} "
                f"(md5 {h}). Hay un contendiente que no está en LOGOS.")
        cols[col] = LOGOS[h]
    return cols


def columnas_totales(ws):
    """Posición de VOTOS VÁLIDOS y siguientes, por su etiqueta."""
    fila = next(f for i, f in enumerate(ws.iter_rows(values_only=True)) if i == 4)
    etiquetas = {str(v).strip(): i for i, v in enumerate(fila) if v}
    faltan = [e for e in ("VOTOS VÁLIDOS", "CANDIDATURAS NO REGISTRADAS",
                          "VOTOS NULOS", "TOTAL", "LISTA NOMINAL")
              if e not in etiquetas]
    if faltan:
        raise SystemExit(f"Encabezado inesperado, faltan columnas: {faltan}")
    return etiquetas


def entero(v):
    return int(v) if isinstance(v, (int, float)) else 0


def celda(fila, i):
    """openpyxl en read_only recorta las celdas vacías del final de la fila."""
    return fila[i] if i < len(fila) else None


def leer_resultados():
    secciones, notas, anticipado = {}, [], []
    archivos = sorted(ENTRADA.glob("DIP MR *_SEC.xlsx"))
    if len(archivos) != 21:
        print(f"  aviso: se esperaban 21 distritos locales, hay {len(archivos)}")

    for ruta in archivos:
        distrito = int(re.search(r"DIP MR (\d+)", ruta.name).group(1))
        ws = openpyxl.load_workbook(ruta, read_only=True).active
        cols_partido = columnas_partido(ruta)
        tot = columnas_totales(ws)

        for i, r in enumerate(ws.iter_rows(values_only=True)):
            if i < 6:
                continue

            # Las notas al pie del IEEC (casillas anuladas por el TEEC) caen en
            # la columna del distrito, en filas sin sección. Se conservan: un
            # distrito con casillas anuladas no se lee igual que uno limpio.
            if isinstance(celda(r, COL_DISTRITO), str):
                notas.append({"distrito_local": distrito,
                              "nota": r[COL_DISTRITO].strip()})
                continue
            if celda(r, COL_SECCION) is None:
                continue
            sec = str(r[COL_SECCION]).strip()

            # Un partido que no contendió en el distrito queda en 0, no en
            # nulo: no compitió, no es que falte el dato.
            votos = {c: 0 for c, _ in PARTIDOS}
            for col, clave in cols_partido.items():
                votos[clave] = entero(celda(r, col))

            registro = {
                "distrito_local": distrito,
                "votos": votos,
                "validos": entero(celda(r, tot["VOTOS VÁLIDOS"])),
                "no_registradas": entero(celda(r, tot["CANDIDATURAS NO REGISTRADAS"])),
                "nulos": entero(celda(r, tot["VOTOS NULOS"])),
                "total": entero(celda(r, tot["TOTAL"])),
                "lista_nominal": entero(celda(r, tot["LISTA NOMINAL"])),
                "casillas": entero(celda(r, COL_CASILLAS)),
            }

            if sec == "VA":   # voto anticipado: no pertenece a ninguna sección
                anticipado.append(registro)
                continue
            if not sec.isdigit():
                continue

            # Dos secciones aparecen en dos distritos (seccional partida por la
            # distritación). Se suman en vez de sobrescribirse.
            if sec in secciones:
                previo = secciones[sec]
                for c in votos:
                    previo["votos"][c] += votos[c]
                for k in ("validos", "no_registradas", "nulos", "total",
                          "lista_nominal", "casillas"):
                    previo[k] += registro[k]
                previo["distritos_locales"].append(distrito)
            else:
                registro["distritos_locales"] = [distrito]
                secciones[sec] = registro

    return secciones, notas, anticipado


def por_bloque(votos):
    return {b: sum(votos.get(c, 0) for c in siglas)
            for b, siglas in BLOQUES.items()}


def rematar(reg):
    """Agrega ganador, margen y participación a un registro de votos."""
    bloques = por_bloque(reg["votos"])
    orden = sorted(bloques.items(), key=lambda kv: kv[1], reverse=True)
    primero, segundo = orden[0], (orden[1] if len(orden) > 1 else ("", 0))
    validos = reg["validos"] or 1
    total = reg["total"] or 1

    reg["bloques"] = bloques
    reg["ganador"] = primero[0]
    reg["ganador_nombre"] = BLOQUE_NOMBRE.get(primero[0], primero[0])
    reg["ganador_votos"] = primero[1]
    reg["segundo"] = segundo[0]
    reg["margen"] = round((primero[1] - segundo[1]) / validos * 100, 2)
    reg["participacion"] = (round(reg["total"] / reg["lista_nominal"] * 100, 2)
                            if reg["lista_nominal"] else None)
    reg["nulos_pct"] = round(reg["nulos"] / total * 100, 2)
    return reg


def agregar_municipios(secciones, seccion_a_mun):
    mun = {}
    huerfanas = []
    for sec, reg in secciones.items():
        cve = seccion_a_mun.get(sec)
        if not cve:
            huerfanas.append(sec)
            continue
        m = mun.setdefault(cve, {
            "cve_mun": cve,
            "nombre": NOMBRE_MUN.get(cve, cve),
            "votos": {c: 0 for c, _ in PARTIDOS},
            "validos": 0, "no_registradas": 0, "nulos": 0, "total": 0,
            "lista_nominal": 0, "casillas": 0, "secciones": 0,
            "distritos_locales": set(),
        })
        for c, v in reg["votos"].items():
            m["votos"][c] += v
        for k in ("validos", "no_registradas", "nulos", "total",
                  "lista_nominal", "casillas"):
            m[k] += reg[k]
        m["secciones"] += 1
        m["distritos_locales"].update(reg["distritos_locales"])

    for m in mun.values():
        m["distritos_locales"] = sorted(m["distritos_locales"])
        rematar(m)
    return mun, huerfanas


# Nomenclatura oficial del INE. La letra es la que trae el encarte en la
# columna "Casilla": B1, C1, C2, E1, S1. "Casilla normal" no existe.
TIPO_CASILLA = {"B": "basica", "C": "contigua", "E": "extraordinaria",
                "S": "especial"}


def contar_casillas(filas):
    """Casillas por tipo y sitios por municipio, tal como se instalaron."""
    mun = collections.defaultdict(lambda: {
        "basica": 0, "contigua": 0, "extraordinaria": 0, "especial": 0,
        "total": 0, "sitios": 0, "secciones_con_casilla": 0,
    })
    sitios = collections.defaultdict(set)
    secciones = collections.defaultdict(set)
    desconocidas = collections.Counter()

    for f in filas:
        cve = CVE_MUN.get(norm(f["municipio"]))
        if not cve:
            continue
        letra = f["casilla"][:1].upper()
        tipo = TIPO_CASILLA.get(letra)
        if not tipo:
            desconocidas[f["casilla"]] += 1
            continue
        mun[cve][tipo] += 1
        mun[cve]["total"] += 1
        sitios[cve].add(f["ubicacion"])
        secciones[cve].add(f["seccion"])

    for cve, d in mun.items():
        d["sitios"] = len(sitios[cve])
        d["secciones_con_casilla"] = len(secciones[cve])

    if desconocidas:
        print(f"  aviso: {sum(desconocidas.values())} casillas con tipo no "
              f"reconocido: {dict(desconocidas)}")
    return mun


def verificar(secciones):
    """La suma de las 16 columnas de partido tiene que dar VOTOS VÁLIDOS.
    Si el IEEC cambia el orden o el número de columnas, aquí se rompe."""
    malas = [s for s, r in secciones.items()
             if sum(r["votos"].values()) != r["validos"]]
    if malas:
        raise SystemExit(
            f"El mapeo de columnas de partido no cuadra en {len(malas)} "
            f"secciones (ej. {malas[:5]}). Revisa PARTIDOS y COL_*.")


# ── Salida ──────────────────────────────────────────────────────────────────

def main():
    print("Encarte 2024…")
    filas = leer_encarte()
    cct = catalogo_cct()
    features, sin_geo, n_sitios = construir_casillas(filas, cct)
    print(f"  {len(filas)} casillas · {n_sitios} sitios · "
          f"{len(features)} geolocalizados · {len(sin_geo)} sin coordenada")

    print("Resultados por sección…")
    secciones, notas, anticipado = leer_resultados()
    verificar(secciones)
    for reg in secciones.values():
        rematar(reg)
    print(f"  {len(secciones)} secciones · {len(notas)} notas del TEEC · "
          f"{len(anticipado)} registros de voto anticipado")

    seccion_a_mun = {}
    for f in filas:
        cve = CVE_MUN.get(norm(f["municipio"]))
        if cve:
            seccion_a_mun[f["seccion"]] = cve
    for sec, reg in secciones.items():
        reg["cve_mun"] = seccion_a_mun.get(sec)

    municipios, huerfanas = agregar_municipios(secciones, seccion_a_mun)
    print(f"  {len(municipios)} municipios · {len(huerfanas)} secciones sin "
          f"municipio en el encarte")

    # La integración de casillas sale del encarte, no de los cómputos: los
    # cómputos dicen cuántas casillas computó cada sección, no de qué tipo.
    conteo = contar_casillas(filas)
    for cve, m in municipios.items():
        m["casillas_tipo"] = conteo.get(cve)
    tipos_estatal = {t: sum(c[t] for c in conteo.values())
                     for t in ("basica", "contigua", "extraordinaria",
                               "especial", "total", "sitios")}
    print("  casillas por tipo:", tipos_estatal)

    meta_comun = {
        "eleccion": "Diputaciones locales de mayoría relativa",
        "proceso": "Proceso Electoral Local Ordinario 2023-2024, Campeche",
        "partidos": [{"clave": c, "nombre": n} for c, n in PARTIDOS],
        "bloques": {b: {"nombre": BLOQUE_NOMBRE[b], "integra": s}
                    for b, s in BLOQUES.items()},
        # Cómputos oficiales del IEEC transcritos, no estimados: la suma por
        # bloque es aritmética sobre esas cifras, no un modelo.
        "procedencia": "dato",
        "generado_por": "backend/datalab/pipeline/build_electoral.py",
    }

    (SALIDA / "resultados_seccion_2024.json").write_text(json.dumps({
        "metadata": dict(meta_comun, fuente=FUENTE_RESULTADOS,
                         fecha_corte=FECHA_CORTE,
                         cobertura=f"{len(secciones)} secciones en 21 distritos locales",
                         advertencia="Voto anticipado y voto en el extranjero "
                                     "van aparte: no pertenecen a ninguna sección.",
                         notas_tribunal=notas,
                         voto_anticipado=anticipado,
                         secciones_sin_municipio=huerfanas),
        "secciones": secciones,
    }, ensure_ascii=False), encoding="utf-8")

    (SALIDA / "resultados_municipio_2024.json").write_text(json.dumps({
        "metadata": dict(meta_comun, fuente=FUENTE_RESULTADOS,
                         fecha_corte=FECHA_CORTE,
                         cobertura="13 municipios",
                         metodologia="Suma de los resultados seccionales. La "
                                     "sección se asigna a municipio con el "
                                     "encarte del INE.",
                         fuente_casillas=FUENTE_ENCARTE,
                         casillas_estatal=tipos_estatal),
        "municipios": municipios,
    }, ensure_ascii=False), encoding="utf-8")

    (SALIDA_GEO / "casillas_2024.geojson").write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {
            "fuente": FUENTE_ENCARTE,
            "fecha_corte": FECHA_CORTE,
            "casillas_instaladas": len(filas),
            "sitios_totales": n_sitios,
            "sitios_geolocalizados": len(features),
            "sitios_sin_coordenada": len(sin_geo),
            # Ubicaciones del encarte del INE. El cruce con el catálogo CCT
            # aporta la coordenada, no la existencia de la casilla.
            "procedencia": "dato",
            "generado_por": "backend/datalab/pipeline/build_electoral.py",
            "metodologia": "El encarte no publica coordenadas. Se cruza el "
                           "nombre del inmueble contra el catálogo CCT de la "
                           "SEP; el sitio que no cruza se queda sin geometría.",
            "advertencia": "Ubicaciones del proceso 2024. NO son las casillas "
                           "de 2027: ésas dependen de acuerdos del INE que aún "
                           "no existen.",
            "generado_por": "backend/datalab/pipeline/build_electoral.py",
        },
        "features": features,
    }, ensure_ascii=False), encoding="utf-8")

    (SALIDA / "casillas_2024_sin_geo.json").write_text(json.dumps({
        "metadata": {
            "fuente": FUENTE_ENCARTE,
            "fecha_corte": FECHA_CORTE,
            "que_es": "Sitios del encarte 2024 que no se pudieron geolocalizar. "
                      "Se publican para que el faltante sea auditable, no para "
                      "dibujarlos en el mapa.",
            # El sitio es dato del encarte; lo que falta es su coordenada.
            "procedencia": "dato",
            "generado_por": "backend/datalab/pipeline/build_electoral.py",
        },
        "sitios": sin_geo,
    }, ensure_ascii=False), encoding="utf-8")

    print("Listo.")


# ── Autocomprobación ────────────────────────────────────────────────────────

def autocomprobar():
    """Comprueba PROPIEDADES, no cifras fijas, y no escribe nada.

    Este pipeline no la tenía. Corría el build completo cuando se le pasaba
    `--autocomprobar` —no había argparse, así que la bandera se ignoraba— y
    salía con código 0, de modo que un bucle que contara ceros lo daba por
    verificado sin que se hubiera verificado nada. La cifra salía bien; la
    afirmación detrás era falsa.

    Se divide en dos mitades. Las invariantes de las constantes no leen disco
    y atrapan el error en cuanto alguien añade un partido o una coalición. Las
    comprobaciones sobre la salida leen los JSON ya publicados, que es lo que
    el frontend consume de verdad.
    """
    # ── 1. Invariantes de las tablas, sin tocar disco ──

    siglas_bloques = [c for s in BLOQUES.values() for c in s]
    claves_partido = [c for c, _ in PARTIDOS]

    # Cada sigla de un bloque tiene que existir como columna de la boleta:
    # una que no exista suma cero para siempre, en silencio.
    huerfanas = sorted(set(siglas_bloques) - set(claves_partido))
    assert not huerfanas, f"bloques con siglas que no están en PARTIDOS: {huerfanas}"

    # Y ninguna puede estar en dos bloques: se contaría dos veces.
    repetidas = [c for c in set(siglas_bloques) if siglas_bloques.count(c) > 1]
    assert not repetidas, f"siglas en más de un bloque: {repetidas}"

    # Toda columna de la boleta tiene que caer en algún bloque, o sus votos
    # desaparecen del agregado sin que nadie lo note.
    sueltas = sorted(set(claves_partido) - set(siglas_bloques))
    assert not sueltas, f"partidos que no están en ningún bloque: {sueltas}"

    # Todo bloque necesita nombre de presentación.
    sin_nombre = sorted(set(BLOQUES) - set(BLOQUE_NOMBRE))
    assert not sin_nombre, f"bloques sin BLOQUE_NOMBRE: {sin_nombre}"

    # Los dos catálogos de municipio tienen que hablar de los mismos 13.
    assert set(CVE_MUN.values()) == set(NOMBRE_MUN), (
        "CVE_MUN y NOMBRE_MUN no cubren el mismo conjunto de municipios")
    assert len(set(CVE_MUN.values())) == len(CVE_MUN), "claves duplicadas en CVE_MUN"

    # norm() es la que cruza encarte con catálogo: si deja de ser idempotente
    # o de quitar acentos, el cruce por nombre falla en silencio.
    assert norm("DZITBALCHÉ ") == "DZITBALCHE"
    assert norm(norm("San Francisco de Campeche")) == norm("San Francisco de Campeche")
    for nombre in CVE_MUN:
        assert norm(nombre) == nombre, f"CVE_MUN tiene una clave sin normalizar: {nombre}"

    # indice()/sin_indice() son pareja: lo que una extrae, la otra lo quita.
    assert indice("12) ESCUELA X") == 12 and sin_indice("12) ESCUELA X") == "ESCUELA X"
    assert indice("ESCUELA X") is None

    # ── 2. Aritmética, sobre un registro sintético ──

    votos = {c: 0 for c in claves_partido}
    votos["PRI"], votos["MORENA"], votos["MC"] = 100, 60, 40
    b = por_bloque(votos)
    assert sum(b.values()) == sum(votos.values()), "por_bloque pierde o inventa votos"
    assert b["PRI-PRD"] == 100 and b["SHH"] == 60 and b["MC"] == 40

    reg = rematar({"votos": votos, "validos": 200, "total": 220, "nulos": 20,
                   "lista_nominal": 400})
    assert reg["ganador"] == "PRI-PRD", reg["ganador"]
    assert reg["segundo"] == "SHH", reg["segundo"]
    assert reg["margen"] == 20.0, reg["margen"]          # (100-60)/200
    assert reg["participacion"] == 55.0, reg["participacion"]   # 220/400

    # Una sección sin lista nominal no puede fingir participación 0: es null.
    assert rematar({"votos": votos, "validos": 200, "total": 220, "nulos": 20,
                    "lista_nominal": 0})["participacion"] is None

    # ── 3. La salida publicada, que es lo que el frontend lee ──

    sec = json.loads((SALIDA / "resultados_seccion_2024.json").read_text())
    mun = json.loads((SALIDA / "resultados_municipio_2024.json").read_text())
    geo = json.loads((SALIDA_GEO / "casillas_2024.geojson").read_text())

    secciones, municipios = sec["secciones"], mun["municipios"]
    assert secciones and municipios, "salida vacía"
    assert set(municipios) == set(NOMBRE_MUN), (
        f"faltan o sobran municipios en la salida: "
        f"{set(NOMBRE_MUN) ^ set(municipios)}")

    for s, r in secciones.items():
        assert sum(r["votos"].values()) == r["validos"], (
            f"sección {s}: los votos por partido no suman los válidos")
        assert sum(r["bloques"].values()) == r["validos"], (
            f"sección {s}: los bloques no suman los válidos")
        assert r["ganador"] in BLOQUES, f"sección {s}: ganador fuera del catálogo"

    # El municipio es la suma de sus secciones. No cuadran exactamente, y eso
    # está bien: el encarte no asigna municipio a tres secciones, así que sus
    # votos existen a nivel sección y no entran en ningún agregado municipal.
    #
    # Lo que se exige aquí no es que no haya hueco, sino que el hueco esté
    # EXPLICADO POR COMPLETO: la diferencia tiene que ser exactamente los
    # votos de las secciones declaradas como huérfanas. Así, una sección que
    # se pierda por cualquier otro motivo no puede esconderse dentro de una
    # discrepancia que ya dábamos por conocida.
    total_sec = sum(r["validos"] for r in secciones.values())
    total_mun = sum(m["validos"] for m in municipios.values())
    huerfanas = [str(s) for s in sec["metadata"].get("secciones_sin_municipio", [])]
    assert huerfanas, "no se declara qué secciones quedaron sin municipio"

    esperado = sum(secciones[s]["validos"] for s in huerfanas if s in secciones)
    assert total_sec - total_mun == esperado, (
        f"el hueco sección↔municipio es {total_sec - total_mun:,} votos, pero "
        f"las {len(huerfanas)} secciones declaradas sin municipio sólo explican "
        f"{esperado:,}. Hay una fuga sin declarar.")

    for s in huerfanas:
        assert s in secciones, f"se declara huérfana la sección {s}, que no existe"

    for cve, m in municipios.items():
        assert sum(m["bloques"].values()) == m["validos"], f"{cve}: bloques != válidos"
        assert m["nombre"] == NOMBRE_MUN[cve]
        t = m["casillas_tipo"]
        assert (t["basica"] + t["contigua"] + t["extraordinaria"] + t["especial"]
                == t["total"]), f"{cve}: las casillas por tipo no suman el total"
        assert t["sitios"] <= t["total"], (
            f"{cve}: más sitios que casillas — un sitio aloja una o varias, "
            f"nunca menos de una")

    # Toda casilla geolocalizada cae dentro de Campeche. Una coordenada
    # invertida (lat/lon al revés) aterriza en el océano Índico y sólo se ve
    # cuando alguien abre el mapa.
    fuera = [f["properties"].get("seccion") for f in geo["features"]
             if not (-92.6 <= f["geometry"]["coordinates"][0] <= -89.0
                     and 17.7 <= f["geometry"]["coordinates"][1] <= 21.0)]
    assert not fuera, f"casillas con coordenada fuera de Campeche: {fuera[:5]}"

    print(f"OK · {len(secciones)} secciones · {len(municipios)} municipios · "
          f"{len(geo['features'])} casillas geolocalizadas · "
          f"{total_sec:,} votos válidos cuadran sección↔municipio")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--autocomprobar", action="store_true",
                    help="comprueba propiedades sobre la salida ya generada, "
                         "sin reconstruir ni escribir nada")
    if ap.parse_args().autocomprobar:
        autocomprobar()
    else:
        main()
