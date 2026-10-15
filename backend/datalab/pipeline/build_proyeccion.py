#!/usr/bin/env python3
"""Proyección 2027 por simulación de Monte Carlo — sólo insumos electorales.

    backend/datalab/venv/bin/python backend/datalab/pipeline/build_proyeccion.py
    backend/datalab/venv/bin/python backend/datalab/pipeline/build_proyeccion.py --autocomprobar

Cuarto pipeline. Sustituye los rangos fijos escritos a mano en
contexto_campeche.json por una simulación reproducible.

Salida: frontend/data/electoral/proyeccion_2027.json

QUÉ INSUMOS HAY, DESPUÉS DE LA FASE 4
─────────────────────────────────────
  SÍ  Resultado 2024 por bloque, de los cómputos del IEEC. Es la BASE.
  SÍ  Resultado 2021 de gubernatura, capturado del cómputo estatal.
  SÍ  Participación 2024 (62.44%), calculada del propio cómputo.
  SÍ  Tracking de Demoscopia, 19 meses (ene-2025 a jul-2026), 8 categorías.
      Lo procesa build_encuestas.py. De ahí sale la DISPERSIÓN.
  NO  Participación de 2021. Sigue sin capturarse.
  NO  Pares históricos encuesta-resultado para Campeche, que es lo que
      permitiría estimar el error encuesta→voto. Sin eso, la dispersión
      cubre la deriva de la intención pero no ese sesgo.

DE DÓNDE SALE CADA MITAD DEL MODELO
───────────────────────────────────
La MEDIA es el resultado real de 2024: dato de cómputo.

La DISPERSIÓN ya no es un supuesto. Antes de la Fase 4 estaba anclada en la
única transición observada (2021→2024, rms 13.08 pp, n=1), y con n=1 no se
estima una varianza. Ahora sale del tracking, con tres métodos independientes
que convergen:

    deriva del líder en 18 meses          4.70 pp
    caminata aleatoria a 11 meses         5.15 pp
    distancia entre 2024 y la encuesta    3.52 pp
    ────────────────────────────────────────────
    σ recomendada (promedio)               4.5 pp

Que tres formas distintas de preguntar lo mismo caigan en 3.5-5.2 es lo que
da confianza en el rango. Si divergieran, promediarlas escondería el
desacuerdo — por eso las tres se publican.

El BARRIDO DE SENSIBILIDAD se conserva. El σ ya viene del dato, pero tiene
incertidumbre propia, y la encuesta es transcripción manual, no descarga
oficial. Si la conclusión cambia mucho entre escenarios, el modelo está
diciendo "no sé" y eso tiene que verse.

Sigue en pie el confusor de 2021 vs 2024: uno fue GUBERNATURA y otro
DIPUTACIONES LOCALES. Con dos observaciones no se separan.

LO QUE NO SE MODELA, Y POR QUÉ
──────────────────────────────
La participación NO entra en la simulación. El modelo proyecta REPARTO del
voto (porcentajes que suman 100), y la participación no cambia un reparto:
cambia cuánta gente lo emite. Meterla como variable aleatoria produciría
números que se mueven sin afectar quién gana — teatro estadístico. Se publica
como contexto, no como entrada del modelo.
"""

import argparse
import json
import pathlib
import sys

try:
    import numpy as np
except ImportError:
    sys.exit("Falta numpy. Usa backend/datalab/venv/bin/python.")

RAIZ = pathlib.Path(__file__).resolve().parents[3]
ELECTORAL = RAIZ / "frontend/data/electoral"
CONTEXTO = RAIZ / "frontend/data/contexto_campeche.json"
SALIDA = ELECTORAL / "proyeccion_2027.json"

CARGO = "Gubernatura"
FECHA_JORNADA = "2027-06-06"
FECHA_CORTE = "2026-08"

# Semilla fija. Una proyección que cambia en cada corrida no es auditable:
# nadie podría reproducir el número que se publicó ni discutirlo.
SEMILLA = 20270606

# 100k basta y sobra: el error de Montecarlo sobre una probabilidad va como
# 1/sqrt(N), así que con 100k la probabilidad de victoria tiene un error
# estándar de ~0.16 pp. Subir a 1M lo bajaría a 0.05 pp — precisión irrelevante
# frente a la incertidumbre real del supuesto de dispersión.
ITERACIONES = 100_000

# Desde la Fase 4 esto ya NO es un supuesto: sale de la serie de tracking de
# Demoscopia, que build_encuestas.py convierte en tres estimaciones
# independientes de cuánto se mueve el líder (deriva de 18 meses, caminata
# aleatoria al horizonte, y distancia entre 2024 y la encuesta de hoy).
# Se lee del archivo; este valor sólo se usa si el archivo no está.
SIGMA_FALLBACK = 8.0

# El barrido publica el mismo modelo con estos σ. No son escenarios políticos:
# son la misma pregunta con distinto grado de confianza en la estabilidad.
BARRIDO = [2.5, 3.5, 4.5, 6.0, 8.0, 11.0]

# Bloques con presencia real. El resto se agrupa: un bloque de 0.45% no
# cambia quién gana y sí ensucia la lectura.
UMBRAL_BLOQUE = 1.0


def sigma_de_encuestas():
    """σ calculado del tracking, o el de respaldo si no hay encuestas.

    Antes de la Fase 4 este número era un supuesto anclado en una sola
    transición observada (n=1). Ahora sale de 19 meses de serie real. Que
    venga de un archivo y no de una constante es deliberado: cuando llegue
    más tracking, el σ se actualiza al correr el pipeline de encuestas, sin
    tocar este archivo.
    """
    ruta = ELECTORAL / "encuestas_2026.json"
    if not ruta.exists():
        return SIGMA_FALLBACK, {
            "origen": "supuesto",
            "nota": "No hay archivo de encuestas; se usa el valor de respaldo.",
        }
    enc = json.loads(ruta.read_text())
    sig = enc["sigma_recomendada"]
    return sig["recomendado_pp"], {
        "origen": "calculado del tracking",
        "casa": enc["metadata"]["casa"],
        "periodo": enc["metadata"]["periodo"],
        "procedencia_insumo": enc["metadata"]["procedencia"],
        "estimaciones": sig["estimaciones"],
        "rango": [sig["minimo"], sig["maximo"]],
        "criterio": sig["criterio"],
        "sustituye_a": sig["sustituye_a"],
    }


def base_2024():
    """Reparto real por bloque en 2024, en fracciones que suman 1."""
    m = json.loads((ELECTORAL / "resultados_municipio_2024.json").read_text())
    bloques, validos = {}, 0
    for x in m["municipios"].values():
        for b, v in x["bloques"].items():
            bloques[b] = bloques.get(b, 0) + v
        validos += x["validos"]

    grandes = {b: v for b, v in bloques.items() if v / validos * 100 >= UMBRAL_BLOQUE}
    otros = sum(v for b, v in bloques.items() if b not in grandes)
    if otros:
        grandes["OTROS"] = otros

    total = sum(grandes.values())
    if abs(total - validos) > 0:
        raise SystemExit(
            f"La suma de bloques ({total:,}) no da los votos válidos "
            f"({validos:,}). No se proyecta sobre una base que no cuadra.")

    orden = sorted(grandes.items(), key=lambda kv: -kv[1])
    return ([b for b, _ in orden],
            np.array([v / total for _, v in orden]),
            m["metadata"])


def swing_observado():
    """El único cambio observado, 2021 -> 2024. Devuelve (detalle, rms)."""
    ctx = json.loads(CONTEXTO.read_text())
    p21 = {r["bloque"]: r["pct"] for r in ctx["historico"]["procesos"][0]["resultados"]}
    nombres, base, _ = base_2024()
    p24 = {b: base[i] * 100 for i, b in enumerate(nombres)}

    detalle = {}
    for b, v21 in p21.items():
        detalle[b] = {"pct_2021": v21, "pct_2024": round(p24.get(b, 0.0), 2),
                      "swing_pp": round(p24.get(b, 0.0) - v21, 2)}
    rms = float(np.sqrt(np.mean([d["swing_pp"] ** 2 for d in detalle.values()])))
    return detalle, round(rms, 2)


def concentracion(base, sigma_pp):
    """Traduce 'σ del líder en puntos porcentuales' al parámetro de Dirichlet.

    La Dirichlet es la distribución natural del reparto del voto: sus muestras
    suman 1 por construcción, así que nunca produce un escenario donde los
    porcentajes den 103%. Perturbar cada bloque con una normal y renormalizar
    después parece equivalente y no lo es: deforma las colas y correlaciona
    los errores de una manera que nadie eligió.

    Para Dirichlet(κ·p), la varianza de cada componente es
        Var(pᵢ) = pᵢ(1-pᵢ) / (κ+1)
    Se despeja κ para que el bloque más grande tenga la σ pedida.
    """
    p = float(base[0])
    var = (sigma_pp / 100.0) ** 2
    if var <= 0:
        raise SystemExit("SIGMA_LIDER tiene que ser mayor que cero.")
    return p * (1 - p) / var - 1


def simular(nombres, base, sigma_pp, iteraciones=ITERACIONES, semilla=SEMILLA):
    """Monte Carlo del reparto de 2027. Devuelve el resumen por bloque."""
    kappa = concentracion(base, sigma_pp)
    if kappa <= 0:
        raise SystemExit(
            f"σ={sigma_pp} pp es demasiado grande para un reparto con líder en "
            f"{base[0]*100:.1f}%: la Dirichlet no admite esa dispersión.")

    rng = np.random.default_rng(semilla)
    muestras = rng.dirichlet(kappa * base, iteraciones) * 100.0

    # El ganador de cada iteración: el índice del máximo de esa fila.
    ganador = muestras.argmax(axis=1)

    fuerzas = []
    for i, b in enumerate(nombres):
        col = muestras[:, i]
        fuerzas.append({
            "bloque": b,
            "base_2024": round(float(base[i] * 100), 2),
            "media": round(float(col.mean()), 2),
            "desviacion": round(float(col.std(ddof=1)), 2),
            # Percentiles: la forma honesta de publicar una simulación. El
            # intervalo del 90% (P5-P95) es el que se enseña en pantalla.
            "p5": round(float(np.percentile(col, 5)), 2),
            "p50": round(float(np.percentile(col, 50)), 2),
            "p95": round(float(np.percentile(col, 95)), 2),
            # IC95 de la media, que es otra cosa que el intervalo del reparto:
            # mide cuánto le falta a la simulación por converger, no cuánta
            # incertidumbre hay en la elección.
            "ic95_media": [
                round(float(np.percentile(col, 2.5)), 2),
                round(float(np.percentile(col, 97.5)), 2),
            ],
            "prob_victoria": round(float((ganador == i).mean() * 100), 1),
        })

    return {
        "iteraciones": iteraciones,
        "semilla": semilla,
        "sigma_lider_pp": sigma_pp,
        "kappa_dirichlet": round(kappa, 2),
        # Error estándar de Montecarlo sobre una probabilidad: cuánto de la
        # cifra publicada es ruido del propio muestreo.
        "error_montecarlo_pp": round(float(100 * 0.5 / np.sqrt(iteraciones)), 3),
        "fuerzas": fuerzas,
    }


def verificar(sim, nombres):
    """Nada se publica sin que la simulación sea internamente consistente."""
    f = sim["fuerzas"]
    if len(f) != len(nombres):
        raise SystemExit("La simulación no devolvió una fila por bloque.")

    medias = sum(x["media"] for x in f)
    if abs(medias - 100.0) > 0.5:
        raise SystemExit(
            f"Las medias del reparto suman {medias:.2f}% y deberían dar 100. "
            f"La Dirichlet no se está muestreando bien.")

    probs = sum(x["prob_victoria"] for x in f)
    if abs(probs - 100.0) > 0.5:
        raise SystemExit(
            f"Las probabilidades de victoria suman {probs:.1f}% y deberían dar "
            f"100: en cada iteración gana exactamente un bloque.")

    for x in f:
        if not (x["p5"] <= x["p50"] <= x["p95"]):
            raise SystemExit(f"{x['bloque']}: los percentiles no están ordenados.")
        if x["desviacion"] <= 0:
            raise SystemExit(f"{x['bloque']}: desviación cero, no hay simulación.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--autocomprobar", action="store_true")
    args = ap.parse_args()
    if args.autocomprobar:
        return autocomprobar()

    print("Base electoral 2024…")
    nombres, base, meta = base_2024()
    print("  " + " · ".join(f"{b} {v*100:.2f}%" for b, v in zip(nombres, base)))

    detalle, rms = swing_observado()
    print(f"Swing observado 2021→2024: rms {rms} pp sobre {len(detalle)} bloques (n=1)")

    sigma, origen_sigma = sigma_de_encuestas()
    print(f"σ del líder: {sigma} pp ({origen_sigma['origen']})")
    print(f"Monte Carlo · {ITERACIONES:,} iteraciones · σ líder {sigma} pp…")
    sim = simular(nombres, base, sigma)
    verificar(sim, nombres)
    for x in sim["fuerzas"]:
        print(f"  {x['bloque']:8} {x['media']:5.2f}% "
              f"[{x['p5']:5.2f}–{x['p95']:5.2f}]  victoria {x['prob_victoria']:5.1f}%")

    print("Barrido de sensibilidad…")
    barrido = []
    for s in BARRIDO:
        b = simular(nombres, base, s)
        verificar(b, nombres)
        barrido.append({
            "sigma_lider_pp": s,
            "prob_victoria": {x["bloque"]: x["prob_victoria"] for x in b["fuerzas"]},
            "p5_p95_lider": [b["fuerzas"][0]["p5"], b["fuerzas"][0]["p95"]],
        })
        print(f"  σ={s:4.1f} pp → " + " · ".join(
            f"{x['bloque']} {x['prob_victoria']:.1f}%" for x in b["fuerzas"][:3]))

    SALIDA.write_text(json.dumps({
        "metadata": {
            "procedencia": "estimacion",
            "metodo": f"Simulación de Monte Carlo, {ITERACIONES:,} iteraciones",
            "cargo": CARGO,
            "fecha_jornada": FECHA_JORNADA,
            "fecha_corte": FECHA_CORTE,
            "fuente_base": meta["fuente"],
            "distribucion": "Dirichlet sobre el reparto de 2024. Sus muestras "
                            "suman 100% por construcción, así que ninguna "
                            "iteración produce un reparto imposible.",
            # Los insumos se DERIVAN de lo que el pipeline hizo de verdad, no
            # se escriben a mano. La versión anterior estaba escrita a mano y se
            # quedó vieja: seguía declarando "no hay ningún dato de encuesta en
            # el repositorio" mientras el σ de esa misma corrida salía del
            # tracking de Demoscopia. La página que consumiera esa metadata
            # habría publicado que no hay encuestas usando su resultado.
            "insumos_disponibles": dict(
                {
                    "resultado_2024_por_bloque": "DATO, cómputos del IEEC",
                    "resultado_2021_gubernatura": "DATO, cómputo estatal capturado",
                    "participacion_2024": "CÁLCULO sobre el cómputo",
                },
                **({
                    "tracking_de_encuestas":
                        f"{origen_sigma.get('procedencia_insumo', 'dato')}, "
                        f"{origen_sigma.get('casa', '')} "
                        f"({origen_sigma.get('periodo', '')}). De aquí sale σ.",
                } if origen_sigma["origen"] != "supuesto" else {})
            ),
            "insumos_ausentes": dict(
                {"participacion_2021": "No está capturada."},
                **({
                    "encuestas": "No hay archivo de tracking; σ es el de respaldo.",
                } if origen_sigma["origen"] == "supuesto" else {})
            ),
            "advertencia_dispersion":
                "La MEDIA de esta simulación es el resultado real de 2024. La "
                "DISPERSIÓN sale de la serie de tracking de Demoscopia (19 "
                "meses), no de un supuesto: se calcula con tres métodos "
                "independientes que convergen. Antes de la Fase 4 era un "
                "supuesto anclado en n=1. El barrido de sensibilidad se "
                "conserva porque el σ sigue teniendo incertidumbre propia y "
                "porque la encuesta es transcripción manual, no descarga "
                "oficial.",
            "confusor_2021_2024":
                "2021 fue gubernatura y 2024 diputaciones locales. Parte del "
                "swing es cambio político y parte es que son elecciones "
                "distintas. Con dos observaciones no se pueden separar.",
            "no_modelado":
                "La participación no entra al modelo. Éste proyecta el REPARTO "
                "del voto; la participación cambia cuánta gente vota, no cómo "
                "se reparte. Incluirla movería números sin afectar quién gana.",
            "swing_observado": detalle,
            "swing_rms_pp": rms,
            "origen_sigma": origen_sigma,
            "generado_por": "backend/datalab/pipeline/build_proyeccion.py",
        },
        "simulacion": sim,
        "sensibilidad": barrido,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"Listo. {SALIDA.relative_to(RAIZ)}")


def autocomprobar():
    """Comprueba las propiedades que tiene que cumplir cualquier simulación."""
    nombres, base, _ = base_2024()

    # La base es un reparto: suma 1.
    assert abs(base.sum() - 1.0) < 1e-9, base.sum()

    sim = simular(nombres, base, SIGMA_FALLBACK, iteraciones=20_000)
    verificar(sim, nombres)

    # Las medias tienen que quedarse pegadas a la base: la Dirichlet es
    # insesgada, así que la simulación no debe desplazar el centro.
    for x in sim["fuerzas"]:
        assert abs(x["media"] - x["base_2024"]) < 0.6, x

    # La σ pedida tiene que aparecer en la desviación del líder.
    lider = sim["fuerzas"][0]
    assert abs(lider["desviacion"] - SIGMA_FALLBACK) < 0.6, lider

    # Más dispersión = más incertidumbre = el favorito baja su probabilidad.
    poco = simular(nombres, base, 4.0, iteraciones=20_000)
    mucho = simular(nombres, base, 12.0, iteraciones=20_000)
    assert poco["fuerzas"][0]["prob_victoria"] >= mucho["fuerzas"][0]["prob_victoria"], (
        "más dispersión debería reducir la ventaja del favorito")

    # Y el intervalo tiene que ensancharse con σ.
    ancho = lambda s: s["fuerzas"][0]["p95"] - s["fuerzas"][0]["p5"]
    assert ancho(poco) < ancho(mucho), "el intervalo no reacciona a σ"

    # Reproducibilidad: misma semilla, mismo resultado.
    a = simular(nombres, base, SIGMA_FALLBACK, iteraciones=5_000)
    b = simular(nombres, base, SIGMA_FALLBACK, iteraciones=5_000)
    assert a["fuerzas"] == b["fuerzas"], "la simulación no es reproducible"

    print(f"OK · {len(nombres)} bloques · medias suman "
          f"{sum(x['media'] for x in sim['fuerzas']):.2f}% · "
          f"probabilidades suman "
          f"{sum(x['prob_victoria'] for x in sim['fuerzas']):.1f}%")


if __name__ == "__main__":
    main()
