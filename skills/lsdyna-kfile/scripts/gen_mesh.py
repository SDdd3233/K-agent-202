"""Mesh generator for simple primitives -> LS-DYNA include file (*NODE/*ELEMENT/*SET).

Emits fixed-format cards (NODE: I8+3xE16, elements: I8 fields) into an include .k
file, plus a JSON summary on stdout (id ranges, set ids) for the calling agent.
Part/section/material cards are NOT emitted - the main deck owns those.

Subcommands (all take --pid, --nid0, --eid0, --sid0, -o out.k):
    plate     shell grid in a plane            --plane xy|yz|zx --origin x y z --size a b --div na nb
              sets: sid0+1..4 = amin,amax,bmin,bmax edges; sid0+5 = all edges
    box       solid hex grid                   --origin x y z --size lx ly lz --div nx ny nz
              sets: sid0+1..6 = xmin,xmax,ymin,ymax,zmin,zmax faces
    cylinder  solid cylinder along z (all-hex, square-to-circle mapped cross-section)
              --center x y --z0 z --radius r --height h --div nr nz   (nr = cells across radius)
              sets: sid0+5 = zmin face, sid0+6 = zmax face
    cylshell  shell surface of a cylinder along z   --center x y --z0 z --radius r --height h --div nc nz
              sets: sid0+5 = zmin ring, sid0+6 = zmax ring
    sphere    solid ball (cube-to-sphere mapped, all-hex)  --center x y z --radius r --div n
              (no node sets emitted - rigid balls constrain via MAT_RIGID CMO, not SPC)
    sphbox    SPH particle fill of a box       --origin x y z --size lx ly lz --div nx ny nz --rho <density in deck units>
    sphcyl    SPH particle fill of a cylinder along z  --center x y --z0 z --radius r --height h --div nr nz --rho <density>

Example:
    python gen_mesh.py plate --plane xy --origin 0 0 0 --size 200 200 --div 40 40 \
        --pid 1 --nid0 1000 --eid0 1000 --sid0 10 -o mesh_plate.k
"""
import argparse
import json
import math
import sys


def fmt_node(nid, x, y, z):
    return f"{nid:8d}{x:16.6E}{y:16.6E}{z:16.6E}"


def fmt_shell(eid, pid, n):
    return f"{eid:8d}{pid:8d}" + "".join(f"{i:8d}" for i in n)


def fmt_solid(eid, pid, n):
    return f"{eid:8d}{pid:8d}" + "".join(f"{i:8d}" for i in n)


def set_cards(sid, nids, title):
    lines = [f"*SET_NODE_LIST_TITLE", title, f"{sid:10d}"]
    row = []
    for nid in nids:
        row.append(f"{nid:10d}")
        if len(row) == 8:
            lines.append("".join(row))
            row = []
    if row:
        lines.append("".join(row))
    return lines


class Mesh:
    def __init__(self):
        self.nodes = []      # (nid, x, y, z)
        self.shells = []     # (eid, pid, [n1..n4])
        self.solids = []     # (eid, pid, [n1..n8])
        self.sph = []        # (nid, pid, mass)
        self.sets = []       # (sid, title, [nids])

    def write(self, path, header_lines):
        out = ["$" + "-" * 78]
        out += ["$ " + h for h in header_lines]
        out.append("$" + "-" * 78)
        out.append("*NODE")
        out.append("$#    nid               x               y               z")
        for nid, x, y, z in self.nodes:
            out.append(fmt_node(nid, x, y, z))
        if self.shells:
            out.append("*ELEMENT_SHELL")
            out.append("$#   eid     pid      n1      n2      n3      n4")
            for eid, pid, n in self.shells:
                out.append(fmt_shell(eid, pid, n))
        if self.solids:
            out.append("*ELEMENT_SOLID")
            out.append("$#   eid     pid      n1      n2      n3      n4      n5      n6      n7      n8")
            for eid, pid, n in self.solids:
                out.append(fmt_solid(eid, pid, n))
        if self.sph:
            out.append("*ELEMENT_SPH")
            out.append("$#    nid     pid            mass")
            for nid, pid, mass in self.sph:
                out.append(f"{nid:8d}{pid:8d}{mass:16.6E}")
        for sid, title, nids in self.sets:
            out += set_cards(sid, nids, title)
        with open(path, "w", encoding="ascii", newline="\n") as f:
            f.write("\n".join(out) + "\n")

    def summary(self):
        s = {
            "n_nodes": len(self.nodes),
            "n_shell": len(self.shells),
            "n_solid": len(self.solids),
            "n_sph": len(self.sph),
        }
        if self.nodes:
            s["nid_range"] = [self.nodes[0][0], self.nodes[-1][0]]
        eids = [e for e, _, _ in self.shells] + [e for e, _, _ in self.solids]
        if eids:
            s["eid_range"] = [min(eids), max(eids)]
        if self.sph:
            s["sph_nid_range"] = [self.sph[0][0], self.sph[-1][0]]
            s["sph_particle_mass"] = self.sph[0][2]
        s["node_sets"] = {title: sid for sid, title, _ in self.sets}
        return s


def grid_nodes(mesh, nid0, coords):
    """coords: list of (x,y,z); returns list of nids in same order."""
    nids = []
    nid = nid0
    for x, y, z in coords:
        mesh.nodes.append((nid, x, y, z))
        nids.append(nid)
        nid += 1
    return nids


def make_plate(a):
    m = Mesh()
    na, nb = a.div
    la, lb = a.size
    ox, oy, oz = a.origin
    idx = {}
    coords = []
    k = 0
    for j in range(nb + 1):
        for i in range(na + 1):
            u, v = la * i / na, lb * j / nb
            if a.plane == "xy":
                c = (ox + u, oy + v, oz)
            elif a.plane == "yz":
                c = (ox, oy + u, oz + v)
            else:  # zx
                c = (ox + v, oy, oz + u)
            coords.append(c)
            idx[(i, j)] = k
            k += 1
    nids = grid_nodes(m, a.nid0, coords)
    eid = a.eid0
    for j in range(nb):
        for i in range(na):
            n = [nids[idx[(i, j)]], nids[idx[(i + 1, j)]],
                 nids[idx[(i + 1, j + 1)]], nids[idx[(i, j + 1)]]]
            m.shells.append((eid, a.pid, n))
            eid += 1
    if getattr(a, "flip_normal", False):
        m.shells = [(eid, pid, [n[0], n[3], n[2], n[1]]) for eid, pid, n in m.shells]
    edges = {
        "amin": [nids[idx[(0, j)]] for j in range(nb + 1)],
        "amax": [nids[idx[(na, j)]] for j in range(nb + 1)],
        "bmin": [nids[idx[(i, 0)]] for i in range(na + 1)],
        "bmax": [nids[idx[(i, nb)]] for i in range(na + 1)],
    }
    allb = sorted(set(edges["amin"] + edges["amax"] + edges["bmin"] + edges["bmax"]))
    for off, key in enumerate(["amin", "amax", "bmin", "bmax"], start=1):
        m.sets.append((a.sid0 + off, f"plate pid{a.pid} edge {key}", edges[key]))
    m.sets.append((a.sid0 + 5, f"plate pid{a.pid} all edges", allb))
    return m


def hex_block(m, a, mapper, nx, ny, nz):
    """Structured (nx,ny,nz) hex block; mapper(i,j,k)->(x,y,z)."""
    idx = {}
    coords = []
    c = 0
    for k in range(nz + 1):
        for j in range(ny + 1):
            for i in range(nx + 1):
                coords.append(mapper(i, j, k))
                idx[(i, j, k)] = c
                c += 1
    nids = grid_nodes(m, a.nid0, coords)
    eid = a.eid0
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                n = [nids[idx[(i, j, k)]], nids[idx[(i + 1, j, k)]],
                     nids[idx[(i + 1, j + 1, k)]], nids[idx[(i, j + 1, k)]],
                     nids[idx[(i, j, k + 1)]], nids[idx[(i + 1, j, k + 1)]],
                     nids[idx[(i + 1, j + 1, k + 1)]], nids[idx[(i, j + 1, k + 1)]]]
                m.solids.append((eid, a.pid, n))
                eid += 1
    return nids, idx


def make_box(a):
    m = Mesh()
    nx, ny, nz = a.div
    lx, ly, lz = a.size
    ox, oy, oz = a.origin
    nids, idx = hex_block(m, a, lambda i, j, k: (ox + lx * i / nx, oy + ly * j / ny, oz + lz * k / nz),
                          nx, ny, nz)
    faces = {
        "xmin": [nids[idx[(0, j, k)]] for k in range(nz + 1) for j in range(ny + 1)],
        "xmax": [nids[idx[(nx, j, k)]] for k in range(nz + 1) for j in range(ny + 1)],
        "ymin": [nids[idx[(i, 0, k)]] for k in range(nz + 1) for i in range(nx + 1)],
        "ymax": [nids[idx[(i, ny, k)]] for k in range(nz + 1) for i in range(nx + 1)],
        "zmin": [nids[idx[(i, j, 0)]] for j in range(ny + 1) for i in range(nx + 1)],
        "zmax": [nids[idx[(i, j, nz)]] for j in range(ny + 1) for i in range(nx + 1)],
    }
    for off, key in enumerate(["xmin", "xmax", "ymin", "ymax", "zmin", "zmax"], start=1):
        m.sets.append((a.sid0 + off, f"box pid{a.pid} face {key}", sorted(faces[key])))
    return m


def axis_perm(axis, p):
    """Reorient a point generated for an axis-z primitive onto axis x/y/z.
    axis y: --center means (x,z), --z0 is the y start; axis x: --center means (y,z), --z0 is the x start."""
    a, b, c = p
    if axis == "y":
        return (a, c, b)
    if axis == "x":
        return (c, a, b)
    return (a, b, c)


def sq2circle(u, v):
    """Elliptical map of [-1,1]^2 square onto unit disk (all-quad, no poles)."""
    return (u * math.sqrt(max(0.0, 1.0 - v * v / 2.0)),
            v * math.sqrt(max(0.0, 1.0 - u * u / 2.0)))


def make_cylinder(a):
    m = Mesh()
    nr, nz = a.div
    n = 2 * nr  # cells across the diameter
    cx, cy = a.center
    def mapper(i, j, k):
        u = 2.0 * i / n - 1.0
        v = 2.0 * j / n - 1.0
        x, y = sq2circle(u, v)
        return axis_perm(a.axis, (cx + a.radius * x, cy + a.radius * y,
                                  a.z0 + a.height * k / nz))
    nids, idx = hex_block(m, a, mapper, n, n, nz)
    zmin = sorted(nids[idx[(i, j, 0)]] for j in range(n + 1) for i in range(n + 1))
    zmax = sorted(nids[idx[(i, j, nz)]] for j in range(n + 1) for i in range(n + 1))
    m.sets.append((a.sid0 + 5, f"cyl pid{a.pid} zmin face", zmin))
    m.sets.append((a.sid0 + 6, f"cyl pid{a.pid} zmax face", zmax))
    return m


def make_cylshell(a):
    m = Mesh()
    nc, nz = a.div
    cx, cy = a.center
    idx = {}
    coords = []
    c = 0
    for k in range(nz + 1):
        for i in range(nc):
            th = 2.0 * math.pi * i / nc
            coords.append(axis_perm(a.axis, (cx + a.radius * math.cos(th),
                                             cy + a.radius * math.sin(th),
                                             a.z0 + a.height * k / nz)))
            idx[(i, k)] = c
            c += 1
    nids = grid_nodes(m, a.nid0, coords)
    eid = a.eid0
    for k in range(nz):
        for i in range(nc):
            i2 = (i + 1) % nc
            n = [nids[idx[(i, k)]], nids[idx[(i2, k)]],
                 nids[idx[(i2, k + 1)]], nids[idx[(i, k + 1)]]]
            m.shells.append((eid, a.pid, n))
            eid += 1
    m.sets.append((a.sid0 + 5, f"cylshell pid{a.pid} zmin ring", [nids[idx[(i, 0)]] for i in range(nc)]))
    m.sets.append((a.sid0 + 6, f"cylshell pid{a.pid} zmax ring", [nids[idx[(i, nz)]] for i in range(nc)]))
    if getattr(a, "flip_normal", False):
        m.shells = [(eid, pid, [n[0], n[3], n[2], n[1]]) for eid, pid, n in m.shells]
    return m


def cube2sphere(u, v, w):
    """Map [-1,1]^3 cube point to unit ball (spherified cube, all-hex)."""
    x = u * math.sqrt(max(0.0, 1.0 - v * v / 2.0 - w * w / 2.0 + v * v * w * w / 3.0))
    y = v * math.sqrt(max(0.0, 1.0 - w * w / 2.0 - u * u / 2.0 + w * w * u * u / 3.0))
    z = w * math.sqrt(max(0.0, 1.0 - u * u / 2.0 - v * v / 2.0 + u * u * v * v / 3.0))
    return x, y, z


def make_sphere(a):
    m = Mesh()
    n = a.div[0]
    cx, cy, cz = a.center
    def mapper(i, j, k):
        u = 2.0 * i / n - 1.0
        v = 2.0 * j / n - 1.0
        w = 2.0 * k / n - 1.0
        x, y, z = cube2sphere(u, v, w)
        return (cx + a.radius * x, cy + a.radius * y, cz + a.radius * z)
    hex_block(m, a, mapper, n, n, n)
    return m


def make_sphbox(a):
    m = Mesh()
    nx, ny, nz = a.div
    lx, ly, lz = a.size
    ox, oy, oz = a.origin
    mass = a.rho * lx * ly * lz / (nx * ny * nz)
    nid = a.nid0
    nids = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                x = ox + lx * (i + 0.5) / nx
                y = oy + ly * (j + 0.5) / ny
                z = oz + lz * (k + 0.5) / nz
                m.nodes.append((nid, x, y, z))
                m.sph.append((nid, a.pid, mass))
                nids.append(nid)
                nid += 1
    m.sets.append((a.sid0 + 1, f"sph pid{a.pid} all particles", nids))
    return m


def make_sphcyl(a):
    m = Mesh()
    nr, nz = a.div
    cx, cy = a.center
    dx = a.radius / nr           # particle pitch in the cross-section
    dzz = a.height / nz
    pts = []
    nspan = int(math.ceil(a.radius / dx))
    for k in range(nz):
        z = a.z0 + (k + 0.5) * dzz
        for j in range(-nspan, nspan + 1):
            for i in range(-nspan, nspan + 1):
                x = (i + 0.5) * dx
                y = (j + 0.5) * dx
                if x * x + y * y <= a.radius * a.radius:
                    pts.append(axis_perm(a.axis, (cx + x, cy + y, z)))
    vol = math.pi * a.radius ** 2 * a.height
    mass = a.rho * vol / len(pts)
    nid = a.nid0
    nids = []
    for x, y, z in pts:
        m.nodes.append((nid, x, y, z))
        m.sph.append((nid, a.pid, mass))
        nids.append(nid)
        nid += 1
    m.sets.append((a.sid0 + 1, f"sph pid{a.pid} all particles", nids))
    return m


def main(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, ndiv):
        sp.add_argument("--pid", type=int, required=True)
        sp.add_argument("--nid0", type=int, required=True, help="first node id")
        sp.add_argument("--eid0", type=int, required=True, help="first element id")
        sp.add_argument("--sid0", type=int, default=0, help="node-set id base")
        sp.add_argument("--div", type=int, nargs=ndiv, required=True)
        sp.add_argument("-o", "--out", required=True)

    sp = sub.add_parser("plate"); common(sp, 2)
    sp.add_argument("--plane", choices=["xy", "yz", "zx"], default="xy")
    sp.add_argument("--origin", type=float, nargs=3, required=True)
    sp.add_argument("--size", type=float, nargs=2, required=True)
    sp.add_argument("--flip-normal", action="store_true",
                    help="reverse shell connectivity (n1n2n3n4 -> n1n4n3n2) to flip normals")

    sp = sub.add_parser("box"); common(sp, 3)
    sp.add_argument("--origin", type=float, nargs=3, required=True)
    sp.add_argument("--size", type=float, nargs=3, required=True)

    sp = sub.add_parser("cylinder"); common(sp, 2)
    sp.add_argument("--center", type=float, nargs=2, required=True)
    sp.add_argument("--z0", type=float, required=True)
    sp.add_argument("--radius", type=float, required=True)
    sp.add_argument("--height", type=float, required=True)
    sp.add_argument("--axis", choices=["x", "y", "z"], default="z",
                    help="cylinder axis; for y: --center=(x,z) --z0=y start; for x: --center=(y,z) --z0=x start")

    sp = sub.add_parser("cylshell"); common(sp, 2)
    sp.add_argument("--center", type=float, nargs=2, required=True)
    sp.add_argument("--z0", type=float, required=True)
    sp.add_argument("--radius", type=float, required=True)
    sp.add_argument("--height", type=float, required=True)
    sp.add_argument("--axis", choices=["x", "y", "z"], default="z",
                    help="cylinder axis; for y: --center=(x,z) --z0=y start; for x: --center=(y,z) --z0=x start")
    sp.add_argument("--flip-normal", action="store_true",
                    help="reverse shell connectivity to flip normals outward/inward (FORMING contacts care)")

    sp = sub.add_parser("sphere"); common(sp, 1)
    sp.add_argument("--center", type=float, nargs=3, required=True)
    sp.add_argument("--radius", type=float, required=True)

    sp = sub.add_parser("sphbox"); common(sp, 3)
    sp.add_argument("--origin", type=float, nargs=3, required=True)
    sp.add_argument("--size", type=float, nargs=3, required=True)
    sp.add_argument("--rho", type=float, required=True, help="density in deck units")

    sp = sub.add_parser("sphcyl"); common(sp, 2)
    sp.add_argument("--center", type=float, nargs=2, required=True)
    sp.add_argument("--z0", type=float, required=True)
    sp.add_argument("--radius", type=float, required=True)
    sp.add_argument("--height", type=float, required=True)
    sp.add_argument("--rho", type=float, required=True, help="density in deck units")
    sp.add_argument("--axis", choices=["x", "y", "z"], default="z",
                    help="cylinder axis; for y: --center=(x,z) --z0=y start; for x: --center=(y,z) --z0=x start")

    a = p.parse_args(argv)
    maker = {"plate": make_plate, "box": make_box, "cylinder": make_cylinder,
             "cylshell": make_cylshell, "sphere": make_sphere,
             "sphbox": make_sphbox, "sphcyl": make_sphcyl}[a.cmd]
    m = maker(a)
    hdr = [f"gen_mesh.py {a.cmd} pid={a.pid}", " ".join(argv)]
    m.write(a.out, hdr)
    s = m.summary()
    s["file"] = a.out
    s["cmd"] = a.cmd
    s["pid"] = a.pid
    print(json.dumps(s, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
