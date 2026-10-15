#!/usr/bin/env python3
"""Manifiesto de fuentes — la trazabilidad, generada del propio sistema.

    backend/datalab/venv/bin/python backend/datalab/pipeline/build_fuentes.py
    backend/datalab/venv/bin/python backend/datalab/pipeline/build_fuentes.py --autocomprobar

Décimo pipeline. Salida: frontend/data/fuentes.json

POR QUÉ ESTO EXISTE
───────────────────
fuentes.html es la página que declara de dónde viene cada dato del sistema.
Estaba escrita a mano, y en la auditoría de conjunto resultó ser la pieza más
desfasada de todas: citaba un solo archivo —`data/mock/territorio.json`— que
llevaba fases sin usarse, mientras el sistema servía veintitrés.

No es casualidad. Una lista de fuentes escrita a mano se desfasa por
construcción: se actualiza sólo si alguien se acuerda, y nadie se acuerda. La
única versión que se mantiene sola es la que se genera de los datos mismos.

Cada pipeline ya declara su `fuente`, `fecha_corte`, `procedencia` y
`generado_por` en la metadata de lo que publica. Este script los recorre y arma
el manifiesto. Si un archivo no declara algo, NO se inventa: se marca como
faltante, y el propio manifiesto se convierte en la auditoría de qué le falta
declarar a quién.

DÓNDE ESTÁ LA FUENTE EN CADA ARCHIVO
────────────────────────────────────
No todos la ponen en el mismo sitio, porque cada pipeline nació en su fase:

  la mayoría              metadata.fuente
  encuestas_2026          metadata.casa (es una casa encuestadora)
  proyeccion_2027         metadata.fuente_base (la base de la simulación)
  correlaciones_2024      metadata.fuentes (varias, es un cruce)
  contexto_campeche       por bloque, no a nivel de archivo

Se leen todas esas formas en vez de forzar un cambio de esquema en nueve
pipelines ya verificados. Lo que sí se hace es DECLARAR la irregularidad.
"""

import argparse
import json
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[3]
DATOS = RAIZ / "frontend/data"
SALIDA = DATOS / "fuentes.json"

# Los pipelines no viven todos en el mismo sitio. `build_geo.py` y
# `build_inegi.py` nacieron dentro de frontend/data/geo/ —antes de que
# existiera backend/datalab/pipeline/— y siguen ahí porque escriben en su
# propio directorio. Buscarlos sólo en pipeline/ hacía que el manifiesto
# reportara 10 pipelines cuando son 12, y que sus salidas apareciesen como
# "captura manual" siendo generadas.
DIRS_PIPELINE = [RAIZ / "backend/datalab/pipeline", RAIZ / "frontend/data/geo"]

# Dónde buscar la fuente, en orden. La primera que exista gana.
CLAVES_FUENTE = ["fuente", "casa", "fuente_base", "fuente_oficial"]

# Carpetas que no son capa servida: el mock quedó muerto en la Fase 2 y se
# lista como tal en vez de omitirse, para que su presencia sea visible.
IGNORAR = {"mock"}

# Familias, para que el manifiesto se lea por origen y no por carpeta.
FAMILIAS = {
    "electoral": "Resultados y cartografía electoral",
    "geo": "Capas geoespaciales",
    "censo": "Censo de Población y Vivienda",
    "": "Contexto estatal",
}


def fuente_de(meta):
    """La fuente declarada, mirando los nombres que usa cada pipeline."""
    for k in CLAVES_FUENTE:
        v = meta.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip(), k
    # correlaciones publica varias, porque es un cruce.
    v = meta.get("fuentes")
    if isinstance(v, dict):
        partes = [str(x) for x in v.values() if x]
        if partes:
            return " · ".join(sorted(set(partes))), "fuentes"
    return None, None


def leer(ruta):
    try:
        d = json.loads(ruta.read_text())
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    meta = d.get("metadata")
    if not isinstance(meta, dict):
        meta = {}
    fuente, clave = fuente_de(meta)

    # Cuántos registros trae, para que el manifiesto diga qué tan grande es
    # cada cosa sin tener que abrirla.
    registros = None
    for k, v in d.items():
        if k in ("metadata", "type") or not isinstance(v, (list, dict)):
            continue
        registros = registros or {}
        registros[k] = len(v)

    return {
        "fuente": fuente,
        "clave_fuente": clave,
        "fecha_corte": meta.get("fecha_corte"),
        "procedencia": meta.get("procedencia"),
        # Un archivo puede declararla desglosada en vez de a nivel de archivo.
        # La vista necesita distinguirlo de un hueco real.
        "procedencia_desglosada": bool(meta.get("procedencia_por_campo")
                                       or meta.get("procedencia_por_bloque")),
        "generado_por": meta.get("generado_por"),
        "que_es": meta.get("que_es") or meta.get("nombre"),
        "registros": registros,
        "campos_metadata": len(meta),
        "_meta": meta,
    }


def faltantes(info, meta):
    """Qué no está declarado. Un `null` EXPLÍCITO no cuenta como faltante.

    La diferencia importa: escuelas_campeche.geojson trae
    `"fecha_corte": null` a propósito, porque el catálogo CCT de la SEP no
    publica una. Eso es una declaración —"la fuente no lo dice"— y es lo
    contrario de un descuido. Tratarlas igual castigaría al pipeline que se
    tomó la molestia de ser explícito.
    """
    # Una declaración por campo o por bloque es MÁS precisa que una a nivel de
    # archivo, no menos: contexto_campeche mezcla dato del INEGI, estimación
    # propia y simulación, y resumirlo en un solo valor sería falso. Se acepta
    # como declarada la procedencia que viene desglosada.
    desglosada = {"procedencia"} if (
        meta.get("procedencia_por_campo") or meta.get("procedencia_por_bloque")
    ) else set()

    f = []
    for campo, valor in (("fuente", info.get("fuente")),
                         ("fecha_corte", info.get("fecha_corte")),
                         ("procedencia", info.get("procedencia")),
                         ("generado_por", info.get("generado_por"))):
        if valor:
            continue
        if campo in meta and meta[campo] is None:
            continue          # declarado como nulo: es una respuesta, no un hueco
        if campo in desglosada:
            continue          # declarado por campo/bloque: más fino, no menos
        f.append(campo)
    return f


def construir():
    archivos, muertos = [], []
    for ruta in sorted(list(DATOS.rglob("*.json")) + list(DATOS.rglob("*.geojson"))):
        if ruta.name == SALIDA.name:
            continue
        rel = ruta.relative_to(DATOS)
        familia = rel.parts[0] if len(rel.parts) > 1 else ""
        if familia in IGNORAR:
            muertos.append(str(rel))
            continue
        info = leer(ruta)
        meta_cruda = info.pop("_meta", {})
        info.update({
            "archivo": str(rel),
            "familia": familia,
            "bytes": ruta.stat().st_size,
            "falta_declarar": faltantes(info, meta_cruda),
        })
        archivos.append(info)

    pipes = sorted({p.name for d in DIRS_PIPELINE for p in d.glob("build_*.py")})
    generados = {a["generado_por"].split("/")[-1] for a in archivos
                 if a.get("generado_por")}
    return archivos, muertos, pipes, sorted(generados)


def verificar(archivos, pipes, generados):
    if not archivos:
        raise SystemExit("No se encontró ningún archivo de datos.")
    for a in archivos:
        if a.get("error"):
            raise SystemExit(f"{a['archivo']}: no se pudo leer ({a['error']}).")
        if a["bytes"] <= 0:
            raise SystemExit(f"{a['archivo']}: archivo vacío.")
    # Todo pipeline que dice haber generado algo tiene que existir.
    for g in generados:
        if g not in pipes:
            raise SystemExit(
                f"Un archivo dice estar generado por '{g}', que no está en "
                f"{' ni en '.join(str(d.relative_to(RAIZ)) for d in DIRS_PIPELINE)}. "
                f"O se renombró el pipeline o la metadata quedó vieja.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--autocomprobar", action="store_true")
    args = ap.parse_args()
    if args.autocomprobar:
        return autocomprobar()

    archivos, muertos, pipes, generados = construir()
    verificar(archivos, pipes, generados)

    sin_declarar = [a for a in archivos if a["falta_declarar"]]
    total = sum(a["bytes"] for a in archivos)

    print(f"{len(archivos)} archivos servidos · {total // 1024} KB · "
          f"{len(pipes)} pipelines")
    for fam, etiqueta in FAMILIAS.items():
        de_fam = [a for a in archivos if a["familia"] == fam]
        if de_fam:
            print(f"  {etiqueta}: {len(de_fam)} archivos, "
                  f"{sum(a['bytes'] for a in de_fam) // 1024} KB")
    if muertos:
        print(f"  fuera de la capa servida: {muertos}")
    print(f"\n{len(sin_declarar)} archivos con algo sin declarar:")
    for a in sin_declarar:
        print(f"  {a['archivo']:44} falta: {', '.join(a['falta_declarar'])}")

    SALIDA.write_text(json.dumps({
        "metadata": {
            "procedencia": "calculo",
            "que_es": "Manifiesto de todo lo que el sistema sirve, generado "
                      "leyendo la metadata de cada archivo publicado.",
            "por_que_generado":
                "Una lista de fuentes escrita a mano se desfasa por "
                "construcción. Ésta se regenera con el resto de los pipelines, "
                "así que no puede quedarse vieja sin que alguien lo note.",
            "como_se_lee_la_fuente":
                "Cada pipeline la declara donde le tocó por su fase: `fuente` "
                "en la mayoría, `casa` en encuestas, `fuente_base` en la "
                "proyección, `fuentes` en correlaciones. Se leen todas esas "
                "formas en vez de forzar un cambio de esquema en nueve "
                "pipelines ya verificados.",
            "lo_que_no_hace":
                "Rellenar. Si un archivo no declara su fuente o su fecha de "
                "corte, se marca en `falta_declarar` en vez de inventarla.",
            "fuera_de_la_capa_servida": muertos,
            "pipelines": pipes,
            "total_archivos": len(archivos),
            "total_bytes": total,
            "archivos_con_faltantes": len(sin_declarar),
            "familias": FAMILIAS,
            "generado_por": "backend/datalab/pipeline/build_fuentes.py",
        },
        "archivos": archivos,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"\nListo. {SALIDA.relative_to(RAIZ)}")


def autocomprobar():
    archivos, muertos, pipes, generados = construir()
    verificar(archivos, pipes, generados)

    # Cada archivo servido tiene ruta, tamaño y familia.
    for a in archivos:
        assert a["archivo"] and a["bytes"] > 0
        assert a["familia"] in FAMILIAS, a["familia"]

    # La lectura de la fuente cubre las cuatro formas que usan los pipelines.
    assert fuente_de({"fuente": "A"}) == ("A", "fuente")
    assert fuente_de({"casa": "B"}) == ("B", "casa")
    assert fuente_de({"fuente_base": "C"}) == ("C", "fuente_base")
    assert fuente_de({"fuentes": {"x": "D", "y": "E"}})[0] == "D · E"
    assert fuente_de({}) == (None, None), "sin fuente no se inventa una"

    # faltantes() señala exactamente lo que no está.
    assert faltantes({"fuente": "A"}, {}) == ["fecha_corte", "procedencia",
                                              "generado_por"]
    assert faltantes({"fuente": "A", "fecha_corte": "2024-06",
                      "procedencia": "dato", "generado_por": "x.py"}, {}) == []
    # Un null explícito es una declaración, no un hueco.
    assert "fecha_corte" not in faltantes({"fuente": "A"}, {"fecha_corte": None})

    # Los archivos grandes del sistema tienen que estar en el manifiesto: si
    # alguno se cae, la página de trazabilidad dejaría de listarlo en silencio.
    nombres = {a["archivo"] for a in archivos}
    for esperado in ("electoral/resultados_seccion_2024.json",
                     "geo/escuelas_campeche.geojson",
                     "censo/poblacion_2020.json"):
        assert esperado in nombres, f"falta {esperado} en el manifiesto"

    sin = sum(1 for a in archivos if a["falta_declarar"])
    print(f"OK · {len(archivos)} archivos · {len(pipes)} pipelines · "
          f"{sin} con algo sin declarar")


if __name__ == "__main__":
    main()
