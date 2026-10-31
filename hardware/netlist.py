#!/usr/bin/env python3
"""
Leest een KiCad-netlist (.net) in.

Bewust een echte s-expressie-parser en geen regels met reguliere expressies.
KiCad 9 schreef de netlist compact op een regel, KiCad 10 zet elk element op
een eigen regel - met regex-parsing breekt dat stilletjes en lijkt de netlist
leeg. Op de structuur parsen werkt voor beide, en voor wat er daarna komt.
"""
import re


def _tokeniseer(tekst):
    i, n = 0, len(tekst)
    while i < n:
        c = tekst[i]
        if c in "()":
            yield c
            i += 1
        elif c.isspace():
            i += 1
        elif c == '"':
            i += 1
            stuk = []
            while i < n and tekst[i] != '"':
                if tekst[i] == "\\" and i + 1 < n:
                    stuk.append(tekst[i + 1])
                    i += 2
                else:
                    stuk.append(tekst[i])
                    i += 1
            i += 1
            yield ('str', "".join(stuk))
        else:
            j = i
            while j < n and not tekst[j].isspace() and tekst[j] not in "()":
                j += 1
            yield ('sym', tekst[i:j])
            i = j


def ontleed(tekst):
    """Geeft de hele netlist als geneste lijsten."""
    stapel, huidig = [], []
    for t in _tokeniseer(tekst):
        if t == "(":
            stapel.append(huidig)
            huidig = []
        elif t == ")":
            klaar = huidig
            huidig = stapel.pop()
            huidig.append(klaar)
        else:
            huidig.append(t[1])
    return huidig[0] if len(huidig) == 1 else huidig


def kind(knoop, tag):
    """Eerste kind-lijst die met deze tag begint, of None."""
    for k in knoop:
        if isinstance(k, list) and k and k[0] == tag:
            return k
    return None


def kinderen(knoop, tag):
    return [k for k in knoop
            if isinstance(k, list) and k and k[0] == tag]


def waarde(knoop, tag, standaard=""):
    """De eerste waarde achter een tag, bv. (ref "U1") -> "U1"."""
    k = kind(knoop, tag)
    if not k or len(k) < 2:
        return standaard
    return k[1] if isinstance(k[1], str) else standaard


def lees(pad):
    """Geeft (onderdelen, netten).

    onderdelen : {ref: {"footprint":…, "value":…, "description":…}}
    netten     : {netnaam: [(ref, padnummer), …]}
    """
    boom = ontleed(open(pad, encoding="utf-8").read())
    onderdelen = {}
    comps = kind(boom, "components")
    for c in kinderen(comps or [], "comp"):
        ref = waarde(c, "ref")
        fp = waarde(c, "footprint")
        if not fp:                      # KiCad 9 zette hem alleen in fields
            velden = kind(c, "fields")
            for v in kinderen(velden or [], "field"):
                if waarde(v, "name") == "Footprint" and len(v) > 2:
                    fp = v[2]
        onderdelen[ref] = {"footprint": fp,
                           "value": waarde(c, "value"),
                           "description": waarde(c, "description")}
    netten = {}
    for net in kinderen(kind(boom, "nets") or [], "net"):
        naam = waarde(net, "name")
        netten[naam] = [(waarde(k, "ref"), waarde(k, "pin"))
                        for k in kinderen(net, "node")]
    return onderdelen, netten


def pinnamen(pad):
    """Pinnaam per pinnummer, per symbool: {symbool: {nummer: naam}}.

    Uit de libparts-sectie van de netlist, dus zoals het schema ze werkelijk
    gebruikt - niet zoals de bron zegt dat ze zouden moeten zijn.
    """
    boom = ontleed(open(pad, encoding="utf-8").read())
    uit = {}
    for lp in kinderen(kind(boom, "libparts") or [], "libpart"):
        uit[waarde(lp, "part")] = {waarde(p, "num"): waarde(p, "name")
                                   for p in kinderen(kind(lp, "pins") or [], "pin")}
    return uit


if __name__ == "__main__":
    import sys
    o, n = lees(sys.argv[1])
    print(f"{len(o)} onderdelen, {len(n)} netten")
