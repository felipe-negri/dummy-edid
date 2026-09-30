#!/usr/bin/env python3
"""Gera o EDID do dummy HDMI da void com modos nativos dos clientes de streaming.

Galaxy S26 Ultra: 3120x1440, 2340x1080 (FHD+) e 1560x720 (HD+)
Galaxy Tab S9 Ultra: 2960x1848@90 (120 Hz não cabe no TMDS de 600 MHz) e 2560x1600@120
Dispositivos só a 120 Hz (a taxa da tela deles); 60 Hz fica só no 1080p do desktop.

Timings = CVT-RB2 (`edid-decode --cvt w=..,h=..,fps=..,rb=2`).
Uso: python3 build_edid.py [saida.bin]   (padrão: edid/void-dummy.bin)
"""
import re
from math import gcd
import subprocess
import sys

# (w, h, fps) — o 1o é o preferido (desktop), o 2o também vai no bloco base
MODES = [
    (1920, 1080, 60),    # desktop
    (3120, 1440, 120),   # S26 Ultra nativo
    (2340, 1080, 120),   # S26 Ultra FHD+
    (1560, 720, 120),    # S26 Ultra HD+
    (2960, 1848, 90),    # Tab S9 Ultra nativo (120 Hz daria 713 MHz, acima do TMDS)
    (2560, 1600, 120),   # Tab S9 Ultra em 16:10 a 120 Hz
]
MAX_TMDS_MHZ = 600


def cvt(w, h, fps):
    if (w, h, fps) == (1920, 1080, 60):   # CEA 1080p60, igual ao EDID original
        return dict(clk=148.5, ha=1920, hfp=88, hs=44, hbp=148, va=1080, vfp=4, vs=5, vbp=36, hpol=1, vpol=1)
    out = subprocess.run(["edid-decode", "--cvt", f"w={w},h={h},fps={fps},rb=2"],
                         capture_output=True, text=True).stdout
    clk = float(re.search(r"([\d.]+) MHz", out).group(1))
    hf, hs, hb = map(int, re.search(r"Hfront\s+(\d+) Hsync\s+(\d+) Hback\s+(\d+)", out).groups())
    vf, vs, vb = map(int, re.search(r"Vfront\s+(\d+) Vsync\s+(\d+) Vback\s+(\d+)", out).groups())
    if vf > 63:   # DTD só tem 6 bits de Vfront: o excesso vai pro Vback (Vblank total igual)
        vb += vf - 63
        vf = 63
    return dict(clk=clk, ha=w, hfp=hf, hs=hs, hbp=hb, va=h, vfp=vf, vs=vs, vbp=vb, hpol=1, vpol=0)


def dtd(t):
    pc = round(t["clk"] * 100)            # unidades de 10 kHz
    hbl = t["hfp"] + t["hs"] + t["hbp"]
    vbl = t["vfp"] + t["vs"] + t["vbp"]
    ha, va = t["ha"], t["va"]
    hmm = 600
    vmm = round(600 * va / ha)
    flags = 0x18 | (0x04 if t["vpol"] else 0) | (0x02 if t["hpol"] else 0)  # digital separate sync
    return bytes([
        pc & 0xFF, pc >> 8,
        ha & 0xFF, hbl & 0xFF, ((ha >> 8) << 4) | (hbl >> 8),
        va & 0xFF, vbl & 0xFF, ((va >> 8) << 4) | (vbl >> 8),
        t["hfp"] & 0xFF, t["hs"] & 0xFF,
        ((t["vfp"] & 0xF) << 4) | (t["vs"] & 0xF),
        ((t["hfp"] >> 8) << 6) | ((t["hs"] >> 8) << 4) | ((t["vfp"] >> 4) << 2) | (t["vs"] >> 4),
        hmm & 0xFF, vmm & 0xFF, ((hmm >> 8) << 4) | (vmm >> 8),
        0, 0, flags,
    ])


def text_desc(tag, s):
    b = s.encode()[:13]
    b = b + (b"\n" + b" " * 12 if len(b) < 13 else b"")
    return bytes([0, 0, 0, tag, 0]) + b[:13]


def checksum(block):
    return bytes([(-sum(block)) & 0xFF])


def base_block(timings):
    b = bytearray()
    b += bytes([0, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0])
    b += bytes([0x59, 0xE4])              # fabricante "VOD"
    b += bytes([0x26, 0x0A])              # produto 0x0A26
    b += bytes([0, 0, 0, 0])              # serial
    b += bytes([39, 2026 - 1990])         # semana/ano
    b += bytes([1, 3])                    # EDID 1.3 (a spec HDMI exige 1.3)
    b += bytes([0x80, 60, 38, 0x78, 0x0A])  # digital, 60x38cm, gamma 2.2, RGB, 1o DTD preferido
    b += bytes([0xCF, 0x74, 0xA3, 0x57, 0x4C, 0xB0, 0x23, 0x09, 0x48, 0x4C])  # cromaticidade original
    b += bytes([0x21, 0x08, 0x00])        # established 640x480, 800x600, 1024x768
    std = [(1280, 1024, 60), (1280, 800, 60), (1440, 900, 60), (1600, 900, 60),
           (1680, 1050, 60), (1920, 1200, 60), (1600, 1200, 60)]  # 2560 não cabe em std timing (máx 2288)
    aspect = {(16, 10): 0, (4, 3): 1, (5, 4): 2, (16, 9): 3}
    for w, h, f in std:
        g = gcd(w, h); ar = (w // g, h // g)
        ar = {(8, 5): (16, 10)}.get(ar, ar)
        b += bytes([w // 8 - 31, (aspect[ar] << 6) | (f - 60)])
    b += bytes([1, 1] * (8 - len(std)))
    b += dtd(timings[0])
    b += dtd(timings[1])
    b += bytes([0, 0, 0, 0xFD, 0, 24, 144, 15, 255, MAX_TMDS_MHZ // 10, 0x00, 0x0A]) + b" " * 6  # range limits
    b += text_desc(0xFC, "void-dummy")
    b += bytes([1])                       # 1 extensão
    assert len(b) == 127, len(b)
    return bytes(b) + checksum(b)


def cta_block(timings):
    vics = [16, 63, 4, 31, 95, 94, 93, 3]  # 1080p60(nativo), 1080p120, 720p60, 1080p50, 4K30/25/24, 480p
    vdb = bytes([(2 << 5) | len(vics)]) + bytes([0x80 | vics[0]] + vics[1:])
    adb = bytes([(1 << 5) | 3, 0x09, 0x07, 0x07])                     # LPCM 2ch 32/44.1/48 16/20/24
    hdmi = bytes([(3 << 5) | 7, 0x03, 0x0C, 0x00, 0x10, 0x00, 0x00, 0x44])  # HDMI 1.4 VSDB, PA 1.0.0.0, 340 MHz
    hf = bytes([(3 << 5) | 7, 0xD8, 0x5D, 0xC4, 0x01, MAX_TMDS_MHZ // 5, 0x88, 0x00])  # HF-VSDB: 600 MHz, SCDC
    vcdb = bytes([(7 << 5) | 2, 0x00, 0xCF])                           # VCDB: RGB quantization selecionável
    data = vdb + adb + hdmi + hf + vcdb
    dtds = b"".join(dtd(t) for t in timings)
    b = bytearray([0x02, 0x03, 4 + len(data), 0x80 | 0x40 | 0x20 | 0x10 | 1])  # underscan, basic audio, 444, 422; 1 DTD nativo
    b += data + dtds
    assert len(b) <= 127, f"CTA estourou: {len(b)}"
    b += bytes(127 - len(b))
    return bytes(b) + checksum(b)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "edid/void-dummy.bin"
    timings = [cvt(*m) for m in MODES]
    for m, t in zip(MODES, timings):
        assert t["clk"] <= MAX_TMDS_MHZ, (m, t["clk"])
    edid = base_block(timings[:2]) + cta_block(timings[2:])
    open(out, "wb").write(edid)
    print(f"{out}: {len(edid)} bytes")


if __name__ == "__main__":
    main()
