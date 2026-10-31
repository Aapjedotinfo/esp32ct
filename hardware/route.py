#!/usr/bin/env python3
"""
Legt de banen op esp32ct-revc.kicad_pcb, zonder externe autorouter.

Een rasterrouter: het bord wordt opgedeeld in cellen op twee lagen, en per
verbinding zoekt A* de goedkoopste weg. Rond elk pad, elke baan en elke via
ligt een verbodszone ter grootte van de afstandsregel plus de halve breedte
van de baan die erlangs wil. Zolang een baan buiten die zones blijft, haalt
hij de DRC vanzelf.

Die verbodszones worden per breedteklasse bijgehouden: een smal signaal van
0,3 mm mag dichter langs een pad dan een voedingsbaan van 0,6 mm. Met één
kaart voor de breedste baan paste er tussen de pinnen van de ESP32 niets meer.

Een net met meerdere pinnen groeit als boom: elke volgende pin mag aansluiten
op een pad of op een baan die al ligt. De bovenlaag heeft voorkeur, zodat het
GND-vlak op de onderkant zo heel mogelijk blijft. GND zelf wordt grotendeels
door de massavlakken gedragen; wat de router voor GND niet haalt, pakt het
vlak na het vullen meestal alsnog - de DRC beslist.

Draaien met de Python van KiCad:
  "/c/Program Files/KiCad/<versie>/bin/python.exe" route.py

Weigert een bord waar al banen op liggen, zodat handwerk niet verloren gaat.
Met OPNIEUW_ROUTEN=1 worden bestaande banen en via's eerst verwijderd.
"""
import os, sys, math, heapq, time
import pcbnew

HIER = os.path.dirname(os.path.abspath(__file__))
PROJ = "esp32ct-revc"
PCB = os.path.join(HIER, PROJ, PROJ + ".kicad_pcb")

G = float(os.environ.get("ROUTE_RASTER", 0.635))   # rastermaat, mm
LAGEN = (pcbnew.F_Cu, pcbnew.B_Cu)
LAAGKOST = (1.0, 1.6)          # onderlaag duurder: daar ligt het GND-vlak
VIAKOST = 8.0
VIA_D, VIA_BOOR = 0.8, 0.4

# Breedteklassen: halve baanbreedte waarvoor elke kaart wordt bijgehouden.
# Een net gebruikt de kleinste klasse waar zijn eigen halve breedte in past.
KLASSEN = (0.15, 0.30)

# Volgorde: eerst de brede en belangrijke netten, GND als laatste.
VOORRANG = {"VBIAS": 0, "+3V3": 1, "+5V": 1, "GND": 9}

RICHTINGEN = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
              (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2)),
              (-1, 1, math.sqrt(2)), (-1, -1, math.sqrt(2))]


def mm(v):
    return pcbnew.FromMM(float(v))


def naar_mm(v):
    return pcbnew.ToMM(v)


def klasse_voor(breedte):
    for k, half in enumerate(KLASSEN):
        if breedte / 2 <= half + 1e-6:
            return k
    return len(KLASSEN) - 1


class Rooster:
    """Twee lagen cellen. Per cel:
      kern         - van welk net het pad-koper op deze plek is (0 = geen pad,
                     -1 = hard verboden: rand, gat, antenne; <-1 = pad zonder net)
      eigen[k]     - per breedteklasse: welk net hier in de buurt koper heeft
                     (0 = vrij, -1 = te dicht bij twee verschillende netten)
    """

    def __init__(self, breed, hoog):
        self.nx = int(breed / G) + 1
        self.ny = int(hoog / G) + 1
        self.n = self.nx * self.ny
        self.kern = [[0] * self.n for _ in LAGEN]
        self.eigen = [[[0] * self.n for _ in LAGEN] for _ in KLASSEN]

    def idx(self, i, j):
        return j * self.nx + i

    def ij(self, idx):
        return idx % self.nx, idx // self.nx

    def xy(self, idx):
        i, j = self.ij(idx)
        return i * G, j * G

    def mag(self, laag, idx, net, k):
        kern = self.kern[laag][idx]
        if kern == net:
            return True            # eigen pad: altijd toegestaan
        if kern != 0:
            return False
        e = self.eigen[k][laag][idx]
        return e == 0 or e == net

    def _claim(self, k, laag, idx, net):
        kaart = self.eigen[k][laag]
        e = kaart[idx]
        if net < 0:
            kaart[idx] = -1
        elif e == 0:
            kaart[idx] = net
        elif e != net:
            kaart[idx] = -1

    def claim_rond(self, laag, x0, y0, x1, y1, basis, net):
        """Claim rond een rechthoek: basis + halve breedte van elke klasse."""
        for k, half in enumerate(KLASSEN):
            for idx in self.cellen_rond(x0, y0, x1, y1, basis + half):
                self._claim(k, laag, idx, net)

    def claim_langs(self, laag, a, b, basis, net):
        for k, half in enumerate(KLASSEN):
            for idx in self.cellen_langs(a, b, basis + half):
                self._claim(k, laag, idx, net)

    def cellen_rond(self, x0, y0, x1, y1, r):
        """Alle cellen waarvan het middelpunt binnen r van de rechthoek ligt."""
        i0, i1 = max(0, int((x0 - r) / G)), min(self.nx - 1, int((x1 + r) / G) + 1)
        j0, j1 = max(0, int((y0 - r) / G)), min(self.ny - 1, int((y1 + r) / G) + 1)
        for j in range(j0, j1 + 1):
            y = j * G
            dy = max(y0 - y, 0.0, y - y1)
            for i in range(i0, i1 + 1):
                x = i * G
                dx = max(x0 - x, 0.0, x - x1)
                if dx * dx + dy * dy <= r * r:
                    yield self.idx(i, j)

    def cellen_langs(self, a, b, r):
        """Alle cellen waarvan het middelpunt binnen r van segment a-b ligt."""
        (ax, ay), (bx, by) = a, b
        vx, vy = bx - ax, by - ay
        ll = vx * vx + vy * vy
        for idx in self.cellen_rond(min(ax, bx), min(ay, by),
                                    max(ax, bx), max(ay, by), r):
            x, y = self.xy(idx)
            t = 0.0 if ll == 0 else max(0.0, min(1.0, ((x - ax) * vx + (y - ay) * vy) / ll))
            dx, dy = x - (ax + t * vx), y - (ay + t * vy)
            if dx * dx + dy * dy <= r * r:
                yield idx


def bouw_rooster(bord, net_id, afstand, randafstand):
    """Zet randen, gaten, verbodsgebieden en alle pads in het rooster."""
    bb = bord.GetBoardEdgesBoundingBox()
    breed, hoog = naar_mm(bb.GetRight()), naar_mm(bb.GetBottom())
    R = Rooster(breed, hoog)
    breedste = KLASSEN[-1]

    # bordrand: behoudend, voor de breedste baan
    rand = randafstand + breedste
    for j in range(R.ny):
        for i in range(R.nx):
            x, y = i * G, j * G
            if x < rand or y < rand or x > breed - rand or y > hoog - rand:
                for l in range(2):
                    R.kern[l][R.idx(i, j)] = -1

    # verbodsgebieden (de antenne van de ESP32)
    for z in bord.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
            zb = z.GetBoundingBox()
            for idx in R.cellen_rond(naar_mm(zb.GetLeft()), naar_mm(zb.GetTop()),
                                     naar_mm(zb.GetRight()), naar_mm(zb.GetBottom()),
                                     breedste):
                for l in range(2):
                    R.kern[l][idx] = -1

    # pads
    geen_net = -2
    for fp in bord.GetFootprints():
        for pad in fp.Pads():
            pb = pad.GetBoundingBox()
            x0, y0 = naar_mm(pb.GetLeft()), naar_mm(pb.GetTop())
            x1, y1 = naar_mm(pb.GetRight()), naar_mm(pb.GetBottom())
            lagen = [l for l, L in enumerate(LAGEN) if pad.IsOnLayer(L)]
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                for idx in R.cellen_rond(x0, y0, x1, y1, afstand + breedste):
                    for l in range(2):
                        R.kern[l][idx] = -1
                continue
            net = net_id.get(pad.GetNetname(), 0)
            if net == 0:
                net = geen_net
                geen_net -= 1
            for l in lagen:
                raak = False
                for idx in R.cellen_rond(x0, y0, x1, y1, 0.0):
                    x, y = R.xy(idx)
                    if pad.HitTest(pcbnew.VECTOR2I(mm(x), mm(y))):
                        if R.kern[l][idx] == 0:
                            R.kern[l][idx] = net
                        raak = True
                if not raak:
                    # Pad valt tussen de roosterpunten: neem de dichtstbijzijnde cel.
                    c = pad.GetPosition()
                    R.kern[l][R.idx(int(round(naar_mm(c.x) / G)),
                                    int(round(naar_mm(c.y) / G)))] = net
                R.claim_rond(l, x0, y0, x1, y1, afstand, net if net > 0 else -1)
    return R


def kern_van(R, pad, net):
    """Knopen (laag, idx) die bij dit pad horen."""
    pb = pad.GetBoundingBox()
    uit = []
    for l, L in enumerate(LAGEN):
        if not pad.IsOnLayer(L):
            continue
        for idx in R.cellen_rond(naar_mm(pb.GetLeft()), naar_mm(pb.GetTop()),
                                 naar_mm(pb.GetRight()), naar_mm(pb.GetBottom()), G):
            if R.kern[l][idx] == net:
                uit.append((l, idx))
    return uit


def via_mag(R, idx, net):
    """Een via is 0,8 mm: behoudend toetsen tegen de kaart van de breedste baan,
    op de cel zelf en alle buren."""
    k = len(KLASSEN) - 1
    i, j = R.ij(idx)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            ii, jj = i + di, j + dj
            if not (0 <= ii < R.nx and 0 <= jj < R.ny):
                return False
            n = R.idx(ii, jj)
            for l in range(2):
                if not R.mag(l, n, net, k) or R.kern[l][n] == net:
                    return False
    return True


def zoek(R, net, k, starts, doelen):
    """A* van een van de startknopen naar een van de doelknopen."""
    if not doelen:
        return None
    di = [R.ij(idx)[0] for _, idx in doelen]
    dj = [R.ij(idx)[1] for _, idx in doelen]
    ti0, ti1, tj0, tj1 = min(di), max(di), min(dj), max(dj)

    def h(idx):
        i, j = R.ij(idx)
        dx = max(ti0 - i, 0, i - ti1)
        dy = max(tj0 - j, 0, j - tj1)
        return max(dx, dy) + (math.sqrt(2) - 1) * min(dx, dy)

    g, van, open_ = {}, {}, []
    for s in starts:
        g[s] = 0.0
        heapq.heappush(open_, (h(s[1]), 0.0, s))
    via_cache = {}
    while open_:
        f, kost, knoop = heapq.heappop(open_)
        if kost > g.get(knoop, math.inf):
            continue
        if knoop in doelen:
            pad = [knoop]
            while pad[-1] in van:
                pad.append(van[pad[-1]])
            return pad[::-1]
        l, idx = knoop
        i, j = R.ij(idx)
        buren = []
        for dx, dy, c in RICHTINGEN:
            ii, jj = i + dx, j + dy
            if not (0 <= ii < R.nx and 0 <= jj < R.ny):
                continue
            n = R.idx(ii, jj)
            if not R.mag(l, n, net, k):
                continue
            if dx and dy and not (R.mag(l, R.idx(i + dx, j), net, k)
                                  and R.mag(l, R.idx(i, j + dy), net, k)):
                continue           # geen hoeken afsnijden langs koper
            buren.append(((l, n), c * LAAGKOST[l]))
        ander = 1 - l
        if R.kern[l][idx] == net and R.kern[ander][idx] == net:
            buren.append(((ander, idx), 0.0))          # door het eigen pad heen
        elif R.mag(ander, idx, net, k):
            if idx not in via_cache:
                via_cache[idx] = via_mag(R, idx, net)
            if via_cache[idx]:
                buren.append(((ander, idx), VIAKOST))
        for b, c in buren:
            nk = kost + c
            if nk < g.get(b, math.inf):
                g[b] = nk
                van[b] = knoop
                heapq.heappush(open_, (nk + h(b[1]), nk, b))
    return None


def leg(bord, R, pad, net, netinfo, breedte, afstand, boom):
    """Zet een gevonden pad om naar banen en via's, en claim het rooster."""
    runs, huidig = [], [pad[0]]
    for a, b in zip(pad, pad[1:]):
        if a[1] == b[1] and a[0] != b[0]:          # laagwissel
            runs.append(huidig)
            if R.kern[a[0]][a[1]] != net:
                v = pcbnew.PCB_VIA(bord)
                x, y = R.xy(a[1])
                v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
                v.SetWidth(mm(VIA_D))
                v.SetDrill(mm(VIA_BOOR))
                v.SetViaType(pcbnew.VIATYPE_THROUGH)
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetNet(netinfo)
                bord.Add(v)
                for l in range(2):
                    R.claim_rond(l, x, y, x, y, VIA_D / 2 + afstand, net)
                    boom.add((l, a[1]))
            huidig = [b]
        else:
            huidig.append(b)
    runs.append(huidig)

    banen = 0
    for run in runs:
        if len(run) < 2:
            boom.update(run)
            continue
        l = run[0][0]
        punten = [R.xy(k[1]) for k in run]
        # rechte stukken samenvoegen
        kort = [punten[0]]
        for p, q, r in zip(punten, punten[1:], punten[2:]):
            if (round(q[0] - p[0], 4), round(q[1] - p[1], 4)) != \
               (round(r[0] - q[0], 4), round(r[1] - q[1], 4)):
                kort.append(q)
        kort.append(punten[-1])
        for a, b in zip(kort, kort[1:]):
            t = pcbnew.PCB_TRACK(bord)
            t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
            t.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
            t.SetWidth(mm(breedte))
            t.SetLayer(LAGEN[l])
            t.SetNet(netinfo)
            bord.Add(t)
            banen += 1
            R.claim_langs(l, a, b, breedte / 2 + afstand, net)
        boom.update(run)
    return banen


def main():
    bord = pcbnew.LoadBoard(PCB)
    bestaand = list(bord.GetTracks())
    if bestaand:
        if os.environ.get("OPNIEUW_ROUTEN") != "1":
            print(f"OVERGESLAGEN: er liggen al {len(bestaand)} banen/via's op het bord.\n"
                  "  Met OPNIEUW_ROUTEN=1 worden die eerst verwijderd.")
            return 0
        for t in bestaand:
            bord.Remove(t)

    ds = bord.GetDesignSettings()
    ns = ds.m_NetSettings
    pads_per_net = {}
    for fp in bord.GetFootprints():
        for pad in fp.Pads():
            n = pad.GetNetname()
            if n and not n.startswith("unconnected-"):
                pads_per_net.setdefault(n, []).append(pad)
    netten = {n: p for n, p in pads_per_net.items() if len(p) >= 2}
    net_id = {n: i + 1 for i, n in enumerate(sorted(pads_per_net))}

    breedtes = {n: naar_mm(ns.GetEffectiveNetClass(n).GetTrackWidth()) for n in netten}
    afstand = max(naar_mm(ns.GetEffectiveNetClass(n).GetClearance()) for n in netten)
    randafstand = naar_mm(ds.m_CopperEdgeClearance)
    R = bouw_rooster(bord, net_id, afstand, randafstand)
    print(f"rooster {R.nx} x {R.ny} x 2 lagen ({G} mm), afstand {afstand} mm, "
          f"rand {randafstand} mm, {len(netten)} netten")

    def lengte(pads):
        xs = [naar_mm(p.GetPosition().x) for p in pads]
        ys = [naar_mm(p.GetPosition().y) for p in pads]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))

    # Binnen een voorrangsgroep de LANGSTE eerst: een lange verbinding dwars
    # over het bord vindt later geen doorgang meer, een korte vindt altijd wel
    # een weg eromheen. Van kort naar lang liepen juist de lange vast.
    volgorde = sorted(netten, key=lambda n: (VOORRANG.get(n, 5), -lengte(netten[n])))
    mislukt, banen, t0 = [], 0, time.time()
    for naam in volgorde:
        net = net_id[naam]
        k = klasse_voor(breedtes[naam])
        netinfo = bord.FindNet(naam)
        pads = netten[naam]
        cx = sum(naar_mm(p.GetPosition().x) for p in pads) / len(pads)
        cy = sum(naar_mm(p.GetPosition().y) for p in pads) / len(pads)
        pads = sorted(pads, key=lambda p: (naar_mm(p.GetPosition().x) - cx) ** 2
                      + (naar_mm(p.GetPosition().y) - cy) ** 2)
        boom = set(kern_van(R, pads[0], net))
        open_pads = pads[1:]
        while open_pads:
            def afst(p):
                px, py = naar_mm(p.GetPosition().x), naar_mm(p.GetPosition().y)
                return min((R.xy(b[1])[0] - px) ** 2 + (R.xy(b[1])[1] - py) ** 2
                           for b in boom)
            p = min(open_pads, key=afst)
            open_pads.remove(p)
            starts = kern_van(R, p, net)
            if set(starts) & boom:
                boom.update(starts)
                continue
            gevonden = zoek(R, net, k, starts, boom)
            if gevonden is None:
                mislukt.append((naam, f"{p.GetParentFootprint().GetReference()}"
                                      f".{p.GetNumber()}"))
                continue
            banen += leg(bord, R, gevonden, net, netinfo, breedtes[naam], afstand, boom)
            boom.update(starts)
            for q in list(open_pads):
                if set(kern_van(R, q, net)) & boom:
                    open_pads.remove(q)
                    boom.update(kern_van(R, q, net))

    pcbnew.ZONE_FILLER(bord).Fill(bord.Zones())
    pcbnew.SaveBoard(PCB, bord)
    print(f"{banen} baansegmenten gelegd in {time.time() - t0:.0f} s")
    signaal = [m for m in mislukt if m[0] != "GND"]
    gnd = [m for m in mislukt if m[0] == "GND"]
    if gnd:
        print(f"{len(gnd)} GND-verbindingen niet als baan gelegd - het massavlak "
              "moet die dragen, de DRC beslist")
    if signaal:
        print(f"{len(signaal)} SIGNAALverbindingen niet gelukt:")
        for n, p in signaal:
            print(f"    {n}: {p}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
