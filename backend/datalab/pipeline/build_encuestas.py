#!/usr/bin/env python3
"""Tracking de intención de voto — Demoscopia, Campeche 2025-2026.

    backend/datalab/venv/bin/python backend/datalab/pipeline/build_encuestas.py
    backend/datalab/venv/bin/python backend/datalab/pipeline/build_encuestas.py --autocomprobar

Quinto pipeline. Convierte la serie de tracking en el insumo que le faltaba a
la proyección: una medida de volatilidad calculada del dato real, en vez del
supuesto que se usaba antes.

Insumo (no se toca):
  backend/datalab/uploads/encuestasDemoscopia/
    tracking_demoscopia_campeche_2025_2026.csv

Salida:
  frontend/data/electoral/encuestas_2026.json

PROCEDENCIA DEL INSUMO — IMPORTA
────────────────────────────────
La serie es TRANSCRIPCIÓN MANUAL desde la interfaz de tracking de Demoscopia,
no una descarga oficial de su base. Está verificada matemáticamente (los 19
meses suman exactamente 100.0%), pero verificar la aritmética no es lo mismo
que verificar el origen: un error de lectura que respete la suma no lo detecta
nadie. Se publica como `dato_transcrito`, no como `dato`.

LO QUE LA SERIE SÍ MIDE Y LO QUE NO
───────────────────────────────────
Cada mes es una muestra de 1,000 personas. Eso significa que una parte del
movimiento mes a mes NO es cambio de opinión: es error de muestreo. Con la
MoE declarada (±3.8%, que implica un efecto de diseño de 1.5 sobre muestreo
aleatorio simple), el error esperado de una fuerza al 38% es de ±1.9 pp — más
grande que la desviación observada de Morena en toda la serie.

    fuerza   sd observada   sd de muestreo   sd REAL
    morena       1.57            1.88          0.00   <- todo es ruido
    mc           1.90            1.74          0.76
    pan          1.11            0.69          0.87
    pri          0.99            0.82          0.55
    pvem         0.71            0.68          0.23   <- marginal
    pt           0.58            0.65          0.00   <- todo es ruido
    no_decide    3.44            1.41          3.14   <- el que más se mueve

Conclusión que cambia el modelo: **la desviación de la serie NO sirve como
medida de volatilidad**, porque para el líder es indistinguible de cero. Lo
que sí es real y direccional es la DERIVA: Morena baja 3.37 pp y MC sube 3.83
pp entre los primeros y los últimos tres meses. Eso es señal, no ruido.

EL INDECISO NO ES UN PARTIDO
────────────────────────────
`no_decide` va de 8.9% a 20.7% y es la categoría con más movimiento real de
todas. No se reparte ni se ignora: se excluye del denominador para calcular
VOTO EFECTIVO, que es lo único comparable con un resultado electoral (donde
los porcentajes son sobre votos emitidos, y quien no decidió no votó o votó
por alguien). Ese reparto es CÁLCULO, y el indeciso se publica aparte.
"""

import argparse
import csv
import json
import math
import pathlib
import statistics
import sys

try:
    import numpy as np
except ImportError:
    sys.exit("Falta numpy. Usa backend/datalab/venv/bin/python.")

RAIZ = pathlib.Path(__file__).resolve().parents[3]
ENTRADA = (RAIZ / "backend/datalab/uploads/encuestasDemoscopia"
           / "tracking_demoscopia_campeche_2025_2026.csv")
ELECTORAL = RAIZ / "frontend/data/electoral"
SALIDA = ELECTORAL / "encuestas_2026.json"

CASA = "Demoscopia (con La Jornada Estado de México)"
MUESTRA = 1000
MOE_DECLARADA = 3.8          # % , al 95 % de confianza
CONFIANZA = 95
Z = 1.959964                 # cuantil normal para el 95 %
METODO = ("Llamadas telefónicas, muestreo aleatorio simple. "
          "Pregunta: «Si hoy fueran las elecciones para elegir gobernador(a), "
          "¿por cuál partido votaría?»")
FECHA_CORTE = "2026-07"

# Correspondencia explícita entre lo que mide la encuesta (6 fuerzas sueltas)
# y los bloques con los que se publicó 2024 (16 contendientes agrupados).
#
# El supuesto que hay detrás, y que hay que decir: la encuesta pregunta por
# PARTIDO, no por coalición. Sumar morena+pvem+pt asume que en 2027 vuelven a
# ir juntos, como en 2024. Si se rompen, este mapeo deja de valer y el modelo
# hay que recorrerlo.
MAPA_BLOQUES = {
    "SHH": ["morena", "pvem", "pt"],
    "MC": ["mc"],
    "PRI-PRD": ["pri"],
    "PAN": ["pan"],
    "OTROS": ["otros"],
}
NO_PARTIDO = "no_decide"

# Tamaños para la tabla de "cómo cambia el margen de error". El primero es el
# real de esta encuesta.
TAMANOS_MUESTRA = [400, 600, 1000, 1500, 2400, 4000, 9600]


def leer():
    if not ENTRADA.exists():
        raise SystemExit(f"Falta el tracking en {ENTRADA}")
    filas = list(csv.DictReader(ENTRADA.open(encoding="utf-8-sig")))
    if not filas:
        raise SystemExit("El tracking está vacío.")

    cols = [c for c in filas[0] if c != "mes"]
    faltan = [c for m in MAPA_BLOQUES.values() for c in m if c not in cols]
    if faltan:
        raise SystemExit(f"El tracking no trae las columnas {faltan}.")
    if NO_PARTIDO not in cols:
        raise SystemExit(f"El tracking no trae la columna '{NO_PARTIDO}'.")

    # Verificación independiente: cada mes tiene que sumar 100. Que el insumo
    # sea transcripción manual es justamente la razón para no confiar.
    malas = []
    for f in filas:
        s = sum(float(f[c]) for c in cols)
        if abs(s - 100.0) > 0.05:
            malas.append((f["mes"], round(s, 2)))
    if malas:
        raise SystemExit(
            f"Hay meses que no suman 100%: {malas}. La transcripción tiene un "
            f"error; no se publica una serie que no cuadra.")

    return filas, cols


def deff():
    """Efecto de diseño implícito en la MoE declarada.

    La casa declara ±3.8% con n=1,000. El muestreo aleatorio simple daría
    ±3.10% en p=0.5. La razón al cuadrado es el efecto de diseño: cuánto peor
    es esta muestra que una aleatoria simple del mismo tamaño. Se usa para que
    los errores por fuerza salgan con la escala que la propia casa declara, no
    con la teórica optimista.
    """
    moe_srs = Z * math.sqrt(0.25 / MUESTRA) * 100
    return (MOE_DECLARADA / moe_srs) ** 2


def error_estandar(p_pct, n=MUESTRA, con_deff=True):
    """Error estándar de una proporción, en puntos porcentuales."""
    p = p_pct / 100.0
    se = math.sqrt(max(p * (1 - p), 0.0) / n) * 100
    return se * math.sqrt(deff()) if con_deff else se


def margen(p_pct, n=MUESTRA, con_deff=True):
    return Z * error_estandar(p_pct, n, con_deff)


def descomponer(serie, media):
    """Separa el movimiento real del ruido de muestreo.

        var_observada = var_real + var_muestreo

    Si la observada no supera a la de muestreo, la serie es indistinguible de
    una línea plana: se devuelve 0, no un número pequeño que aparente señal.
    """
    var_obs = statistics.variance(serie)
    var_mue = error_estandar(media) ** 2
    var_real = var_obs - var_mue
    return {
        "sd_observada": round(math.sqrt(var_obs), 2),
        "sd_muestreo": round(math.sqrt(var_mue), 2),
        "sd_real": round(math.sqrt(var_real), 2) if var_real > 0 else 0.0,
        "hay_senal": bool(var_real > 0 and math.sqrt(var_real) > 0.5),
    }


def voto_efectivo(filas):
    """Reparto entre fuerzas, excluyendo al indeciso. CÁLCULO, no dato."""
    salida = []
    for f in filas:
        bl = {b: sum(float(f[c]) for c in cs) for b, cs in MAPA_BLOQUES.items()}
        total = sum(bl.values())
        salida.append({
            "mes": f["mes"],
            "bruto": bl,
            "efectivo": {b: round(v / total * 100, 2) for b, v in bl.items()},
            "no_decide": float(f[NO_PARTIDO]),
        })
    return salida


def volatilidad(efectivo):
    """Las tres medidas de cuánto se mueve el líder, calculadas del dato.

    Ninguna es "la" respuesta: son tres formas de preguntar lo mismo con
    horizontes distintos. Que converjan es lo que da confianza en el rango.
    """
    bloques = list(MAPA_BLOQUES)
    series = {b: [e["efectivo"][b] for e in efectivo] for b in bloques}
    lider = max(bloques, key=lambda b: series[b][-1])
    v = series[lider]

    # 1. Deriva observada: primeros tres meses contra últimos tres. Es una
    #    medida directa de cuánto se movió en 18 meses, y es robusta a que la
    #    serie esté suavizada.
    deriva = abs(statistics.mean(v[-3:]) - statistics.mean(v[:3]))

    # 2. Caminata aleatoria hasta la jornada. σ del cambio mensual escalado
    #    por la raíz del horizonte. OJO: supone pasos independientes, y el σ
    #    del cambio observado (1.55) es MENOR que el que daría el puro
    #    muestreo, lo que sugiere que la serie viene suavizada. Se publica
    #    como referencia, no como la estimación principal.
    pasos = [v[i + 1] - v[i] for i in range(len(v) - 1)]
    sd_paso = statistics.stdev(pasos)
    meses_a_jornada = 11
    caminata = sd_paso * math.sqrt(meses_a_jornada)

    # 3. Distancia entre la última elección y la encuesta de hoy: cuánto se
    #    movió el reparto entre 2024 y 2026, sobre todos los bloques.
    return {
        "bloque_lider": lider,
        "deriva_18_meses_pp": round(deriva, 2),
        "sd_cambio_mensual_pp": round(sd_paso, 2),
        "caminata_aleatoria_11_meses_pp": round(caminata, 2),
        "meses_a_la_jornada": meses_a_jornada,
        "advertencia_caminata":
            "σ del cambio mensual observado es menor que el que produciría el "
            "solo error de muestreo entre dos muestras independientes, lo que "
            "sugiere que la serie publicada viene suavizada. Por eso la "
            "caminata aleatoria se reporta como referencia y la estimación "
            "principal es la deriva observada.",
    }


def distancia_a_2024(efectivo):
    """Cuánto cambió el reparto entre la elección de 2024 y la encuesta."""
    ruta = ELECTORAL / "resultados_municipio_2024.json"
    if not ruta.exists():
        return None
    m = json.loads(ruta.read_text())
    bl, val = {}, 0
    for x in m["municipios"].values():
        for k, v in x["bloques"].items():
            bl[k] = bl.get(k, 0) + v
        val += x["validos"]
    p24 = {
        "SHH": bl.get("SHH", 0), "MC": bl.get("MC", 0),
        "PRI-PRD": bl.get("PRI-PRD", 0), "PAN": bl.get("PAN", 0),
        "OTROS": sum(bl.get(k, 0) for k in ("CL", "EDC", "PES", "MLC")),
    }
    ult = {b: statistics.mean([e["efectivo"][b] for e in efectivo[-3:]])
           for b in MAPA_BLOQUES}
    dif = {b: round(ult[b] - p24[b] / val * 100, 2) for b in MAPA_BLOQUES}
    rms = math.sqrt(statistics.mean([d ** 2 for d in dif.values()]))
    return {
        "pct_2024": {b: round(p24[b] / val * 100, 2) for b in MAPA_BLOQUES},
        "pct_encuesta_ultimos_3m": {b: round(v, 2) for b, v in ult.items()},
        "diferencia_pp": dif,
        "rms_pp": round(rms, 2),
        "nota": "El resultado de 2024 es de DIPUTACIONES LOCALES y la encuesta "
                "pregunta por GUBERNATURA. Parte de la diferencia es cambio de "
                "opinión y parte es que son elecciones distintas.",
    }


def sigma_recomendada(vol, dist):
    """El σ que sustituye al supuesto, y de dónde sale.

    Se toma el promedio de las tres estimaciones reales disponibles. No es una
    media ponderada sofisticada: es el centro de tres números que ya de por sí
    convergen (3.5, 4.7, 5.1). Si divergieran, promediarlos sería esconder el
    desacuerdo — por eso se publican los tres.
    """
    est = {
        "deriva_18_meses": vol["deriva_18_meses_pp"],
        "caminata_11_meses": vol["caminata_aleatoria_11_meses_pp"],
    }
    if dist:
        est["distancia_2024_a_2026"] = dist["rms_pp"]
    valores = list(est.values())
    return {
        "estimaciones": est,
        "minimo": round(min(valores), 2),
        "maximo": round(max(valores), 2),
        "recomendado_pp": round(statistics.mean(valores), 1),
        "criterio": "Promedio de las estimaciones independientes disponibles. "
                    "Las tres se publican: si divergieran, el promedio "
                    "escondería el desacuerdo.",
        "sustituye_a": "SIGMA_LIDER = 8.0, que era un supuesto anclado en el "
                       "swing 2021→2024 (rms 13.08 pp, n=1).",
    }


def construir():
    filas, cols = leer()
    efectivo = voto_efectivo(filas)
    partidos = [c for c in cols if c != NO_PARTIDO]

    fuerzas = {}
    for c in cols:
        serie = [float(f[c]) for f in filas]
        media = statistics.mean(serie)
        fuerzas[c] = dict(
            descomponer(serie, media),
            media=round(media, 2),
            minimo=min(serie), maximo=max(serie),
            deriva_18m=round(statistics.mean(serie[-3:])
                             - statistics.mean(serie[:3]), 2),
            margen_error_pp=round(margen(media), 2),
            es_partido=c != NO_PARTIDO,
        )

    vol = volatilidad(efectivo)
    dist = distancia_a_2024(efectivo)
    return filas, cols, partidos, fuerzas, efectivo, vol, dist


def verificar(filas, fuerzas, efectivo):
    for e in efectivo:
        s = sum(e["efectivo"].values())
        if abs(s - 100.0) > 0.1:
            raise SystemExit(f"{e['mes']}: el voto efectivo suma {s:.2f}%.")

    for c, f in fuerzas.items():
        if f["sd_real"] > f["sd_observada"] + 1e-9:
            raise SystemExit(
                f"{c}: la sd real ({f['sd_real']}) no puede superar a la "
                f"observada ({f['sd_observada']}).")
        if not (f["minimo"] <= f["media"] <= f["maximo"]):
            raise SystemExit(f"{c}: la media queda fuera del rango de la serie.")

    # El margen de error tiene que encogerse al crecer la muestra: si no, la
    # fórmula está mal escrita.
    m = [margen(40, n) for n in TAMANOS_MUESTRA]
    if any(m[i] <= m[i + 1] for i in range(len(m) - 1)):
        raise SystemExit("El margen de error no decrece con el tamaño de muestra.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--autocomprobar", action="store_true")
    args = ap.parse_args()
    if args.autocomprobar:
        return autocomprobar()

    filas, cols, partidos, fuerzas, efectivo, vol, dist = construir()
    verificar(filas, fuerzas, efectivo)

    print(f"Tracking Demoscopia · {len(filas)} meses · {len(partidos)} fuerzas")
    print(f"  efecto de diseño implícito en la MoE declarada: {deff():.2f}")
    print("  fuerza      sd_obs  sd_muestreo  sd_real  señal")
    for c in cols:
        f = fuerzas[c]
        print(f"  {c:10} {f['sd_observada']:6.2f}  {f['sd_muestreo']:11.2f}  "
              f"{f['sd_real']:7.2f}  {'sí' if f['hay_senal'] else 'no — ruido'}")

    sig = sigma_recomendada(vol, dist)
    print(f"  líder: {vol['bloque_lider']} · deriva 18m "
          f"{vol['deriva_18_meses_pp']} pp · caminata 11m "
          f"{vol['caminata_aleatoria_11_meses_pp']} pp"
          + (f" · distancia a 2024 {dist['rms_pp']} pp" if dist else ""))
    print(f"  σ recomendada: {sig['recomendado_pp']} pp "
          f"(rango {sig['minimo']}–{sig['maximo']})")

    escala = [{"n": n,
               "margen_pp": round(margen(50, n), 2),
               "margen_lider_pp": round(margen(48, n), 2)}
              for n in TAMANOS_MUESTRA]

    SALIDA.write_text(json.dumps({
        "metadata": {
            "procedencia": "dato_transcrito",
            "casa": CASA,
            "muestra": MUESTRA,
            "metodo": METODO,
            "margen_error_declarado_pp": MOE_DECLARADA,
            "confianza_pct": CONFIANZA,
            "efecto_diseno_implicito": round(deff(), 2),
            "fecha_corte": FECHA_CORTE,
            "periodo": f"{filas[0]['mes']} a {filas[-1]['mes']}",
            "meses": len(filas),
            "advertencia_procedencia":
                "TRANSCRIPCIÓN MANUAL desde la interfaz de tracking de la casa "
                "encuestadora, no una descarga oficial de su base de datos. "
                "Verificada aritméticamente (los 19 meses suman 100.0%), pero "
                "un error de lectura que respete la suma no lo detecta esa "
                "verificación. No se publica como dato de fuente.",
            "advertencia_muestreo":
                "Cada mes es una muestra distinta de 1,000 personas. Parte del "
                "movimiento entre meses es error de muestreo, no cambio de "
                "opinión: para el líder, la desviación observada es MENOR que "
                "el error esperado, o sea indistinguible de una serie plana.",
            "mapa_bloques": MAPA_BLOQUES,
            "supuesto_coalicion":
                "La encuesta pregunta por PARTIDO. Agrupar morena+pvem+pt en "
                "SHH asume que repiten coalición en 2027, como en 2024. Si se "
                "rompen, este mapeo deja de valer.",
            "trato_indecisos":
                "`no_decide` no es una fuerza y no se reparte entre partidos. "
                "Se excluye del denominador para obtener VOTO EFECTIVO, que es "
                "lo comparable con un resultado electoral. Es CÁLCULO.",
            "generado_por": "backend/datalab/pipeline/build_encuestas.py",
        },
        "serie": [dict(f, **{c: float(f[c]) for c in cols}) for f in filas],
        "fuerzas": fuerzas,
        "voto_efectivo": efectivo,
        "volatilidad": vol,
        "distancia_a_2024": dist,
        "sigma_recomendada": sig,
        "margen_por_tamano_muestra": {
            "que_es": "Cómo cambia el margen de error al 95% según el tamaño "
                      "de la muestra. El margen va como 1/√n: para partirlo a "
                      "la mitad hay que cuadruplicar la muestra.",
            "escala": escala,
        },
    }, ensure_ascii=False), encoding="utf-8")
    print(f"Listo. {SALIDA.relative_to(RAIZ)}")


def autocomprobar():
    filas, cols, partidos, fuerzas, efectivo, vol, dist = construir()
    verificar(filas, fuerzas, efectivo)

    # El margen de error va como 1/√n: cuadruplicar la muestra lo parte a la
    # mitad. Es la propiedad que la tabla de tamaños tiene que respetar.
    assert abs(margen(50, 4000) - margen(50, 1000) / 2) < 1e-9

    # La MoE declarada tiene que reproducirse en p=0.5 con n=1,000.
    assert abs(margen(50, MUESTRA) - MOE_DECLARADA) < 0.05, margen(50, MUESTRA)

    # Una serie plana no puede producir señal.
    plana = descomponer([40.0] * 19, 40.0)
    assert plana["sd_real"] == 0.0 and not plana["hay_senal"]

    # Una serie con movimiento muy por encima del ruido sí.
    fuerte = descomponer([30.0, 40.0] * 9 + [30.0], 35.0)
    assert fuerte["hay_senal"], fuerte

    # El voto efectivo redistribuye al indeciso: sube a todos.
    for e in efectivo:
        assert all(e["efectivo"][b] >= e["bruto"][b] - 1e-9 for b in e["bruto"])

    # Morena es el caso que motivó todo esto: su serie es ruido.
    assert fuerzas["morena"]["sd_real"] == 0.0, fuerzas["morena"]

    print(f"OK · {len(filas)} meses · σ recomendada "
          f"{sigma_recomendada(vol, dist)['recomendado_pp']} pp · "
          f"{sum(1 for f in fuerzas.values() if f['hay_senal'])} fuerzas con señal")


if __name__ == "__main__":
    main()
