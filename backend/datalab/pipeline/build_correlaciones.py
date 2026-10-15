#!/usr/bin/env python3
"""Correlaciones — cruce de demografía, socioeconómico y participación.

    backend/datalab/venv/bin/python backend/datalab/pipeline/build_correlaciones.py
    backend/datalab/venv/bin/python backend/datalab/pipeline/build_correlaciones.py --autocomprobar

Octavo pipeline. Salida: frontend/data/electoral/correlaciones_2024.json

POR QUÉ ESTA FASE IBA AL FINAL
──────────────────────────────
Una correlación es la forma más barata de producir una conclusión que parece
rigurosa. Basta cruzar dos columnas y publicar un número con tres decimales.
Este pipeline calcula esos números y, sobre todo, calcula CUÁNTO VALEN.

TRES COSAS QUE HAY QUE SABER ANTES DE LEER CUALQUIER r
─────────────────────────────────────────────────────

1. EL INGRESO NO EXISTE COMO VARIABLE. La fase pedía cruzar ingreso con
   participación. El bloque `nse` de contexto_campeche.json es una estimación
   ESTATAL, y su propio archivo lo dice: "NO es un porcentaje por municipio: el
   modelo no baja a ese nivel y no se va a inventar el desglose". Lo único que
   hay por municipio es una tipología cualitativa de cuatro grupos. Así que no
   hay correlación ingreso-participación, y no se fabrica una.

2. CON n=12 CASI NADA ES DISTINGUIBLE DE CERO. Hay 13 municipios y el Censo
   2020 sólo cubre 12 (Dzitbalché se creó en 2021). El intervalo de confianza
   de una correlación con n=12 es enorme:

       participación vs % de 50 y más    r = +0.480   IC95 [−0.130, +0.826]

   Ese r parece una relación moderada y su intervalo incluye el cero: es
   compatible con no haber ninguna relación. Publicar el 0.480 sin el
   intervalo sería el error que esta fase existe para no cometer.

3. HAY 542 SECCIONES Y ESE ES EL NIVEL DONDE SÍ SE PUEDE MEDIR. Las variables
   electorales existen por sección, y el catálogo del INE clasifica cada una
   como urbana, rural o mixta. Ahí n es grande y los intervalos se cierran.

Por eso la salida separa DOS NIVELES con etiquetas distintas de fiabilidad, en
vez de mezclarlos en una sola tabla donde todos los números se ven igual.

LA FALACIA ECOLÓGICA, QUE AQUÍ NO ES UN TECNICISMO
──────────────────────────────────────────────────
Todo esto son datos AGREGADOS. Que los municipios con más gente mayor voten
más NO dice que las personas mayores voten más: puede ser que en esos
municipios vote más todo el mundo, por razones que no tienen que ver con la
edad. Concluir sobre individuos desde agregados se llama falacia ecológica, y
el ejemplo clásico de los manuales es, literalmente, un estudio de datos
electorales (Robinson, 1950).

Ninguna cifra de este archivo permite decir quién vota. Todas dicen cómo se
comportan las UNIDADES TERRITORIALES.
"""

import argparse
import json
import math
import pathlib
import statistics

RAIZ = pathlib.Path(__file__).resolve().parents[3]
ELECTORAL = RAIZ / "frontend/data/electoral"
CENSO = RAIZ / "frontend/data/censo/poblacion_2020.json"
CONTEXTO = RAIZ / "frontend/data/contexto_campeche.json"
SALIDA = ELECTORAL / "correlaciones_2024.json"

Z95 = 1.959964

# Con menos observaciones que esto, un coeficiente se mueve tanto al quitar un
# solo caso que no describe nada. No es un corte de significancia: es el punto
# a partir del cual la cifra se publica con la etiqueta de fiabilidad baja.
N_MINIMO_FIABLE = 30


def pearson(x, y):
    """Coeficiente de correlación de Pearson, sin dependencias."""
    n = len(x)
    if n < 3:
        return None
    mx, my = statistics.fmean(x), statistics.fmean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    if sx == 0 or sy == 0:
        # Una variable constante no correlaciona con nada: no es que la
        # relación sea cero, es que la pregunta no aplica.
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


def intervalo_r(r, n):
    """IC95 de una correlación, por la transformación z de Fisher.

    r no se distribuye normal —está acotado en [−1, 1] y su varianza depende
    de su propio valor—, así que no se le puede poner un ± simétrico. La
    transformación de Fisher, arctanh(r), sí es aproximadamente normal con
    error estándar 1/sqrt(n−3); se calcula el intervalo ahí y se devuelve con
    tanh. Por eso el intervalo resultante es asimétrico, que es lo correcto.
    """
    if r is None or n < 4 or abs(r) >= 1:
        return None
    z = math.atanh(r)
    se = 1 / math.sqrt(n - 3)
    return [round(math.tanh(z - Z95 * se), 3), round(math.tanh(z + Z95 * se), 3)]


def jackknife(x, y):
    """Cuánto se mueve r al quitar una observación, una por una.

    Con pocas observaciones un solo caso puede sostener la correlación entera.
    Este número dice si el resultado describe al conjunto o a un municipio.
    """
    base = pearson(x, y)
    if base is None or len(x) < 5:
        return None
    peor, quien = 0.0, None
    for i in range(len(x)):
        xs = x[:i] + x[i + 1:]
        ys = y[:i] + y[i + 1:]
        r = pearson(xs, ys)
        if r is not None and abs(r - base) > peor:
            peor, quien = abs(r - base), i
    return {"maximo_cambio": round(peor, 3), "indice": quien}


def correlacion(etiqueta, x, y, unidades, fuentes, etiquetas=None):
    n = len(x)
    r = pearson(x, y)
    ic = intervalo_r(r, n)
    jk = jackknife(x, y)
    cruza_cero = bool(ic and ic[0] < 0 < ic[1])
    return {
        "etiqueta": etiqueta,
        "n": n,
        "unidad": unidades,
        "fuentes": fuentes,
        "r": round(r, 3) if r is not None else None,
        "ic95": ic,
        "incluye_cero": cruza_cero,
        "fiabilidad": "baja" if n < N_MINIMO_FIABLE else "aceptable",
        "jackknife": jk,
        "lectura": (
            "El intervalo incluye el cero: estos datos son compatibles con que "
            "no haya ninguna relación. El coeficiente no se puede interpretar."
            if cruza_cero else
            "El intervalo no incluye el cero: hay asociación entre las dos "
            "variables agregadas. Sigue sin decir nada sobre personas."
        ),
    }


def por_grupo(valores, grupos):
    """Media e IC95 de la media por grupo. Para variables categóricas.

    Con una categórica no hay correlación que calcular: se comparan medias.
    El IC de cada media es lo que permite ver si los grupos se distinguen —
    dos medias distintas con intervalos que se solapan no son dos medias
    distintas.
    """
    salida = []
    for g in sorted(set(grupos)):
        sub = [v for v, gg in zip(valores, grupos) if gg == g]
        if len(sub) < 2:
            continue
        m = statistics.fmean(sub)
        se = statistics.stdev(sub) / math.sqrt(len(sub))
        salida.append({
            "grupo": g, "n": len(sub),
            "media": round(m, 2),
            "ic95": [round(m - Z95 * se, 2), round(m + Z95 * se, 2)],
        })
    return sorted(salida, key=lambda s: -s["n"])


def cargar():
    sec = json.loads((ELECTORAL / "resultados_seccion_2024.json").read_text())
    mun = json.loads((ELECTORAL / "resultados_municipio_2024.json").read_text())
    cat = json.loads((ELECTORAL / "secciones_catalogo_2026.json").read_text())
    cen = json.loads(CENSO.read_text())
    ctx = json.loads(CONTEXTO.read_text())
    return sec, mun, cat, cen, ctx


def nivel_seccion(sec, cat):
    S = [(s, r) for s, r in sec["secciones"].items()]
    part = [r["participacion"] or 0.0 for _, r in S]
    nul = [r["nulos_pct"] or 0.0 for _, r in S]
    ln = [float(r["lista_nominal"]) for _, r in S]
    mar = [r["margen"] for _, r in S]

    F = {"electoral": sec["metadata"]["fuente"]}
    pares = [
        ("Participación y voto nulo", part, nul),
        ("Participación y tamaño de la sección", part, ln),
        ("Participación y margen de victoria", part, mar),
        ("Voto nulo y margen de victoria", nul, mar),
    ]
    corr = [correlacion(e, x, y, "sección electoral", F) for e, x, y in pares]

    # Urbano/rural es lo único demográfico que existe a nivel sección, y viene
    # del catálogo del INE. Es categórica: se comparan medias, no se correlaciona.
    tipos, parts = [], []
    for s, r in S:
        t = cat["secciones"].get(s, {}).get("tipo")
        if t:
            tipos.append(t)
            parts.append(r["participacion"] or 0.0)
    grupos = por_grupo(parts, tipos)

    return {
        "correlaciones": corr,
        "participacion_por_tipo": {
            "grupos": grupos,
            "n_con_tipo": len(tipos),
            "fuente_tipo": cat["metadata"]["fuente"],
            "nota": "El tipo de sección (urbana, rural, mixta) lo declara el "
                    "catálogo del INE. Es la única variable de contexto que "
                    "existe al nivel donde hay muchas observaciones.",
        },
    }


def nivel_municipal(mun, cen):
    comunes = sorted(set(cen["municipios"]) & set(mun["municipios"]))
    m = mun["municipios"]
    c = cen["municipios"]

    part = [m[k]["participacion"] for k in comunes]
    nulos = [m[k]["nulos_pct"] for k in comunes]
    p50 = [c[k]["mayores_50"] / c[k]["poblacion_total"] * 100 for k in comunes]
    p18 = [c[k]["menores_18"] / c[k]["poblacion_total"] * 100 for k in comunes]
    muj = [c[k]["mujeres"] / c[k]["poblacion_total"] * 100 for k in comunes]
    pob = [float(c[k]["poblacion_total"]) for k in comunes]

    F = {"electoral": mun["metadata"]["fuente"], "demografia": cen["metadata"]["fuente"]}
    pares = [
        ("Participación y población de 50 y más", part, p50),
        ("Participación y población menor de 18", part, p18),
        ("Participación y proporción de mujeres", part, muj),
        ("Participación y tamaño del municipio", part, pob),
        ("Voto nulo y población de 50 y más", nulos, p50),
    ]
    corr = []
    for e, x, y in pares:
        d = correlacion(e, x, y, "municipio", F)
        if d["jackknife"] and d["jackknife"]["indice"] is not None:
            d["jackknife"]["municipio"] = m[comunes[d["jackknife"]["indice"]]]["nombre"]
        corr.append(d)

    return {
        "municipios": comunes,
        "correlaciones": corr,
        "advertencias": {
            "n_pequeno":
                f"Sólo hay {len(comunes)} observaciones. El intervalo de "
                f"confianza de una correlación con esta n es tan ancho que "
                f"casi cualquier coeficiente resulta compatible con cero.",
            "falta_dzitbalche":
                "El Censo 2020 no incluye a Dzitbalché, que se erigió en "
                "municipio en 2021. Son 12 de 13.",
            "calkini_contaminado":
                "La cifra censal de Calkiní INCLUYE el territorio que hoy es "
                "Dzitbalché; su resultado electoral de 2024 ya no. Es la única "
                "observación cuyas dos variables no describen el mismo "
                "territorio. Quitarla mueve r de +0.480 a +0.464: poco, pero "
                "queda dicho.",
            "desfase_temporal":
                "El Censo es de 2020 y la elección de 2024. Cuatro años de "
                "diferencia en la composición de la población.",
        },
    }


def nivel_nse(ctx, mun):
    """NSE sólo existe como tipología cualitativa. Se compara, no se correlaciona."""
    nse = ctx.get("nse", {})
    tip = nse.get("tipologia_municipal", {})
    m = mun["municipios"]

    grupos = []
    for g in tip.get("grupos", []):
        claves = [k for k in g.get("municipios", []) if k in m]
        if not claves:
            continue
        parts = [m[k]["participacion"] for k in claves]
        d = {
            "etiqueta": g.get("etiqueta"),
            "rasgo": g.get("rasgo"),
            "municipios": [m[k]["nombre"] for k in claves],
            "n": len(claves),
            "participacion_media": round(statistics.fmean(parts), 2),
        }
        if len(parts) > 1:
            se = statistics.stdev(parts) / math.sqrt(len(parts))
            d["ic95"] = [round(d["participacion_media"] - Z95 * se, 2),
                         round(d["participacion_media"] + Z95 * se, 2)]
        grupos.append(d)

    return {
        "grupos": sorted(grupos, key=lambda g: -g["n"]),
        "procedencia": tip.get("procedencia", "inferencia"),
        "por_que_no_hay_correlacion":
            "El bloque NSE es una estimación ESTATAL. Su propio archivo declara "
            "que el modelo no baja a nivel municipal y que el desglose no se "
            "va a inventar. Lo único municipal es esta tipología cualitativa "
            "de cuatro grupos, así que no hay una variable numérica de ingreso "
            "con la cual correlacionar.",
        "advertencia_grupos":
            "Varios grupos tienen uno o dos municipios. Una media de un solo "
            "caso es ese caso, no una media: se muestra sin intervalo porque "
            "no se puede calcular.",
        "fuente": nse.get("fuente"),
        "metodologia": nse.get("metodologia"),
    }


def verificar(d):
    todas = d["seccion"]["correlaciones"] + d["municipal"]["correlaciones"]
    for c in todas:
        if c["r"] is not None and not (-1 <= c["r"] <= 1):
            raise SystemExit(f"{c['etiqueta']}: r fuera de rango ({c['r']}).")
        if c["ic95"]:
            lo, hi = c["ic95"]
            if lo > hi:
                raise SystemExit(f"{c['etiqueta']}: intervalo invertido.")
            if not (lo <= c["r"] <= hi):
                raise SystemExit(
                    f"{c['etiqueta']}: r={c['r']} fuera de su propio intervalo "
                    f"[{lo}, {hi}].")
        # La etiqueta de fiabilidad tiene que corresponder con la n.
        esperada = "baja" if c["n"] < N_MINIMO_FIABLE else "aceptable"
        if c["fiabilidad"] != esperada:
            raise SystemExit(f"{c['etiqueta']}: fiabilidad mal etiquetada.")

    # Las municipales tienen que salir todas con fiabilidad baja: son 12.
    if any(c["fiabilidad"] != "baja" for c in d["municipal"]["correlaciones"]):
        raise SystemExit("Alguna correlación municipal no está marcada como "
                         "de fiabilidad baja, y con n=12 todas lo son.")

    # Los grupos de un solo municipio no pueden traer intervalo.
    for g in d["nse"]["grupos"]:
        if g["n"] < 2 and "ic95" in g:
            raise SystemExit(f"{g['etiqueta']}: intervalo con n={g['n']}.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--autocomprobar", action="store_true")
    args = ap.parse_args()
    if args.autocomprobar:
        return autocomprobar()

    sec, mun, cat, cen, ctx = cargar()
    d = {
        "seccion": nivel_seccion(sec, cat),
        "municipal": nivel_municipal(mun, cen),
        "nse": nivel_nse(ctx, mun),
    }
    verificar(d)

    print("NIVEL SECCIÓN — n grande, intervalos cerrados")
    for c in d["seccion"]["correlaciones"]:
        print(f"  {c['etiqueta']:42} r={c['r']:+.3f}  IC95 {c['ic95']}  n={c['n']}"
              + ("  ← incluye cero" if c["incluye_cero"] else ""))
    print("  participación por tipo de sección:")
    for g in d["seccion"]["participacion_por_tipo"]["grupos"]:
        print(f"    {g['grupo']:12} n={g['n']:3}  {g['media']:5.2f}%  IC95 {g['ic95']}")

    print("\nNIVEL MUNICIPAL — n=12, intervalos enormes")
    for c in d["municipal"]["correlaciones"]:
        marca = "  ← INCLUYE CERO" if c["incluye_cero"] else ""
        print(f"  {c['etiqueta']:42} r={c['r']:+.3f}  IC95 {c['ic95']}{marca}")

    print("\nNSE — sólo tipología cualitativa, no hay variable numérica")
    for g in d["nse"]["grupos"]:
        ic = f"  IC95 {g['ic95']}" if "ic95" in g else "  (n=1, sin intervalo)"
        print(f"  {g['etiqueta']:22} n={g['n']}  {g['participacion_media']:5.2f}%{ic}")

    SALIDA.write_text(json.dumps({
        "metadata": {
            "procedencia": "inferencia",
            "que_es": "Asociación entre variables agregadas por unidad "
                      "territorial. Ninguna cifra permite concluir sobre "
                      "personas.",
            "falacia_ecologica":
                "Todos estos datos son agregados. Que los municipios con más "
                "población mayor tengan más participación NO dice que las "
                "personas mayores voten más: puede ser que en esos municipios "
                "vote más todo el mundo por razones ajenas a la edad. "
                "Concluir sobre individuos desde agregados es la falacia "
                "ecológica, y el ejemplo clásico es un estudio electoral "
                "(Robinson, 1950).",
            "no_es_causalidad":
                "Una correlación no dice qué causa qué, ni si hay una tercera "
                "variable que explique a las dos.",
            "metodo": {
                "coeficiente": "Pearson",
                "intervalo": "IC95 por transformación z de Fisher. r no se "
                             "distribuye normal, así que no admite un ± "
                             "simétrico: el intervalo es asimétrico a propósito.",
                "jackknife": "Cuánto se mueve r al quitar una observación. Con "
                             "pocas unidades, un solo caso puede sostener la "
                             "correlación entera.",
                "n_minimo_fiable": N_MINIMO_FIABLE,
            },
            "fuentes": {
                "electoral": sec["metadata"]["fuente"],
                "demografia": cen["metadata"]["fuente"],
                "tipo_seccion": cat["metadata"]["fuente"],
                "nse": ctx.get("nse", {}).get("fuente"),
            },
            "fecha_corte": "2024-06",
            "generado_por": "backend/datalab/pipeline/build_correlaciones.py",
        },
        **d,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"\nListo. {SALIDA.relative_to(RAIZ)}")


def autocomprobar():
    # Pearson contra casos conocidos.
    assert abs(pearson([1, 2, 3, 4], [2, 4, 6, 8]) - 1.0) < 1e-9
    assert abs(pearson([1, 2, 3, 4], [8, 6, 4, 2]) + 1.0) < 1e-9
    assert pearson([1, 1, 1, 1], [1, 2, 3, 4]) is None, "constante: no aplica"

    # El intervalo de Fisher se estrecha con n y es asimétrico salvo en r=0.
    a = intervalo_r(0.5, 12)
    b = intervalo_r(0.5, 500)
    assert (b[1] - b[0]) < (a[1] - a[0]), "más n debería cerrar el intervalo"
    assert a[0] < 0.5 < a[1]
    assert abs((0.5 - a[0]) - (a[1] - 0.5)) > 0.01, "debería ser asimétrico"
    simetrico = intervalo_r(0.0, 100)
    assert abs(simetrico[0] + simetrico[1]) < 1e-9, "en r=0 sí es simétrico"

    # El caso que motiva toda la fase: n=12 con r moderado incluye el cero.
    ic = intervalo_r(0.48, 12)
    assert ic[0] < 0 < ic[1], ic

    sec, mun, cat, cen, ctx = cargar()
    d = {"seccion": nivel_seccion(sec, cat), "municipal": nivel_municipal(mun, cen),
         "nse": nivel_nse(ctx, mun)}
    verificar(d)

    munс = d["municipal"]["correlaciones"]
    cero = sum(1 for c in munс if c["incluye_cero"])
    secc = d["seccion"]["correlaciones"]
    print(f"OK · sección: {len(secc)} correlaciones, "
          f"{sum(1 for c in secc if c['incluye_cero'])} incluyen cero · "
          f"municipal: {len(munс)}, {cero} incluyen cero · "
          f"NSE: {len(d['nse']['grupos'])} grupos")


if __name__ == "__main__":
    main()
