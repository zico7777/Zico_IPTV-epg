#!/usr/bin/env python3
import gzip
import io
import re
import sys
import urllib.request
from xml.etree import ElementTree as ET

M3U_FILE = "Zico Iptv.m3u"
OUTPUT_FILE = "guide.xml"
EPGSHARE_BASE = "https://epgshare01.online/epgshare01/epg_ripper_{code}1.xml.gz"
PAISES_EPGSHARE = ["AR", "BR", "CR", "ES", "FR", "MX", "PT", "UK", "US"]
OPEN_EPG_URLS = [
    "https://www.open-epg.com/files/unitedkingdom.xml.gz",
    "https://www.open-epg.com/files/unitedstates1.xml.gz",
    "https://www.open-epg.com/files/unitedstates10.xml.gz",
    "https://www.open-epg.com/files/unitedstates11.xml.gz"
]

def parse_m3u(path):
    canales = {}
    patron = re.compile(r'tvg-id="([^"]*)"\s+tvg-name="([^"]*)"\s+tvg-logo="([^"]*)"')
    with open(path, encoding="utf-8") as f:
        for linea in f:
            if linea.startswith("#EXTINF"):
                m = patron.search(linea)
                if not m:
                    continue
                tid, nombre, logo = m.groups()
                if tid and tid not in canales:
                    canales[tid] = {"nombre": nombre, "logo": logo}
    return canales

def descargar_gz(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    try:
        return gzip.decompress(data)
    except OSError:
        return data

def filtrar_programas(xml_bytes, ids_validos):
    programas = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"[AVISO] XML inválido: {e}", file=sys.stderr)
        return programas
    for prog in root.findall("programme"):
        ch = prog.get("channel")
        if ch in ids_validos:
            programas.append(prog)
    return programas

def main():
    print("Leyendo M3U...")
    canales = parse_m3u(M3U_FILE)
    ids_validos = set(canales.keys())
    print(f"  Canales con tvg-id: {len(ids_validos)}")

    todos_programas = []
    for code in PAISES_EPGSHARE:
        url = EPGSHARE_BASE.format(code=code)
        print(f"Descargando {code}: {url}")
        try:
            xml_bytes = descargar_gz(url)
        except Exception as e:
            print(f"  [ERROR] {code}: {e}", file=sys.stderr)
            continue
        programas = filtrar_programas(xml_bytes, ids_validos)
        print(f"  {code}: {len(programas)} programas coincidentes")
        todos_programas.extend(programas)

    for url in OPEN_EPG_URLS:
        print(f"Descargando open-epg: {url}")
        try:
            xml_bytes = descargar_gz(url)
        except Exception as e:
            print(f"  [ERROR] open-epg: {e}", file=sys.stderr)
            continue
        programas = filtrar_programas(xml_bytes, ids_validos)
        print(f"  open-epg: {len(programas)} programas coincidentes")
        todos_programas.extend(programas)

    tv = ET.Element("tv", {
        "generator-info-name": "Zico IPTV EPG",
        "generator-info-url": "https://github.com/",
    })

    for tid, info in canales.items():
        ch = ET.SubElement(tv, "channel", {"id": tid})
        dn = ET.SubElement(ch, "display-name")
        dn.text = info["nombre"]
        if info["logo"]:
            ET.SubElement(ch, "icon", {"src": info["logo"]})

    for prog in todos_programas:
        tv.append(prog)

    tree = ET.ElementTree(tv)
    ET.indent(tree, space="  ")
    tree.write(OUTPUT_FILE, encoding="UTF-8", xml_declaration=True)
    print(f"OK: {OUTPUT_FILE} generado con {len(todos_programas)} programas.")

if __name__ == "__main__":
    main()
