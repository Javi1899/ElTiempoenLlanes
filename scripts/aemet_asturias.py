#!/usr/bin/env python3
"""Descarga las observaciones horarias de AEMET (todas las estaciones) y guarda solo las de Asturias.

Uso: AEMET_API_KEY=... python3 scripts/aemet_asturias.py out/asturias-temperaturas.json
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

# sur, norte, oeste, este (Asturias y su entorno inmediato)
BOX = (42.95, 43.72, -7.25, -4.50)
URL = "https://opendata.aemet.es/opendata/api/observacion/convencional/todas"


def descargar(url, clave, intentos=4):
    ultimo = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(
                url,
                headers={"api_key": clave, "Accept": "application/json", "User-Agent": "tiempo-llanes"},
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
                charset = r.headers.get_content_charset()
            for enc in ([charset] if charset else []) + ["utf-8", "latin-1"]:
                try:
                    return json.loads(raw.decode(enc))
                except (UnicodeDecodeError, LookupError):
                    continue
            raise ValueError("no se pudo decodificar la respuesta")
        except Exception as e:  # reintenta ante errores de red o límite de peticiones
            ultimo = e
            print(f"intento {i + 1} fallido: {e}", file=sys.stderr)
            time.sleep(5 * (i + 1))
    raise ultimo


def filtrar(datos):
    obs = []
    for o in datos:
        try:
            lat, lon, v = float(o["lat"]), float(o["lon"]), float(o["ta"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (BOX[0] <= lat <= BOX[1] and BOX[2] <= lon <= BOX[3]) or not o.get("fint"):
            continue
        obs.append({"id": o.get("idema"), "n": o.get("ubi"), "lat": lat, "lon": lon,
                    "alt": o.get("alt"), "f": o["fint"], "v": v})
    return obs


def main(salida):
    clave = os.environ.get("AEMET_API_KEY", "").strip()
    if not clave:
        sys.exit("Falta el secreto AEMET_API_KEY (Settings > Secrets and variables > Actions)")
    r = descargar(URL, clave)
    if r.get("estado") != 200:
        sys.exit(f"AEMET respondió {r.get('estado')}: {r.get('descripcion')}")
    obs = filtrar(descargar(r["datos"], clave))
    if not obs:
        sys.exit("AEMET no devolvió temperaturas de estaciones de Asturias")
    os.makedirs(os.path.dirname(salida) or ".", exist_ok=True)
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(
            {"generado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "fuente": "AEMET OpenData · observación convencional", "obs": obs},
            f, ensure_ascii=False, separators=(",", ":"),
        )
    print(f"{len(obs)} observaciones de {len({o['id'] for o in obs})} estaciones -> {salida}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: aemet_asturias.py salida.json")
    main(sys.argv[1])
