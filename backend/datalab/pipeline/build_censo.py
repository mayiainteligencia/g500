#!/usr/bin/env python3
"""Censo de Población y Vivienda 2020 (ITER) — población por municipio y localidad.

    backend/datalab/venv/bin/python backend/datalab/pipeline/build_censo.py
    backend/datalab/venv/bin/python backend/datalab/pipeline/build_censo.py --autocomprobar

Tercer pipeline, hermano de build_electoral.py y build_ine_cartografia.py, con
la misma disciplina: el crudo no se toca, se verifica antes de publicar, y lo
que falta se declara en vez de rellenarse.

Insumo (no se toca), en backend/datalab/uploads/censo2020/:

  conjunto_de_datos_iter_04CSV20.csv   ITER de Campeche. 2,800 filas, 286
                                       columnas. Una fila por localidad, más
                                       filas de totales.
  diccionario_datos_iter_04CSV20.csv   qué significa cada mnemónico.
  tam_loc.csv.csv                      catálogo de rangos de tamaño (1 a 249
                                       habitantes, 250 a 499…). NO se usa: es
                                       la leyenda de una columna `TAMLOC` que
                                       no viene en este ITER.

Salida:

  frontend/data/censo/poblacion_2020.json

CUATRO COSAS QUE SE VERIFICARON ANTES DE ESCRIBIR ESTO
──────────────────────────────────────────────────────

1. SECRETO ESTADÍSTICO. El INEGI suprime el desglose con un asterisco `*` en
   1,978 de las 2,762 localidades. Un `*` NO es cero: es "no publicable". Se
   emite `null` con su motivo. Buena noticia: las suprimidas suman 7,376
   habitantes (0.8% del estado) y NINGUNA tiene polígono, así que el mapa no
   pierde nada. Las filas de municipio no traen un solo asterisco.

2. NO SE AGREGAN LOCALIDADES PARA OBTENER EL MUNICIPIO. Sumar el desglose de
   las localidades pierde a las suprimidas: en Calkiní faltarían 66 mujeres y
   en Campeche 192. El desglose municipal se toma de la FILA MUNICIPAL, que el
   ITER ya trae completa.

3. EL CENSO TIENE 12 MUNICIPIOS Y EL PROYECTO 13. Dzitbalché se separó de
   Calkiní en 2021, después del Censo. Así que:
     · Dzitbalché no tiene cifra municipal 2020. Se emite `null` con motivo.
     · La cifra de Calkiní INCLUYE a lo que hoy es Dzitbalché. Se marca.
   No se reconstruye el total de Dzitbalché sumando sus localidades: el Marco
   Geoestadístico sólo le da polígono a dos, y el municipio puede tener más.

4. LA CLAVE DE LOCALIDAD SÍ CRUZA. ITER usa ENTIDAD(2)+MUN(3)+LOC(4) y
   localidades.geojson usa `cvegeo` de 9 dígitos: el mismo formato. Cruzan 499
   de 511 polígonos, y esos 499 tienen desglose completo. De los 12 que no
   cruzan, 2 son de Dzitbalché y se resuelven por renumeración (misma localidad
   física, municipio nuevo); los otros 10 son localidades creadas después de
   2020 y se declaran sin dato.
"""

import argparse
import csv
import json
import pathlib
import sys
import unicodedata

# NOMBRE_MUN se importa en vez de copiarse: la tabla de nombres oficiales vive
# en un solo sitio, igual que CVE_MUN en los otros pipelines.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_electoral import NOMBRE_MUN  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parents[3]
ENTRADA = RAIZ / "backend/datalab/uploads/censo2020"
SALIDA = RAIZ / "frontend/data/censo"
GEO = RAIZ / "frontend/data/geo"

FUENTE = "INEGI — Censo de Población y Vivienda 2020, ITER"
FECHA_CORTE = "2020-03"

# El asterisco es la marca de confidencialidad del INEGI. Se lista aparte de
# la cadena vacía porque significan cosas distintas: `*` es "existe pero no se
# publica"; vacío es "no aplica".
SUPRIMIDO = "*"

MOTIVO_SUPRIMIDO = ("Suprimido por el INEGI para proteger la confidencialidad "
                    "de los habitantes de la localidad")

# Filas que no son localidades: totales y agrupaciones del propio ITER.
LOC_NO_TERRITORIAL = {"0000", "9998", "9999"}

# Rangos pedidos y de dónde sale cada uno. `directo` es DATO: la columna existe
# tal cual en el ITER. `suma` y `resta` son CÁLCULO: se derivan de otras.
DIRECTOS = {
    "poblacion_total": "POBTOT",
    "mujeres": "POBFEM",
    "hombres": "POBMAS",
    "mayores_18": "P_18YMAS",
}
# 50 y más no viene hecho: el ITER salta de P_45A49 a P_50A54 y luego publica
# P_60YMAS. Se arma con los dos quinquenios intermedios más el bloque abierto.
SUMA_50YMAS = ["P_50A54", "P_55A59", "P_60YMAS"]

PROCEDENCIA = {
    "poblacion_total": "dato",
    "mujeres": "dato",
    "hombres": "dato",
    "mayores_18": "dato",
    "menores_18": "calculo",
    "mayores_50": "calculo",
}


def norm(s):
    """Nombre comparable: sin acentos, sin puntuación, en mayúsculas."""
    s = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode()
    return "".join(c for c in s.upper() if c.isalnum())


def entero(v):
    """Devuelve el número, o None si el INEGI lo suprimió.

    Nunca devuelve 0 para un valor suprimido: un cero se suma, se promedia y
    se grafica como si fuera un hecho. `None` se propaga y obliga a decidir."""
    v = (v or "").strip()
    if v == SUPRIMIDO or v == "":
        return None
    return int(v)


def rangos(fila):
    """Los seis indicadores pedidos, a partir de una fila del ITER."""
    r = {k: entero(fila[col]) for k, col in DIRECTOS.items()}

    # Menores de 18 = total − mayores de 18. Si cualquiera de los dos está
    # suprimido, el resultado es desconocido, no cero.
    tot, may = r["poblacion_total"], r["mayores_18"]
    r["menores_18"] = None if tot is None or may is None else tot - may

    partes = [entero(fila[c]) for c in SUMA_50YMAS]
    r["mayores_50"] = None if any(p is None for p in partes) else sum(partes)
    return r


def leer_iter():
    ruta = ENTRADA / "conjunto_de_datos_iter_04CSV20.csv"
    if not ruta.exists():
        raise SystemExit(f"Falta el ITER en {ruta}")
    with ruta.open(encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f))

    faltan = [c for c in list(DIRECTOS.values()) + SUMA_50YMAS
              if c not in filas[0]]
    if faltan:
        raise SystemExit(
            f"El ITER no trae las columnas {faltan}. El archivo cambió de "
            f"forma o no es el de Campeche; revisa DIRECTOS y SUMA_50YMAS.")
    return filas


def construir(filas):
    municipios, localidades = {}, {}
    suprimidas = 0

    for x in filas:
        if x["MUN"] == "000":            # totales de entidad
            continue
        cve_mun = f"{x['ENTIDAD']}{x['MUN']}"

        if x["LOC"] == "0000":           # fila de total municipal
            municipios[cve_mun] = dict(
                rangos(x), cve_mun=cve_mun, nombre=x["NOM_MUN"].strip())
            continue

        if x["LOC"] in LOC_NO_TERRITORIAL:
            continue

        r = rangos(x)
        if r["mujeres"] is None:
            suprimidas += 1
        localidades[f"{cve_mun}{x['LOC']}"] = dict(
            r,
            cve_loc=f"{cve_mun}{x['LOC']}",
            cve_mun=cve_mun,
            nombre=x["NOM_LOC"].strip(),
            motivo_sin_desglose=MOTIVO_SUPRIMIDO if r["mujeres"] is None else None,
        )
    return municipios, localidades, suprimidas


def renumerar_dzitbalche(localidades):
    """Dzitbalché y Bacabchén cambiaron de municipio en 2021, no de lugar.

    El Censo las tiene bajo Calkiní (04001) y el Marco Geoestadístico 2024 las
    pone bajo Dzitbalché (04013). Es la MISMA localidad con clave nueva, así que
    la cifra de 2020 le corresponde. Se cruza por nombre normalizado contra el
    polígono, nunca por número: es el mismo criterio que usa build_electoral.py
    para los municipios, y por la misma razón.

    Devuelve las entradas nuevas y la lista de las que no se pudieron resolver.
    """
    ruta = GEO / "localidades.geojson"
    if not ruta.exists():
        return {}, []
    geo = json.loads(ruta.read_text())

    por_nombre = {}
    for k, v in localidades.items():
        if v["cve_mun"] == "04001":
            por_nombre[norm(v["nombre"])] = v

    nuevas, sin_resolver = {}, []
    for f in geo["features"]:
        p = f["properties"]
        if p.get("cve_mun") != "04013" or p["cvegeo"] in localidades:
            continue
        origen = por_nombre.get(norm(p["nombre"]))
        if not origen:
            sin_resolver.append(p["cvegeo"])
            continue
        nuevas[p["cvegeo"]] = dict(
            origen,
            cve_loc=p["cvegeo"],
            cve_mun="04013",
            nombre=p["nombre"],
            clave_censo_2020=origen["cve_loc"],
            nota=("En 2020 esta localidad pertenecía a Calkiní. Dzitbalché se "
                  "erigió en municipio en 2021, después del Censo: la cifra es "
                  "de la misma localidad con su clave anterior."),
        )
    return nuevas, sin_resolver


def cobertura_geo(localidades):
    """Cuántos polígonos del mapa quedan con dato y cuántos sin él."""
    ruta = GEO / "localidades.geojson"
    if not ruta.exists():
        return None
    geo = json.loads(ruta.read_text())
    con, sin = [], []
    for f in geo["features"]:
        cve = f["properties"]["cvegeo"]
        (con if cve in localidades else sin).append(
            cve if cve in localidades else
            {"cve_loc": cve, "nombre": f["properties"]["nombre"],
             "cve_mun": f["properties"]["cve_mun"]})
    return {
        "poligonos_totales": len(geo["features"]),
        "con_dato": len(con),
        "sin_dato": len(sin),
        "detalle_sin_dato": [s for s in sin if isinstance(s, dict)],
        "motivo_sin_dato": "Localidades del Marco Geoestadístico 2024 que no "
                           "existían en el Censo 2020.",
    }


def verificar(municipios, localidades, filas):
    """Nada se publica sin cuadrar contra los totales del propio ITER."""
    entidad = next(x for x in filas if x["MUN"] == "000" and x["LOC"] == "0000")

    # 1. La suma de los municipios tiene que dar el total de la entidad, en
    #    cada uno de los cuatro indicadores directos.
    for campo, col in DIRECTOS.items():
        esperado = entero(entidad[col])
        obtenido = sum(m[campo] for m in municipios.values() if m[campo] is not None)
        if esperado != obtenido:
            raise SystemExit(
                f"{campo}: la suma municipal da {obtenido:,} y el ITER declara "
                f"{esperado:,} para la entidad. Diferencia {esperado - obtenido:,}.")

    # 2. Los desgloses tienen que ser internamente consistentes.
    for cve, m in municipios.items():
        if m["mujeres"] + m["hombres"] != m["poblacion_total"]:
            raise SystemExit(
                f"{cve} {m['nombre']}: mujeres + hombres "
                f"({m['mujeres'] + m['hombres']:,}) no da la población total "
                f"({m['poblacion_total']:,}).")
        if m["mayores_18"] + m["menores_18"] != m["poblacion_total"]:
            raise SystemExit(f"{cve}: 18+ y menores de 18 no suman el total.")
        if m["mayores_50"] > m["mayores_18"]:
            raise SystemExit(
                f"{cve}: hay más personas de 50+ ({m['mayores_50']:,}) que de "
                f"18+ ({m['mayores_18']:,}). El mapeo de columnas está mal.")

    # 3. Ninguna localidad puede quedar a medias: o trae el desglose entero o
    #    no trae ninguno. Un desglose parcial se sumaría mal en cualquier vista.
    for cve, l in localidades.items():
        campos = [l[k] for k in PROCEDENCIA if k != "poblacion_total"]
        if any(c is None for c in campos) and any(c is not None for c in campos):
            raise SystemExit(f"Localidad {cve}: desglose parcial, {l}")

    return {"municipios": len(municipios), "localidades": len(localidades)}


def agregado_cct():
    """Escuelas y alumnado por municipio, precalculado.

    escuelas_campeche.geojson pesa 2 MB y hasta ahora lo bajaban SEIS páginas.
    Dos de ellas —el centro de mando y demografía— sólo lo querían para contar
    planteles y sumar alumnado por municipio: trece números. Se precalculan
    aquí, y el geojson completo se queda para el mapa, que sí necesita la
    geometría de cada punto.
    """
    ruta = GEO / "escuelas_campeche.geojson"
    if not ruta.exists():
        return None
    geo = json.loads(ruta.read_text())
    por = {}
    sin_mun = 0
    for f in geo["features"]:
        p = f["properties"]
        cve = p.get("cve_mun")
        if not cve:
            sin_mun += 1
            continue
        d = por.setdefault(cve, {
            "cve_mun": cve, "nombre": NOMBRE_MUN.get(cve, cve),
            "planteles": 0, "alumnos": 0, "docentes": 0, "aulas": 0,
        })
        d["planteles"] += 1
        d["alumnos"] += p.get("alumnos_total") or 0
        d["docentes"] += p.get("docentes_total") or 0
        d["aulas"] += p.get("aulas_existentes") or 0

    total = sum(d["planteles"] for d in por.values())
    if total + sin_mun != len(geo["features"]):
        raise SystemExit(
            f"El agregado de CCT pierde planteles: {total} + {sin_mun} sin "
            f"municipio != {len(geo['features'])} del geojson.")
    return {
        "metadata": {
            "procedencia": "calculo",
            "fuente": geo["metadata"]["fuente"],
            "fecha_corte": geo["metadata"].get("fecha_corte"),
            "generado_por": "backend/datalab/pipeline/build_censo.py",
            "que_es": "Conteo de centros de trabajo de la SEP por municipio. "
                      "Precalculado para que las vistas no bajen los 2 MB del "
                      "geojson sólo para contar.",
        },
        "fuente": geo["metadata"]["fuente"],
        "fecha_corte": geo["metadata"].get("fecha_corte"),
        "planteles_totales": len(geo["features"]),
        "sin_municipio": sin_mun,
        "que_es": "Conteo de centros de trabajo de la SEP por municipio. "
                  "Precalculado para que las vistas no bajen los 2 MB del "
                  "geojson sólo para contar.",
        "municipios": por,
    }


def con_poligono(localidades):
    """Sólo las localidades que el mapa puede dibujar.

    El ITER trae 2,762 localidades y el Marco Geoestadístico le da polígono a
    501. Publicar las 2,261 restantes son ~1.4 MB que el navegador descarga
    para no pintar nada — el mismo error que ya está documentado con
    escuelas_campeche.geojson. El crudo se conserva intacto, así que si algún
    día hace falta el resto, se regenera cambiando esta función."""
    ruta = GEO / "localidades.geojson"
    if not ruta.exists():
        return localidades, 0
    geo = json.loads(ruta.read_text())
    claves = {f["properties"]["cvegeo"] for f in geo["features"]}
    recortado = {k: v for k, v in localidades.items() if k in claves}
    return recortado, len(localidades) - len(recortado)


def escribir(municipios, localidades, cob, suprimidas, sin_resolver, omitidas):
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "poblacion_2020.json").write_text(json.dumps({
        "metadata": {
            "fuente": FUENTE,
            "fecha_corte": FECHA_CORTE,
            "que_es": "Población total y su desglose por sexo y por tres cortes "
                      "de edad, a nivel municipio y localidad.",
            # Publicado por el INEGI. Los campos derivados llevan su propia
            # marca en `procedencia_por_campo`, que es más fina que ésta.
            "procedencia": "dato",
            "procedencia_por_campo": PROCEDENCIA,
            "derivaciones": {
                "menores_18": "CÁLCULO: POBTOT − P_18YMAS. El ITER no publica "
                              "el rango.",
                "mayores_50": "CÁLCULO: P_50A54 + P_55A59 + P_60YMAS. El ITER "
                              "salta de 45-49 a 50-54 y cierra en 60 y más; no "
                              "existe una columna de 50 y más.",
                "mayores_18": "DATO: P_18YMAS viene tal cual en el ITER, no se "
                              "suma de quinquenios.",
            },
            "secreto_estadistico": {
                "marca": SUPRIMIDO,
                "localidades_suprimidas": suprimidas,
                "criterio": MOTIVO_SUPRIMIDO,
                "trato": "Se emite null, nunca 0. Un cero se suma y se grafica "
                         "como si fuera un hecho; null obliga a decidir.",
                "nota": "Ninguna localidad suprimida tiene polígono en "
                        "localidades.geojson, así que el mapa no pierde "
                        "cobertura por esto.",
            },
            "municipios_2020_vs_2024": {
                "en_el_censo": len(municipios),
                "en_el_proyecto": 13,
                "falta": "04013 Dzitbalché",
                "explicacion": "Dzitbalché se erigió en municipio en 2021, "
                               "después del Censo. No tiene cifra municipal de "
                               "2020 y no se reconstruye sumando sus "
                               "localidades: sólo dos tienen polígono y el "
                               "municipio puede tener más.",
                "advertencia_calkini": "La cifra de Calkiní (04001) INCLUYE al "
                                       "territorio que hoy es Dzitbalché. No es "
                                       "comparable con el Calkiní electoral de "
                                       "2024, que ya no lo incluye.",
                "localidades_no_resueltas": sin_resolver,
            },
            "cobertura_geografica": cob,
            "localidades_publicadas": {
                "publicadas": len(localidades),
                "omitidas": omitidas,
                "criterio": "Sólo se publican las localidades con polígono en "
                            "localidades.geojson. Las omitidas no se pueden "
                            "dibujar y suman ~1.4 MB de descarga inútil; el "
                            "crudo se conserva y se regeneran cuando hagan "
                            "falta.",
            },
            "generado_por": "backend/datalab/pipeline/build_censo.py",
        },
        "municipios": municipios,
        "localidades": localidades,
    }, ensure_ascii=False), encoding="utf-8")


def autocomprobar():
    """Comprueba lo que no es obvio, sin red y sin frameworks."""
    # Un asterisco NUNCA se convierte en cero: es el error que este pipeline
    # existe para no cometer.
    assert entero("*") is None
    assert entero("") is None
    assert entero(" 123 ") == 123
    assert entero("0") == 0, "un cero real sí es cero"

    # Un rango derivado con una parte suprimida es desconocido, no parcial.
    fila = {"POBTOT": "100", "POBFEM": "*", "POBMAS": "*", "P_18YMAS": "*",
            "P_50A54": "*", "P_55A59": "*", "P_60YMAS": "*"}
    r = rangos(fila)
    assert r["poblacion_total"] == 100
    assert r["menores_18"] is None, "sin 18+ no se puede saber cuántos menores hay"
    assert r["mayores_50"] is None

    fila = {"POBTOT": "100", "POBFEM": "52", "POBMAS": "48", "P_18YMAS": "70",
            "P_50A54": "10", "P_55A59": "8", "P_60YMAS": "12"}
    r = rangos(fila)
    assert r["menores_18"] == 30
    assert r["mayores_50"] == 30

    # norm() ignora acentos y puntuación, que es lo que permite cruzar
    # "Dzitbalché" del Marco Geoestadístico con "Dzitbalche" del ITER.
    assert norm("Dzitbalché") == norm("DZITBALCHE") == "DZITBALCHE"

    # El agregado de CCT no puede perder planteles: es la comprobación que
    # hace fiable sustituir 2 MB por 2 KB.
    cct = agregado_cct()
    if cct:
        suma = sum(d["planteles"] for d in cct["municipios"].values())
        assert suma + cct["sin_municipio"] == cct["planteles_totales"]

    filas = leer_iter()
    mun, loc, sup = construir(filas)
    verificar(mun, loc, filas)
    assert len(mun) == 12, f"se esperaban 12 municipios en el Censo 2020, hay {len(mun)}"
    assert "04013" not in mun, "Dzitbalché no existía en 2020"
    print(f"OK · {len(mun)} municipios · {len(loc)} localidades · "
          f"{sup} con desglose suprimido")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--autocomprobar", action="store_true",
                    help="corre las comprobaciones internas y sale")
    args = ap.parse_args()
    if args.autocomprobar:
        return autocomprobar()

    print("ITER Campeche 2020…")
    filas = leer_iter()
    municipios, localidades, suprimidas = construir(filas)
    print(f"  {len(municipios)} municipios · {len(localidades)} localidades · "
          f"{suprimidas} con desglose suprimido por confidencialidad")

    nuevas, sin_resolver = renumerar_dzitbalche(localidades)
    if nuevas:
        localidades.update(nuevas)
        print(f"  {len(nuevas)} localidades renumeradas a Dzitbalché (04013): "
              + ", ".join(v["nombre"] for v in nuevas.values()))
    if sin_resolver:
        print(f"  {len(sin_resolver)} sin resolver: {sin_resolver}")

    conteo = verificar(municipios, localidades, filas)
    print(f"  verificado: la suma municipal cuadra con el total de la entidad "
          f"en los {len(DIRECTOS)} indicadores directos")

    cob = cobertura_geo(localidades)
    if cob:
        print(f"  cobertura del mapa: {cob['con_dato']} de "
              f"{cob['poligonos_totales']} polígonos con dato")

    localidades, omitidas = con_poligono(localidades)
    print(f"  se publican {len(localidades)} localidades; {omitidas} omitidas "
          f"por no tener polígono que pintar")

    cct = agregado_cct()
    if cct:
        (SALIDA / "cct_por_municipio.json").write_text(
            json.dumps(cct, ensure_ascii=False), encoding="utf-8")
        print(f"  agregado CCT: {len(cct['municipios'])} municipios · "
              f"{cct['planteles_totales']} planteles")

    escribir(municipios, localidades, cob, suprimidas, sin_resolver, omitidas)
    print("Listo.")


if __name__ == "__main__":
    main()
