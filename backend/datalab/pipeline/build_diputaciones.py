#!/usr/bin/env python3
"""Integración del Congreso de Campeche 2024-2027 — LXV Legislatura.

    backend/datalab/venv/bin/python backend/datalab/pipeline/build_diputaciones.py
    backend/datalab/venv/bin/python backend/datalab/pipeline/build_diputaciones.py --autocomprobar

Sexto pipeline. Salida: frontend/data/electoral/diputaciones_2024.json

QUÉ CAMBIÓ RESPECTO A LA PRIMERA VERSIÓN
────────────────────────────────────────
La primera versión calculaba el reparto de RP con parámetros sin verificar y
lo publicaba como escenario. Ya no hace falta: se consiguieron los dos
documentos que faltaban, y el resultado de RP pasa a ser DATO OFICIAL.

  · Ley de Instituciones y Procedimientos Electorales del Estado de Campeche
    (última reforma Decreto 236, P.O. 1/jun/2023)
  · Acuerdo CG/116/2024 del Consejo General del IEEC, 45ª sesión
    extraordinaria del 9 de septiembre de 2024

El texto extraído de ambos se conserva en
backend/datalab/uploads/ieec_acuerdos/.

LO QUE LA LEY DICE Y EL CÓDIGO NO HACÍA
───────────────────────────────────────
El artículo 573 fija un paso previo que la primera versión se saltaba:

    "todo aquel Partido Político que obtenga por lo menos el tres por ciento
     del total de la Votación Válida Emitida tendrá derecho a que se le
     asigne UN Diputado por el principio de Representación Proporcional,
     independientemente de los triunfos de mayoría que hubiere obtenido.
     Realizada la distribución anterior, se procederá a asignar EL RESTO de
     las diputaciones conforme a la fórmula"

Es decir: primero una asignación DIRECTA de un escaño a cada partido sobre el
umbral, y sólo después el cociente natural sobre las que quedan. La primera
versión repartía las 14 por fórmula, lo que daba otro resultado.

Y el divisor del cociente son las diputaciones PENDIENTES, no las 14. El
acuerdo lo dice con todas sus letras: "esta cantidad se dividirá entre 8 que
es el número de diputaciones pendientes por asignar".

LAS DEFINICIONES, DEL ARTÍCULO 569
──────────────────────────────────
  Votación Válida Emitida (VVE)  total en urnas − nulos − no registradas.
                                 Es la base del umbral del 3%.
  Votación Estatal Emitida (VEE) VVE − votos de partidos bajo el 3% −
                                 independientes. Es la base del cociente.

POR QUÉ EL CÁLCULO PROPIO NO DA IGUAL QUE EL OFICIAL, Y ESTÁ BIEN
─────────────────────────────────────────────────────────────────
El acuerdo se emitió DESPUÉS de las sentencias del Tribunal Electoral del
Estado (TEEC/JIN/DIP/1, 2 y 5/2024), que ordenaron recuentos. Así que sus
cifras no son las de los archivos de cómputo que procesa build_electoral.py:

    Votación Válida Emitida oficial   419,632
    la que sale de nuestros archivos  416,950
    diferencia                          2,682   votos de los recuentos

Por eso este pipeline publica las DOS cosas y las compara:

  · `oficial`  — transcrito del acuerdo. Es el dato que vale.
  · `calculo`  — la misma fórmula aplicada a nuestros archivos, como
                 COMPROBACIÓN CRUZADA del algoritmo, no como resultado.

Si el reparto calculado coincide con el oficial pese a partir de cifras
distintas, es que la fórmula está bien implementada. Si no coincidiera, hay
que mirar el algoritmo antes que el dato.
"""


import argparse
import collections
import json
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[3]
ELECTORAL = RAIZ / "frontend/data/electoral"
SALIDA = ELECTORAL / "diputaciones_2024.json"

# ── Reglas del reparto — VERIFICADAS CONTRA LA LEY ─────────────────────────
REGLAS = {
    "verificado_contra_ley": True,
    "fuente": "Ley de Instituciones y Procedimientos Electorales del Estado de "
              "Campeche, última reforma Decreto 236, P.O. 1/jun/2023",
    # Art. 15: "veintiún diputaciones electas según el principio de Mayoría
    # Relativa ... y por catorce diputaciones que serán asignadas según el
    # principio de Representación Proporcional, mediante el sistema de listas
    # propuestas en una circunscripción plurinominal".
    "escanos_mr": 21,
    "escanos_rp": 14,
    "articulo_integracion": 15,
    # Art. 573: el umbral es sobre la VOTACIÓN VÁLIDA EMITIDA, y da derecho a
    # UNA diputación directa antes de aplicar la fórmula.
    "umbral_pct": 3.0,
    "umbral_base": "Votación Válida Emitida",
    "articulo_umbral": 573,
    "asignacion_directa": True,
    # Art. 570-572, 574: proporcionalidad pura = cociente natural + resto
    # mayor, sobre la Votación Estatal Emitida y las diputaciones PENDIENTES.
    "formula": "proporcionalidad pura: cociente natural + resto mayor",
    "cociente_base": "Votación Estatal Emitida",
    "cociente_divisor": "diputaciones pendientes tras la asignación directa",
    "articulos_formula": [570, 571, 572, 574],
    # Art. 575: tres límites.
    "limite_1_max_diputaciones": 21,
    "limite_2_sobrerrepresentacion_pp": 8.0,
    "limite_3_subrepresentacion_pp": 8.0,
    "articulos_limites": [575, 576, 577, 578],
}

# ── DATO OFICIAL — Acuerdo CG/116/2024 ─────────────────────────────────────
# Transcrito del acuerdo del Consejo General del IEEC, 45ª sesión
# extraordinaria del 9 de septiembre de 2024. Emitido tras las sentencias
# TEEC/JIN/DIP/1, 2 y 5/2024, que ordenaron recuentos: por eso sus cifras
# difieren de las de nuestros archivos de cómputo.
OFICIAL = {
    "acuerdo": "CG/116/2024",
    "sesion": "45ª extraordinaria, 9 de septiembre de 2024",
    "url": "https://www.ieec.org.mx/Documentacion/AcuerdosActas/2024/"
           "septiembre/45a_ext/CG_116_2024.pdf",
    "votacion_valida_emitida": 419632,
    "votacion_estatal_emitida": 397424,
    "cociente_natural": 49678,
    "diputaciones_pendientes_tras_directa": 8,
    # votos, y el reparto tal como lo publica el acuerdo
    "partidos": {
        "PAN":    {"votos": 24552,  "directa": 1, "cociente": 0, "resto": 1, "rp": 2, "mr": 0},
        "PRI":    {"votos": 49417,  "directa": 1, "cociente": 0, "resto": 1, "rp": 2, "mr": 1},
        "PRD":    {"votos": 3010,   "directa": 0, "cociente": 0, "resto": 0, "rp": 0, "mr": 0},
        "PT":     {"votos": 17347,  "directa": 1, "cociente": 0, "resto": 0, "rp": 1, "mr": 1},
        "PVEM":   {"votos": 14568,  "directa": 1, "cociente": 0, "resto": 0, "rp": 1, "mr": 1},
        "MC":     {"votos": 128402, "directa": 1, "cociente": 2, "resto": 1, "rp": 4, "mr": 6},
        "MORENA": {"votos": 163138, "directa": 1, "cociente": 3, "resto": 0, "rp": 4, "mr": 12},
        "PES":    {"votos": 3045,   "directa": 0, "cociente": 0, "resto": 0, "rp": 0, "mr": 0},
        "CL":     {"votos": 11154,  "directa": 0, "cociente": 0, "resto": 0, "rp": 0, "mr": 0},
        "EDC":    {"votos": 3115,   "directa": 0, "cociente": 0, "resto": 0, "rp": 0, "mr": 0},
        "MLC":    {"votos": 1884,   "directa": 0, "cociente": 0, "resto": 0, "rp": 0, "mr": 0},
    },
    "limites_aplicados": "ninguno",
    "limites_nota": "El acuerdo comprueba los tres límites del artículo 575 y "
                    "ninguno se rebasa. El más cercano es MORENA: 45.71% del "
                    "Congreso contra un tope de 49.05% (su 41.05% de VEE más "
                    "8 puntos).",
    "sentencias_previas": ["TEEC/JIN/DIP/1/2024", "TEEC/JIN/DIP/2/2024",
                           "TEEC/JIN/DIP/5/2024"],
}

REPARTO_COALICION = "partes iguales entre los partidos que integran la marca"


def cargar():
    mun = json.loads((ELECTORAL / "resultados_municipio_2024.json").read_text())
    sec = json.loads((ELECTORAL / "resultados_seccion_2024.json").read_text())
    return mun, sec


def escanos_mr(sec):
    """Ganador de cada distrito local, de los cómputos. Esto es DATO."""
    dist = collections.defaultdict(collections.Counter)
    validos = collections.Counter()
    for s, r in sec["secciones"].items():
        d = r.get("distrito_local")
        if d is None:
            continue
        for b, v in r["bloques"].items():
            dist[d][b] += v
        validos[d] += r["validos"]

    if len(dist) != REGLAS["escanos_mr"]:
        raise SystemExit(
            f"Se esperaban {REGLAS['escanos_mr']} distritos locales y los "
            f"cómputos traen {len(dist)}. No se reparte sobre una base que no "
            f"cuadra con el catálogo.")

    detalle, ganados = [], collections.Counter()
    for d in sorted(dist):
        orden = dist[d].most_common()
        primero = orden[0]
        segundo = orden[1] if len(orden) > 1 else ("", 0)
        ganados[primero[0]] += 1
        detalle.append({
            "distrito": d,
            "ganador": primero[0],
            "votos": primero[1],
            "pct": round(primero[1] / validos[d] * 100, 2),
            "segundo": segundo[0],
            "margen_pp": round((primero[1] - segundo[1]) / validos[d] * 100, 2),
        })
    return detalle, dict(ganados)


def votos_por_partido(mun):
    """Votación de cada partido, repartiendo las marcas de coalición.

    La ley reparte RP por partido; el voto por coalición se emitió con marca
    propia. Repartirlo en partes iguales es una CONVENCIÓN declarada, no lo
    que dice la ley: el convenio de coalición registrado puede fijar otra
    proporción, y ese documento no está aquí.
    """
    bruto = collections.Counter()
    validos = 0
    for x in mun["municipios"].values():
        for c, v in x["votos"].items():
            bruto[c] += v
        validos += x["validos"]

    simple = collections.Counter()
    for clave, v in bruto.items():
        partes = clave.split("-")
        if len(partes) == 1:
            simple[clave] += v
        else:
            # División entera y el residuo al primero, para que la suma cierre
            # exacta: repartir con float dejaría descuadres de centésimas que
            # después rompen la verificación.
            cada, resto = divmod(v, len(partes))
            for i, p in enumerate(partes):
                simple[p] += cada + (resto if i == 0 else 0)

    if sum(simple.values()) != validos:
        raise SystemExit(
            f"El reparto de coaliciones no conserva el total: "
            f"{sum(simple.values()):,} contra {validos:,} votos válidos.")
    return dict(simple), validos


def reparto_rp(votos, validos):
    """Procedimiento de los artículos 569-574, en su orden.

    El orden importa y es lo que la primera versión tenía mal: PRIMERO la
    asignación directa del artículo 573, y sólo DESPUÉS la fórmula sobre las
    diputaciones que quedan pendientes.
    """
    umbral = REGLAS["umbral_pct"]
    total_rp = REGLAS["escanos_rp"]

    # Art. 573: el umbral se mide sobre la VOTACIÓN VÁLIDA EMITIDA.
    con_derecho = {p: v for p, v in votos.items() if v / validos * 100 >= umbral}
    sin_derecho = {p: round(v / validos * 100, 2)
                   for p, v in votos.items() if p not in con_derecho}
    if not con_derecho:
        raise SystemExit(f"Ningún partido alcanza el umbral de {umbral}%.")

    # Art. 573: una diputación directa a cada uno, antes de cualquier fórmula.
    directa = {p: 1 for p in con_derecho}
    pendientes = total_rp - len(directa)
    if pendientes < 0:
        raise SystemExit(
            f"Hay {len(directa)} partidos sobre el umbral y sólo {total_rp} "
            f"diputaciones de RP: la asignación directa no cabe. Ese caso lo "
            f"tiene que resolver la ley, no este script.")

    # Art. 569 fr. III: la Votación Estatal Emitida deduce a los que no
    # alcanzaron el 3%. Es otra base que la del umbral.
    vee = sum(con_derecho.values())
    # Art. 571 + acuerdo CG/116/2024: el divisor son las PENDIENTES.
    cociente = vee / pendientes if pendientes else 0

    por_cociente, restos = {}, {}
    for p, v in con_derecho.items():
        entero = int(v // cociente) if cociente else 0
        por_cociente[p] = entero
        # Art. 574 fr. II: el resto es la votación NO UTILIZADA.
        restos[p] = v - entero * cociente

    faltan = pendientes - sum(por_cociente.values())
    orden = sorted(restos, key=lambda p: (-restos[p], -con_derecho[p]))
    por_resto = {p: 0 for p in con_derecho}
    for p in orden[:faltan]:
        por_resto[p] = 1

    asignados = {p: directa[p] + por_cociente[p] + por_resto[p]
                 for p in con_derecho}

    return {
        "umbral_pct": umbral,
        "umbral_base": REGLAS["umbral_base"],
        "escanos_rp": total_rp,
        "votacion_valida_emitida": validos,
        "votacion_estatal_emitida": vee,
        "asignacion_directa": directa,
        "diputaciones_pendientes": pendientes,
        "cociente_natural": round(cociente, 2),
        "con_derecho": sorted(con_derecho),
        "sin_derecho": sin_derecho,
        "por_cociente": por_cociente,
        "por_resto_mayor": por_resto,
        "asignados": asignados,
        "restos": {p: round(r, 2) for p, r in restos.items()},
    }


def limites(oficial):
    """Los tres límites del artículo 575, ahora computables.

    Antes se declaraba `computable: False` porque los 21 escaños de MR los
    ganaron BLOQUES de coalición y atribuirlos a partidos requería el convenio.
    El acuerdo CG/116/2024 ya hace esa atribución, así que la prueba se puede
    hacer — y se hace sobre el TOTAL de escaños, que es lo que dice la ley.
    """
    vee = oficial["votacion_estatal_emitida"]
    total_congreso = REGLAS["escanos_mr"] + REGLAS["escanos_rp"]
    tope = REGLAS["limite_2_sobrerrepresentacion_pp"]
    piso = REGLAS["limite_3_subrepresentacion_pp"]

    filas = []
    for p, d in oficial["partidos"].items():
        total = d["mr"] + d["rp"]
        if not total:
            continue
        pct_vee = d["votos"] / vee * 100
        pct_congreso = total / total_congreso * 100
        filas.append({
            "partido": p, "mr": d["mr"], "rp": d["rp"], "total": total,
            "pct_vee": round(pct_vee, 2),
            "pct_congreso": round(pct_congreso, 2),
            "tope_pct": round(pct_vee + tope, 2),
            "piso_pct": round(pct_vee - piso, 2),
            "excede_21": total > REGLAS["limite_1_max_diputaciones"],
            "excede_tope": pct_congreso > pct_vee + tope,
            "bajo_piso": pct_congreso < pct_vee - piso,
        })
    filas.sort(key=lambda f: -f["total"])
    return {
        "computable": True,
        "base": "Votación Estatal Emitida y total de escaños (MR + RP)",
        "detalle": filas,
        "rebasan_tope": [f["partido"] for f in filas if f["excede_tope"]],
        "bajo_piso": [f["partido"] for f in filas if f["bajo_piso"]],
        "exceden_21": [f["partido"] for f in filas if f["excede_21"]],
    }


def construir():
    mun, sec = cargar()
    detalle_mr, mr_bloque = escanos_mr(sec)
    votos, validos = votos_por_partido(mun)
    calc = reparto_rp(votos, validos)

    oficial_rp = {p: d["rp"] for p, d in OFICIAL["partidos"].items() if d["rp"]}
    oficial_mr = {p: d["mr"] for p, d in OFICIAL["partidos"].items() if d["mr"]}

    # COMPROBACIÓN CRUZADA: el algoritmo corre sobre nuestros archivos, que son
    # PREVIOS a las sentencias, así que las cifras de entrada no coinciden con
    # las del acuerdo. Lo que se compara es el REPARTO, no los votos: si sale
    # el mismo con datos distintos, la fórmula está bien implementada.
    coincide = calc["asignados"] == oficial_rp
    difs = {p: {"calculado": calc["asignados"].get(p, 0),
                "oficial": oficial_rp.get(p, 0)}
            for p in set(calc["asignados"]) | set(oficial_rp)
            if calc["asignados"].get(p, 0) != oficial_rp.get(p, 0)}

    # El MR por bloque que sale de los cómputos contra el MR por partido del
    # acuerdo: la coalición SHH se reparte entre MORENA, PT y PVEM.
    shh = sum(oficial_mr.get(p, 0) for p in ("MORENA", "PT", "PVEM"))
    mr_cruce = {
        "por_bloque_calculado": mr_bloque,
        "por_partido_oficial": oficial_mr,
        "shh_oficial_desglosado": shh,
        "coincide_shh": mr_bloque.get("SHH") == shh,
        "coincide_mc": mr_bloque.get("MC") == oficial_mr.get("MC"),
    }

    return {
        "oficial": dict(OFICIAL, rp_total=sum(oficial_rp.values()),
                        mr_total=sum(oficial_mr.values())),
        "calculo": calc,
        "comprobacion_cruzada": {
            "reparto_rp_coincide": coincide,
            "diferencias": difs,
            "vve_oficial": OFICIAL["votacion_valida_emitida"],
            "vve_calculada": validos,
            "diferencia_votos": OFICIAL["votacion_valida_emitida"] - validos,
            "por_que_difieren":
                "El acuerdo se emitió tras las sentencias TEEC/JIN/DIP/1, 2 y "
                "5/2024, que ordenaron recuentos. Nuestros archivos de cómputo "
                "son previos. Se compara el REPARTO, no los votos.",
            "mr": mr_cruce,
        },
        "mr_distritos": detalle_mr,
        "votos_por_partido_calculado": votos,
        "limites": limites(OFICIAL),
        "total_escanos": REGLAS["escanos_mr"] + REGLAS["escanos_rp"],
    }


def verificar(d):
    o, c = d["oficial"], d["calculo"]
    if o["rp_total"] != REGLAS["escanos_rp"]:
        raise SystemExit(f"El acuerdo suma {o['rp_total']} escaños de RP y "
                         f"la ley fija {REGLAS['escanos_rp']}.")
    if o["mr_total"] != REGLAS["escanos_mr"]:
        raise SystemExit(f"El acuerdo suma {o['mr_total']} escaños de MR y "
                         f"la ley fija {REGLAS['escanos_mr']}.")
    # La transcripción tiene que ser internamente consistente: directa +
    # cociente + resto = rp, para cada partido.
    for p, x in OFICIAL["partidos"].items():
        if x["directa"] + x["cociente"] + x["resto"] != x["rp"]:
            raise SystemExit(f"{p}: la transcripción no cuadra, "
                             f"{x['directa']}+{x['cociente']}+{x['resto']} "
                             f"≠ {x['rp']}.")
    # La VEE del acuerdo tiene que ser la suma de los que pasaron el umbral.
    suma = sum(x["votos"] for x in OFICIAL["partidos"].values()
               if x["votos"] / OFICIAL["votacion_valida_emitida"] * 100 >= 3.0)
    if suma != OFICIAL["votacion_estatal_emitida"]:
        raise SystemExit(f"La VEE transcrita ({OFICIAL['votacion_estatal_emitida']:,}) "
                         f"no es la suma de los partidos sobre el umbral ({suma:,}).")
    # Y el cociente tiene que ser esa VEE entre las pendientes.
    esperado = round(OFICIAL["votacion_estatal_emitida"]
                     / OFICIAL["diputaciones_pendientes_tras_directa"])
    if abs(esperado - OFICIAL["cociente_natural"]) > 1:
        raise SystemExit(f"El cociente transcrito ({OFICIAL['cociente_natural']:,}) "
                         f"no es VEE ÷ pendientes ({esperado:,}).")
    if sum(c["asignados"].values()) != REGLAS["escanos_rp"]:
        raise SystemExit("El cálculo propio no reparte las 14 diputaciones.")
    for p in c["sin_derecho"]:
        if c["asignados"].get(p):
            raise SystemExit(f"{p} está bajo el umbral y tiene escaños.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--autocomprobar", action="store_true")
    args = ap.parse_args()
    if args.autocomprobar:
        return autocomprobar()

    d = construir()
    verificar(d)
    o, c, x = d["oficial"], d["calculo"], d["comprobacion_cruzada"]

    print(f"DATO OFICIAL — Acuerdo {o['acuerdo']}, {o['sesion']}")
    print(f"  VVE {o['votacion_valida_emitida']:,} · VEE "
          f"{o['votacion_estatal_emitida']:,} · cociente "
          f"{o['cociente_natural']:,} sobre {o['diputaciones_pendientes_tras_directa']} pendientes")
    print("  partido    MR  RP  total   (directa+cociente+resto)")
    for p, v in sorted(OFICIAL["partidos"].items(),
                       key=lambda kv: -(kv[1]["mr"] + kv[1]["rp"])):
        if v["mr"] or v["rp"]:
            print(f"  {p:9} {v['mr']:3} {v['rp']:3} {v['mr']+v['rp']:5}"
                  f"     ({v['directa']}+{v['cociente']}+{v['resto']})")
    print(f"  límites del art. 575 aplicados: {o['limites_aplicados']}")

    print(f"\nCOMPROBACIÓN CRUZADA — la misma fórmula sobre nuestros archivos")
    print(f"  VVE oficial {x['vve_oficial']:,} vs calculada {x['vve_calculada']:,} "
          f"(dif {x['diferencia_votos']:+,} por los recuentos)")
    print(f"  reparto de RP coincide: {'SÍ' if x['reparto_rp_coincide'] else 'NO'}")
    if x["diferencias"]:
        print(f"  diferencias: {x['diferencias']}")
    print(f"  MR por bloque calculado: {x['mr']['por_bloque_calculado']}")
    print(f"  SHH calculado {x['mr']['por_bloque_calculado'].get('SHH')} vs "
          f"MORENA+PT+PVEM oficial {x['mr']['shh_oficial_desglosado']}: "
          f"{'coincide' if x['mr']['coincide_shh'] else 'NO COINCIDE'}")

    l = d["limites"]
    print(f"\nLÍMITES DEL ART. 575 (ahora computables)")
    print(f"  rebasan el tope de +8 pp: {l['rebasan_tope'] or 'ninguno'}")
    print(f"  por debajo del piso -8 pp: {l['bajo_piso'] or 'ninguno'}")

    SALIDA.write_text(json.dumps({
        "metadata": {
            "procedencia": "dato",
            "eleccion": "Diputaciones locales, Campeche 2024 — LXV Legislatura",
            "que_es": "Integración oficial del Congreso, transcrita del acuerdo "
                      "CG/116/2024 del IEEC, más la misma fórmula aplicada a "
                      "nuestros archivos como comprobación cruzada.",
            "fuente_oficial": f"IEEC — Acuerdo {OFICIAL['acuerdo']}, {OFICIAL['sesion']}",
            "url_acuerdo": OFICIAL["url"],
            "fuente_legal": REGLAS["fuente"],
            "advertencia_cifras":
                "Las cifras del acuerdo son POSTERIORES a las sentencias "
                "TEEC/JIN/DIP/1, 2 y 5/2024. Los archivos de cómputo que "
                "procesa build_electoral.py son previos, así que sus totales "
                "no coinciden. El dato que vale es el del acuerdo.",
            "reparto_coalicion_en_calculo": REPARTO_COALICION,
            "reglas": REGLAS,
            "fecha_corte": "2024-09",
            "generado_por": "backend/datalab/pipeline/build_diputaciones.py",
        },
        **d,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"\nListo. {SALIDA.relative_to(RAIZ)}")


def autocomprobar():
    d = construir()
    verificar(d)

    # La asignación directa es una por partido sobre el umbral, ni más ni menos.
    c = d["calculo"]
    assert all(v == 1 for v in c["asignacion_directa"].values())
    assert len(c["asignacion_directa"]) == len(c["con_derecho"])
    assert c["diputaciones_pendientes"] == REGLAS["escanos_rp"] - len(c["con_derecho"])

    # El cociente se calcula sobre las PENDIENTES, no sobre las 14: éste es el
    # error que tenía la primera versión.
    assert abs(c["cociente_natural"]
               - c["votacion_estatal_emitida"] / c["diputaciones_pendientes"]) < 0.01

    # Las tres vías suman el total, para cada partido y en conjunto.
    for p in c["con_derecho"]:
        assert (c["asignacion_directa"][p] + c["por_cociente"][p]
                + c["por_resto_mayor"][p]) == c["asignados"][p]
    assert sum(c["asignados"].values()) == REGLAS["escanos_rp"]

    # Nadie recibe más de uno por resto mayor.
    assert all(v <= 1 for v in c["por_resto_mayor"].values())

    # La transcripción del acuerdo reproduce el cociente que el propio acuerdo
    # publica: es la comprobación de que no se copió mal un número.
    assert round(OFICIAL["votacion_estatal_emitida"]
                 / OFICIAL["diputaciones_pendientes_tras_directa"]) == 49678

    x = d["comprobacion_cruzada"]
    print(f"OK · oficial RP {d['oficial']['rp_total']} + MR "
          f"{d['oficial']['mr_total']} = {d['total_escanos']} · "
          f"reparto calculado {'coincide' if x['reparto_rp_coincide'] else 'DIFIERE'} "
          f"con el oficial")


if __name__ == "__main__":
    main()
