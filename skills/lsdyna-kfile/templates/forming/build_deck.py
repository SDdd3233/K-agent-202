# Rebuild forming.k: full deck with quadratic stroke curve 901 and mass damping 902.
from pathlib import Path
import math

A = 24.4 / 0.017**2  # quadratic ramp constant

def disp(t):
    if t <= 0.003:   # smooth touchdown 0 -> -0.6 mm
        return -0.3 * (1 - math.cos(math.pi * t / 0.003))
    return -0.6 - A * (t - 0.003)**2   # speed grows with forming resistance

N = 200
curve = "\n".join(f"{i*0.02/N:20.10e}{disp(i*0.02/N):20.10e}" for i in range(N + 1))

head = """*KEYWORD
*TITLE
forming: quasi-static 3-point roll bending, rigid punch roller vs mild steel strip (mm-ton-s)
$
$ ============================= CONTROL =============================
$
*CONTROL_TERMINATION
$#  endtim    endcyc     dtmin    endeng    endmas     nosol
      0.02         0       0.0       0.0   1.0E+08         0
*CONTROL_ENERGY
$#    hgen      rwen    slnten     rylen
         2         2         2         2
*CONTROL_TIMESTEP
$#  dtinit    tssfac      isdo    tslimt     dt2ms      lctm     erode     ms1st
       0.0       0.9         0       0.0  -4.0E-07         0         0         0
$
$ ============================= DATABASE =============================
$
*DATABASE_GLSTAT
$#      dt    binary      lcur     ioopt
  1.000E-4         3         0         1
*DATABASE_MATSUM
$#      dt    binary      lcur     ioopt
  1.000E-4         3         0         1
*DATABASE_BINARY_D3PLOT
$#      dt      lcdt      beam     npltc    psetid
  1.000E-3         0         0         0         0
$
$ ============================= DAMPING =============================
$
$ mass damping on the strip only (curve 902): base 2000/s with a staged
$ boost (8000/s at 7.8-10.2 ms, 4000/s to 12.2 ms) across full tool engagement, absorbing the
$ elastic springback burst; keeps kinetic/internal energy < 5% through the stroke
*DAMPING_PART_MASS
$#     pid      lcid        sf      flag
         1       902       1.0         0
$
$ ============================= MATERIALS =============================
$
$ Part 1 strip: mild steel Q235-class, bilinear hardening (units.py mm-ton-s steel_mild)
*MAT_PIECEWISE_LINEAR_PLASTICITY
$#     mid        ro         e        pr      sigy      etan      fail      tdel
         1  7.85E-09  210000.0       0.3     235.0    1200.0       0.0       0.0
$#       c         p      lcss      lcsr        vp
       0.0       0.0         0         0       0.0
$#    eps1      eps2      eps3      eps4      eps5      eps6      eps7      eps8
       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0
$#     es1       es2       es3       es4       es5       es6       es7       es8
       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0
$ Part 2 punch roller: rigid, only z-translation free (CMO=1 CON1=4 CON2=7)
*MAT_RIGID
$#     mid        ro         e        pr         n    couple         m     alias
         2  7.85E-09  210000.0       0.3       0.0       0.0       0.0
$#     cmo      con1      con2    spcnid      xspc      yspc      zspc
       1.0         4         7
$#     lco        a2        a3        v1        v2        v3
       0.0       0.0       0.0       0.0       0.0       0.0
$ Part 3 left support roller: rigid, fully fixed (CMO=1 CON1=7 CON2=7)
*MAT_RIGID
$#     mid        ro         e        pr         n    couple         m     alias
         3  7.85E-09  210000.0       0.3       0.0       0.0       0.0
$#     cmo      con1      con2    spcnid      xspc      yspc      zspc
       1.0         7         7
$#     lco        a2        a3        v1        v2        v3
       0.0       0.0       0.0       0.0       0.0       0.0
$ Part 4 right support roller: rigid, fully fixed (CMO=1 CON1=7 CON2=7)
*MAT_RIGID
$#     mid        ro         e        pr         n    couple         m     alias
         4  7.85E-09  210000.0       0.3       0.0       0.0       0.0
$#     cmo      con1      con2    spcnid      xspc      yspc      zspc
       1.0         7         7
$#     lco        a2        a3        v1        v2        v3
       0.0       0.0       0.0       0.0       0.0       0.0
$
$ ========================== SECTIONS / PARTS ==========================
$
$ strip: fully integrated shell (ELFORM=16), 5 integration points, t=1.5 mm
*SECTION_SHELL
$#   secid    elform      shrf       nip     propt   qr/irid     icomp     setyp
         1        16    0.8333         5       1.0         0         0         1
$#      t1        t2        t3        t4      nloc     marea      idof    edgset
       1.5       1.5       1.5       1.5       0.0       0.0       0.0         0
$ punch roller: Belytschko-Tsay shell (rigid tool skin), t=0.5 mm
*SECTION_SHELL
$#   secid    elform      shrf       nip     propt   qr/irid     icomp     setyp
         2         2       1.0         2       1.0         0         0         1
$#      t1        t2        t3        t4      nloc     marea      idof    edgset
       0.5       0.5       0.5       0.5       0.0       0.0       0.0         0
$ support rollers: same rigid tool skin section
*SECTION_SHELL
$#   secid    elform      shrf       nip     propt   qr/irid     icomp     setyp
         3         2       1.0         2       1.0         0         0         1
$#      t1        t2        t3        t4      nloc     marea      idof    edgset
       0.5       0.5       0.5       0.5       0.0       0.0       0.0         0
*SECTION_SHELL
$#   secid    elform      shrf       nip     propt   qr/irid     icomp     setyp
         4         2       1.0         2       1.0         0         0         1
$#      t1        t2        t3        t4      nloc     marea      idof    edgset
       0.5       0.5       0.5       0.5       0.0       0.0       0.0         0
*PART
$#                                                                         title
strip (deformable blank)
$#     pid     secid       mid     eosid      hgid      grav    adpopt      tmid
         1         1         1         0         0         0         0         0
*PART
$#                                                                         title
punch roller (rigid, z-motion prescribed)
$#     pid     secid       mid     eosid      hgid      grav    adpopt      tmid
         2         2         2         0         0         0         0         0
*PART
$#                                                                         title
left support roller (rigid, fixed)
$#     pid     secid       mid     eosid      hgid      grav    adpopt      tmid
         3         3         3         0         0         0         0         0
*PART
$#                                                                         title
right support roller (rigid, fixed)
$#     pid     secid       mid     eosid      hgid      grav    adpopt      tmid
         4         4         4         0         0         0         0         0
$
$ ============================ MESH INCLUDES ============================
$
*INCLUDE
mesh_strip.k
*INCLUDE
mesh_punch.k
*INCLUDE
mesh_sup_left.k
*INCLUDE
mesh_sup_right.k
$
$ ============================== CONTACT ==============================
$
$ forming one-way: SURFA = strip (tracked), SURFB = tool, FS=0.12, VDC=20 damping
*CONTACT_FORMING_ONE_WAY_SURFACE_TO_SURFACE
$#   surfa     surfb  surfatyp  surfbtyp   saboxid   sbboxid      sapr      sbpr
         1         2         3         3         0         0         0         0
$#      fs        fd        dc        vc       vdc    penchk        bt        dt
      0.12      0.12       0.0       0.0      20.0         0       0.0       0.0
$#    sfsa      sfsb      sast      sbst     sfsat     sfsbt       fsf       vsf
       1.0       1.0       0.0       0.0       1.0       1.0       1.0       1.0
*CONTACT_FORMING_ONE_WAY_SURFACE_TO_SURFACE
$#   surfa     surfb  surfatyp  surfbtyp   saboxid   sbboxid      sapr      sbpr
         1         3         3         3         0         0         0         0
$#      fs        fd        dc        vc       vdc    penchk        bt        dt
      0.12      0.12       0.0       0.0      20.0         0       0.0       0.0
$#    sfsa      sfsb      sast      sbst     sfsat     sfsbt       fsf       vsf
       1.0       1.0       0.0       0.0       1.0       1.0       1.0       1.0
*CONTACT_FORMING_ONE_WAY_SURFACE_TO_SURFACE
$#   surfa     surfb  surfatyp  surfbtyp   saboxid   sbboxid      sapr      sbpr
         1         4         3         3         0         0         0         0
$#      fs        fd        dc        vc       vdc    penchk        bt        dt
      0.12      0.12       0.0       0.0      20.0         0       0.0       0.0
$#    sfsa      sfsb      sast      sbst     sfsat     sfsbt       fsf       vsf
       1.0       1.0       0.0       0.0       1.0       1.0       1.0       1.0
$
$ ========================= BOUNDARY / INITIAL =========================
$
$ all strip nodes: near-plane-strain constraint (uy, rotx, rotz fixed)
*SET_NODE_LIST_GENERATE
$#     sid       da1       da2       da3       da4    solver
        18       0.0       0.0       0.0       0.0      MECH
$#   b1beg     b1end     b2beg     b2end     b3beg     b3end     b4beg     b4end
    100000    101376
*BOUNDARY_SPC_SET
$#    nsid       cid      dofx      dofy      dofz     dofrx     dofry     dofrz
        18         0         0         1         0         1         0         1
$
$ =============================== LOADS ===============================
$
$ damping constant vs time for *DAMPING_PART_MASS
*DEFINE_CURVE
$#    lcid      sidr       sfa       sfo      offa      offo    dattyp     lcint
       902         0       1.0       1.0       0.0       0.0         0         0
$#                  a1                  o1
    0.0000000000e+00    2.0000000000e+03
    7.4000000000e-03    2.0000000000e+03
    7.8000000000e-03    8.0000000000e+03
    1.0200000000e-02    8.0000000000e+03
    1.1000000000e-02    4.0000000000e+03
    1.2200000000e-02    4.0000000000e+03
    1.3000000000e-02    2.0000000000e+03
    1.0000000000e+00    2.0000000000e+03
$ punch stroke: smooth touchdown (0 -> -0.6 mm over 3 ms, contact speed ~0.23 m/s),
$ then quadratic ramp -0.6 -> -25 mm: speed grows with forming resistance so the
$ kinetic/internal energy ratio stays low; 201-point sampling (VAD=2 displacement)
*BOUNDARY_PRESCRIBED_MOTION_RIGID
$#  typeid       dof       vad      lcid        sf       vid     death     birth
         2         3         2       901       1.0         0       0.0       0.0
*DEFINE_CURVE
$#    lcid      sidr       sfa       sfo      offa      offo    dattyp     lcint
       901         0       1.0       1.0       0.0       0.0         0         0
$#                  a1                  o1
"""

with open(Path(__file__).resolve().parent / "forming.k", "w", newline=chr(10)) as f:
    f.write(head + curve + "\n*END\n")
print("deck rebuilt OK")
