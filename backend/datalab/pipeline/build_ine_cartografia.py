#!/usr/bin/env python3
"""Cartografía electoral oficial del INE — distritos y catálogo de secciones.

    backend/datalab/venv/bin/python backend/datalab/pipeline/build_ine_cartografia.py --descargar
    backend/datalab/venv/bin/python backend/datalab/pipeline/build_ine_cartografia.py

Hermano de build_electoral.py y con la misma disciplina: el crudo no se toca,
se verifica antes de publicar, y lo que falta se declara en vez de inventarse.

Dos insumos que se cruzan por clave de sección:

  GEOMETRÍA   endpoint público del INE, uno por sección:
              cartografia.ine.mx/sige8/api/getConoceTuNuevoDistrito?entidad=4&seccion=N

  JERARQUÍA   catálogos tabulares en
              backend/datalab/uploads/cartografiaCampeche/ (corte FEB2026)

LO QUE EL ENDPOINT SÍ DA Y LO QUE NO
────────────────────────────────────
Se verificó contra el servidor en vivo. El endpoint NO devuelve el polígono de
la sección que se le pide: devuelve los TRES DISTRITOS QUE LA CONTIENEN. Su
nombre lo dice —"conoce tu nuevo distrito"—: responde "¿en qué distrito estoy?",
no "¿qué forma tiene mi sección?".

La respuesta es una LISTA de tres FeatureCollection, no un FeatureCollection:

    [0]  {"entidad": 4, "distrito": 1}      distrito federal
    [1]  {"entidad": 4, "distrito_l": 1}    distrito local
    [2]  {"circuito": 31, "distrito_j": 1}  distrito judicial electoral

Consecuencia para el plan: la capa 'secciones' del mapa SIGUE PENDIENTE. Las
otras tres se destraban con esto. Ver PENDIENTE-INEGI-INE.md.

POR QUÉ 26 PETICIONES Y NO 555
──────────────────────────────
Se comprobó que el polígono de un distrito es byte a byte idéntico se pida
desde la sección que se pida (secciones 3 y 7, mismo distrito, mismo md5 de
geometría). Así que pedir las 555 secciones bajaría el mismo polígono cientos
de veces: ~330 MB para obtener ~12 MB de información.

Los catálogos ya dicen qué sección pertenece a qué distrito, así que basta una
sección representante por combinación (distrito federal, distrito local,
municipio): 26 peticiones que cubren los 21 distritos locales, los 2 federales
y —con buena dispersión geográfica— los judiciales, que no vienen en ningún
catálogo y sólo se descubren pidiéndolos.
"""

import argparse
import collections
import json
import pathlib
import sys
import time
import unicodedata
import urllib.error
import urllib.request

try:
    import openpyxl
except ImportError:
    sys.exit("Falta openpyxl. Usa backend/datalab/venv/bin/python.")

# El crosswalk de municipios (nombre normalizado -> clave INEGI) se importa en
# vez de copiarse: si esa tabla se duplicara y una copia se corrigiera sin la
# otra, los dos pipelines publicarían municipios distintos con la misma clave.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from build_electoral import CVE_MUN, NOMBRE_MUN, norm  # noqa: E402

RAIZ = pathlib.Path(__file__).resolve().parents[3]
CATALOGOS = RAIZ / "backend/datalab/uploads/cartografiaCampeche"
CRUDO = RAIZ / "backend/datalab/uploads/ine_cartografia/secciones_raw"
SALIDA_GEO = RAIZ / "frontend/data/geo"
SALIDA = RAIZ / "frontend/data/electoral"

ENDPOINT = ("https://cartografia.ine.mx/sige8/api/getConoceTuNuevoDistrito"
            "?entidad={entidad}&seccion={seccion}")
ENTIDAD = 4

FUENTE_GEO = "INE — Sistema de Consulta de Cartografía Electoral (SIGE8)"
FUENTE_CAT = "INE — Catálogos cartográficos, corte febrero 2026"
FECHA_CORTE = "2026-02"

PAUSA = 0.4       # segundos entre peticiones. El servidor no es nuestro.
REINTENTOS = 3

# Las tres capas que trae cada respuesta, en el orden en que llegan. La clave
# es la propiedad que identifica al distrito dentro de su FeatureCollection.
CAPAS = [
    ("distrito",   "distritos_federales",  "Distrito federal"),
    ("distrito_l", "distritos_locales",    "Distrito local"),
    ("distrito_j", "distritos_judiciales", "Distrito judicial electoral"),
]


def archivo(fragmento):
    """Ubica un catálogo por un fragmento de su nombre.

    macOS guarda los nombres de archivo en Unicode NFD (la tilde va aparte de
    la letra). Un literal escrito en NFC —lo normal al teclearlo— no abre el
    archivo aunque en pantalla se vea idéntico. Por eso se busca comparando
    formas normalizadas en vez de hardcodear el nombre.
    """
    objetivo = unicodedata.normalize("NFC", fragmento).lower()
    for p in sorted(CATALOGOS.iterdir()):
        if objetivo in unicodedata.normalize("NFC", p.name).lower():
            return p
    raise SystemExit(f"No está el catálogo que contiene '{fragmento}' en {CATALOGOS}")


# ── Catálogos tabulares ─────────────────────────────────────────────────────

def leer_xlsx(ruta):
    ws = openpyxl.load_workbook(ruta, read_only=True).active
    filas = list(ws.iter_rows(values_only=True))
    cab = [str(c).strip() for c in filas[0]]
    return [dict(zip(cab, f)) for f in filas[1:] if f[0] is not None]


def leer_pipes(ruta):
    lineas = ruta.read_text(encoding="latin-1").splitlines()
    cab = [c.strip() for c in lineas[0].split("|")]
    return [dict(zip(cab, l.split("|"))) for l in lineas[1:] if l.strip()]


def leer_catalogos():
    """Devuelve {seccion: {distrito_federal, distrito_local, cve_mun, tipo}}."""
    csdel = leer_xlsx(archivo("Secciones con Distritos Electorales Locales"))
    csedef = leer_pipes(archivo("Catálogo de Secciones.txt"))
    cm = leer_xlsx(archivo("Catálogo de Municipios.xlsx"))

    # El INE numera los municipios 1=CAMPECHE, 2=CALKINI; el INEGI 04001=Calkiní,
    # 04002=Campeche. Cruzar por número intercambiaría municipios enteros
    # (Calakmul es 11 en el INE y 04010 en el INEGI; Candelaria, al revés).
    # Se cruza por nombre normalizado, igual que build_electoral.py.
    mun_ine = {}
    sin_clave = []
    for r in cm:
        n = norm(r["NOMBRE MUNICIPIO"])
        cve = CVE_MUN.get(n)
        if not cve:
            sin_clave.append(r["NOMBRE MUNICIPIO"])
        mun_ine[str(r["MUNICIPIO"])] = cve
    if sin_clave:
        raise SystemExit(
            f"Municipios del catálogo del INE que no cruzan contra CVE_MUN: "
            f"{sin_clave}. Revisa norm() o la tabla en build_electoral.py.")

    tipo = {str(r["SECCION"]): r["TIPO"] for r in csedef}

    secciones = {}
    for r in csdel:
        sec = str(r["SECCION"])
        secciones[sec] = {
            "seccion": sec,
            "distrito_federal": int(r["DISTRITO_FEDERAL"]),
            "distrito_local": int(r["DISTRITO_LOCAL"]),
            "municipio_ine": int(r["MUNICIPIO"]),
            "cve_mun": mun_ine[str(r["MUNICIPIO"])],
            "nombre_municipio": NOMBRE_MUN[mun_ine[str(r["MUNICIPIO"])]],
            "tipo": tipo.get(sec),
        }
    return secciones


def representantes(secciones):
    """Una sección por combinación (federal, local, municipio).

    El municipio entra en la combinación aunque no haga falta para los
    distritos: da dispersión geográfica, que es lo único que puede descubrir
    los distritos judiciales — no vienen en ningún catálogo.
    """
    vistos = {}
    for sec, d in sorted(secciones.items(), key=lambda kv: int(kv[0])):
        clave = (d["distrito_federal"], d["distrito_local"], d["municipio_ine"])
        vistos.setdefault(clave, sec)
    return sorted(vistos.values(), key=int)


# ── Descarga ────────────────────────────────────────────────────────────────

def descargar(secciones):
    CRUDO.mkdir(parents=True, exist_ok=True)
    objetivo = representantes(secciones)
    print(f"{len(objetivo)} secciones representantes de {len(secciones)} totales.")

    for i, sec in enumerate(objetivo, 1):
        destino = CRUDO / f"seccion_{int(sec):04d}.json"
        if destino.exists():
            print(f"  [{i}/{len(objetivo)}] sección {sec}: ya estaba")
            continue

        url = ENDPOINT.format(entidad=ENTIDAD, seccion=sec)
        for intento in range(1, REINTENTOS + 1):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    cuerpo = r.read()
                break
            except (urllib.error.URLError, TimeoutError) as e:
                if intento == REINTENTOS:
                    raise SystemExit(
                        f"Sección {sec}: falló tras {REINTENTOS} intentos ({e}). "
                        f"El crudo ya descargado se conserva; vuelve a correr "
                        f"con --descargar y sigue desde donde se quedó.")
                # Espera creciente: si el servidor está saturado, insistir al
                # mismo ritmo lo empeora.
                time.sleep(PAUSA * 4 * intento)

        # Se valida la forma ANTES de guardar: un HTML de error o un 500
        # guardado como .json es una bomba de tiempo en la consolidación.
        try:
            datos = json.loads(cuerpo)
        except json.JSONDecodeError:
            raise SystemExit(f"Sección {sec}: la respuesta no es JSON. "
                             f"Primeros bytes: {cuerpo[:200]!r}")
        validar_respuesta(datos, sec)

        destino.write_bytes(cuerpo)
        print(f"  [{i}/{len(objetivo)}] sección {sec}: {len(cuerpo)//1024} KB")
        time.sleep(PAUSA)

    print(f"Crudo en {CRUDO.relative_to(RAIZ)}")


def validar_respuesta(datos, sec):
    """Una respuesta buena es una lista de 3 FeatureCollection, cada una con
    la propiedad de distrito que le toca. Cualquier otra cosa detiene todo:
    el endpoint no está versionado y puede cambiar sin avisar."""
    if not isinstance(datos, list) or len(datos) != len(CAPAS):
        raise SystemExit(
            f"Sección {sec}: se esperaban {len(CAPAS)} FeatureCollection y "
            f"llegó {type(datos).__name__} de "
            f"{len(datos) if isinstance(datos, list) else '?'}. "
            f"El endpoint cambió de forma; revisa CAPAS.")

    for fc, (prop, _, etiqueta) in zip(datos, CAPAS):
        # El isinstance no sobra: una lista del largo correcto pero con
        # cualquier cosa adentro pasaba el chequeo de arriba y reventaba aquí
        # con AttributeError, que no dice nada útil de qué llegó mal.
        if not isinstance(fc, dict) or fc.get("type") != "FeatureCollection" \
                or not fc.get("features"):
            raise SystemExit(f"Sección {sec}: {etiqueta} no es un "
                             f"FeatureCollection con features (llegó "
                             f"{type(fc).__name__}).")
        p = fc["features"][0].get("properties") or {}
        if prop not in p:
            raise SystemExit(
                f"Sección {sec}: {etiqueta} no trae la propiedad '{prop}' "
                f"(trae {sorted(p)}). El orden de las capas cambió.")


# ── Consolidación ───────────────────────────────────────────────────────────

def consolidar_distritos():
    """Junta los polígonos de distrito de todo el crudo, deduplicando.

    Devuelve {nombre_capa: {numero_distrito: feature}} y la cuenta de veces
    que se vio cada distrito, que es lo que permite verificar que el mismo
    distrito no llegó con dos geometrías distintas."""
    archivos = sorted(CRUDO.glob("seccion_*.json"))
    if not archivos:
        raise SystemExit(
            f"No hay crudo en {CRUDO.relative_to(RAIZ)}. "
            f"Corre primero con --descargar.")

    capas = {nombre: {} for _, nombre, _ in CAPAS}
    firmas = collections.defaultdict(set)

    for ruta in archivos:
        sec = int(ruta.stem.split("_")[1])
        datos = json.loads(ruta.read_text())
        validar_respuesta(datos, sec)

        for fc, (prop, nombre, etiqueta) in zip(datos, CAPAS):
            f = fc["features"][0]
            num = f["properties"][prop]
            firma = json.dumps(f["geometry"], sort_keys=True)
            firmas[(nombre, num)].add(hash(firma))
            if num not in capas[nombre]:
                props = {"numero": num, "etiqueta": f"{etiqueta} {num}"}
                if prop == "distrito_j":
                    props["circuito"] = f["properties"].get("circuito")
                capas[nombre][num] = {
                    "type": "Feature",
                    "geometry": f["geometry"],
                    "properties": props,
                }

    # El mismo distrito pedido desde secciones distintas tiene que traer el
    # mismo polígono. Si no, el endpoint es inestable y nada de esto sirve.
    inestables = [k for k, v in firmas.items() if len(v) > 1]
    if inestables:
        raise SystemExit(
            f"El endpoint devolvió geometrías distintas para el mismo "
            f"distrito: {inestables[:5]}. No se puede deduplicar.")

    return capas, len(archivos)


def verificar(capas, secciones):
    """Nada se publica sin que cuadre contra los catálogos."""
    esperado_f = {d["distrito_federal"] for d in secciones.values()}
    esperado_l = {d["distrito_local"] for d in secciones.values()}

    obtenido_f = set(capas["distritos_federales"])
    obtenido_l = set(capas["distritos_locales"])

    faltan_f = esperado_f - obtenido_f
    faltan_l = esperado_l - obtenido_l
    if faltan_f or faltan_l:
        raise SystemExit(
            f"Faltan distritos por descargar. Federales: {sorted(faltan_f)}. "
            f"Locales: {sorted(faltan_l)}. Corre --descargar de nuevo.")

    sobran_f = obtenido_f - esperado_f
    sobran_l = obtenido_l - esperado_l
    if sobran_f or sobran_l:
        raise SystemExit(
            f"El endpoint devolvió distritos que no están en los catálogos. "
            f"Federales: {sorted(sobran_f)}. Locales: {sorted(sobran_l)}. "
            f"Los dos insumos no son del mismo corte.")

    # Los judiciales no tienen catálogo contra el cual cuadrar: son nuevos y
    # no vienen en ningún archivo tabular. Sólo se puede reportar cuántos se
    # descubrieron, y quien los use tiene que saber que el número sale del
    # muestreo, no de una fuente que declare el total.
    return {
        "distritos_federales": len(obtenido_f),
        "distritos_locales": len(obtenido_l),
        "distritos_judiciales": len(capas["distritos_judiciales"]),
    }


def reconciliar_2024(secciones):
    """Compara el catálogo 2026 contra las secciones con resultado en 2024.

    NO es un chequeo de errores: es un hecho del dominio que hay que publicar.
    Entre 2024 y el corte de 2026 el INE reseccionó, así que unir el resultado
    de 2024 con la geografía de 2026 no es 1 a 1. Quien cruce las dos cosas
    tiene que saber cuáles secciones no tienen contraparte."""
    ruta = SALIDA / "resultados_seccion_2024.json"
    if not ruta.exists():
        return None
    res = json.loads(ruta.read_text())
    cat = {int(s) for s in secciones}
    con_resultado = {int(s) for s in res["secciones"]}

    return {
        "secciones_catalogo_2026": len(cat),
        "secciones_con_resultado_2024": len(con_resultado),
        "nuevas_sin_resultado_2024": sorted(cat - con_resultado),
        "con_resultado_2024_ya_no_vigentes": sorted(con_resultado - cat),
        "nota": "El catálogo del INE es del corte febrero 2026 y los "
                "resultados son del proceso 2024. Las secciones que aparecen "
                "en uno y no en el otro son producto de la reseccionalización, "
                "no un error de captura. El cruce entre ambos NO es 1 a 1.",
    }


def redondear(geom, decimales=6):
    """El endpoint publica 9 decimales: ~0.1 micrómetros, precisión que no
    existe en el dato original y que sólo infla el archivo. build_geo.py ya
    publica a 6 (~11 cm), así que se usa el mismo corte en todo el proyecto."""
    def rec(o):
        if isinstance(o, list):
            return [rec(x) for x in o]
        return round(o, decimales)
    return {"type": geom["type"], "coordinates": rec(geom["coordinates"])}


def escribir(capas, secciones, conteo, n_archivos):
    SALIDA_GEO.mkdir(parents=True, exist_ok=True)
    meta_geo = {
        "fuente": FUENTE_GEO,
        "fecha_corte": FECHA_CORTE,
        "metodologia": "Polígonos obtenidos del endpoint público "
                       "getConoceTuNuevoDistrito, una petición por combinación "
                       "de distrito y municipio. El polígono de un distrito es "
                       "idéntico se pida desde la sección que se pida, lo que "
                       "se verifica al consolidar. Coordenadas redondeadas a 6 "
                       "decimales (~11 cm), el mismo corte que build_geo.py.",
        "secciones_consultadas": n_archivos,
        # Geometría publicada por el INE, no cálculo nuestro: la única
        # transformación es el redondeo a 6 decimales.
        "procedencia": "dato",
        "generado_por": "backend/datalab/pipeline/build_ine_cartografia.py",
    }

    for _, nombre, etiqueta in CAPAS:
        feats = [dict(capas[nombre][k],
                      geometry=redondear(capas[nombre][k]["geometry"]))
                 for k in sorted(capas[nombre], key=int)]
        meta = dict(meta_geo, capa=etiqueta, total=len(feats))
        if nombre == "distritos_judiciales":
            meta["advertencia"] = (
                "Los distritos judiciales no vienen en ningún catálogo "
                "tabular del INE. Los que están aquí son los que aparecieron "
                "al consultar las secciones representantes. Si existe uno que "
                "no toca ninguna de esas secciones, no está.")
        (SALIDA_GEO / f"{nombre}.geojson").write_text(json.dumps({
            "type": "FeatureCollection", "metadata": meta, "features": feats,
        }, ensure_ascii=False), encoding="utf-8")

    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / "secciones_catalogo_2026.json").write_text(json.dumps({
        "metadata": {
            "fuente": FUENTE_CAT,
            "fecha_corte": FECHA_CORTE,
            "que_es": "Jerarquía oficial sección -> distrito federal, distrito "
                      "local y municipio, del catálogo del INE. NO trae "
                      "geometría de sección: el INE no la publica por este "
                      "medio. Ver PENDIENTE-INEGI-INE.md.",
            "cobertura": f"{len(secciones)} secciones",
            "conteo": conteo,
            "reconciliacion_2024": reconciliar_2024(secciones),
            "procedencia": "dato",
            "generado_por": "backend/datalab/pipeline/build_ine_cartografia.py",
        },
        "secciones": secciones,
    }, ensure_ascii=False), encoding="utf-8")


def autocomprobar():
    """Comprueba lo que no es obvio, sin red y sin frameworks.

        build_ine_cartografia.py --autocomprobar
    """
    # archivo() tiene que encontrar el catálogo aunque el nombre en disco esté
    # en NFD y el fragmento que se busca venga en NFC. Éste es el bug que se
    # come una tarde: en pantalla los dos nombres son idénticos.
    nfc = archivo(unicodedata.normalize("NFC", "Catálogo de Secciones.txt"))
    nfd = archivo(unicodedata.normalize("NFD", "Catálogo de Secciones.txt"))
    assert nfc == nfd, "archivo() no es estable ante NFC/NFD"

    # redondear() recorta la precisión pero no toca la estructura: un
    # MultiPolygon tiene que salir con el mismo anidamiento con que entró.
    g = {"type": "MultiPolygon",
         "coordinates": [[[[-91.938637027, 21.236212858], [-92.0, 21.1]]]]}
    r = redondear(g)
    assert r["type"] == "MultiPolygon"
    assert r["coordinates"] == [[[[-91.938637, 21.236213], [-92.0, 21.1]]]], r
    assert len(json.dumps(r)) < len(json.dumps(g))

    # representantes() debe cubrir TODOS los distritos con la menor cantidad de
    # secciones. Si dejara fuera un distrito, verificar() lo atraparía después,
    # pero tras 26 peticiones de red desperdiciadas.
    secs = leer_catalogos()
    reps = representantes(secs)
    for campo in ("distrito_federal", "distrito_local"):
        todos = {d[campo] for d in secs.values()}
        cubiertos = {secs[s][campo] for s in reps}
        assert todos == cubiertos, f"{campo}: sin cubrir {todos - cubiertos}"
    assert len(reps) < len(secs), "los representantes no ahorran peticiones"

    # validar_respuesta() tiene que rechazar lo que no es la forma esperada.
    for malo in ([], {"type": "FeatureCollection"}, [1, 2, 3],
                 [{"type": "FeatureCollection", "features": []}] * 3):
        try:
            validar_respuesta(malo, "prueba")
        except SystemExit:
            pass
        else:
            raise AssertionError(f"validar_respuesta aceptó {malo!r}")

    print(f"OK · {len(secs)} secciones · {len(reps)} representantes "
          f"({len(reps) * 100 // len(secs)}% de las peticiones)")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--descargar", action="store_true",
                    help="baja el crudo del endpoint del INE antes de consolidar")
    ap.add_argument("--autocomprobar", action="store_true",
                    help="corre las comprobaciones internas y sale")
    args = ap.parse_args()

    if args.autocomprobar:
        return autocomprobar()

    print("Catálogos del INE…")
    secciones = leer_catalogos()
    print(f"  {len(secciones)} secciones · "
          f"{len({d['distrito_federal'] for d in secciones.values()})} distritos federales · "
          f"{len({d['distrito_local'] for d in secciones.values()})} distritos locales")

    if args.descargar:
        print("Descargando geometría…")
        descargar(secciones)

    print("Consolidando…")
    capas, n = consolidar_distritos()
    conteo = verificar(capas, secciones)
    print(f"  {n} respuestas · " + " · ".join(f"{v} {k.split('_')[1]}"
                                              for k, v in conteo.items()))

    rec = reconciliar_2024(secciones)
    if rec:
        print(f"  reconciliación 2024: {len(rec['nuevas_sin_resultado_2024'])} "
              f"secciones nuevas · "
              f"{len(rec['con_resultado_2024_ya_no_vigentes'])} ya no vigentes")

    escribir(capas, secciones, conteo, n)
    print("Listo.")


if __name__ == "__main__":
    main()
