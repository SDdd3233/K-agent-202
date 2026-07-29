*KEYWORD
*TITLE
drop: rigid steel block drop onto clamped aluminum plate (mm-ton-s)
$
$ ==== CONTROL ====
$
*CONTROL_TERMINATION
$#  endtim    endcyc     dtmin    endeng    endmas     nosol
    3.0E-3         0       0.0       0.0     1.0E8         0
*CONTROL_ENERGY
$#    hgen      rwen    slnten     rylen
         2         2         2         2
*CONTROL_TIMESTEP
$#  dtinit    tssfac      isdo    tslimt     dt2ms      lctm     erode     ms1st
       0.0       0.9         0       0.0       0.0         0         0         0
$
$ ==== DATABASE ====
$
*DATABASE_GLSTAT
$#      dt    binary      lcur     ioopt
   1.5E-5         0         0         1
*DATABASE_MATSUM
$#      dt    binary      lcur     ioopt
   1.5E-5         0         0         1
*DATABASE_BINARY_D3PLOT
$#      dt      lcdt      beam     npltc    psetid
   1.5E-4         0         0         0         0
$
$ ==== MATERIALS ====
$
$ Part 1: Aluminum 6061-T6 (units.py mm-ton-s aluminum_6061t6)
*MAT_PIECEWISE_LINEAR_PLASTICITY
$#     mid        ro         e        pr      sigy      etan      fail      tdel
         1   2.7E-9   68900.0      0.33     276.0     600.0       0.0       0.0
$#       c         p      lcss      lcsr        vp
       0.0       0.0         0         0       0.0
$#    eps1      eps2      eps3      eps4      eps5      eps6      eps7      eps8
       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0
$#     es1       es2       es3       es4       es5       es6       es7       es8
       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0
$
$ Part 2: Rigid steel block (units.py mm-ton-s steel_rigid)
$ CMO=1.0 CON1=4 (x,y translations fixed) CON2=7 (all rotations fixed)
*MAT_RIGID
$#     mid        ro         e        pr         n    couple         m     alias
         2   7.85E-9  210000.0       0.3       0.0       0.0       0.0
$#     cmo      con1      con2
       1.0         4         7
$# lco/a1        a2        a3        v1        v2        v3
       0.0       0.0       0.0       0.0       0.0       0.0
$
$ ==== SECTIONS / PARTS ====
$
*SECTION_SHELL
$#   secid    elform      shrf       nip     propt   qr/irid     icomp     setyp
         1        16       1.0         5       1.0         0         0         1
$#      t1        t2        t3        t4      nloc     marea      idof    edgset
       2.0       2.0       2.0       2.0       0.0       0.0       0.0         0
*SECTION_SOLID
$#   secid    elform       aet
         2         1         0
*PART
$# title
aluminum plate 150x150x2mm clamped
$#     pid     secid       mid     eosid      hgid      grav    adpopt      tmid
         1         1         1         0         0         0         0         0
*PART
$# title
rigid steel block 40x40x20mm
$#     pid     secid       mid     eosid      hgid      grav    adpopt      tmid
         2         2         2         0         0         0         0         0
$
$ ==== MESH INCLUDES ====
$
*INCLUDE
mesh_plate.k
*INCLUDE
mesh_block.k
$
$ ==== CONTACT ====
$
*CONTACT_AUTOMATIC_SURFACE_TO_SURFACE
$#   surfa     surfb  surfatyp  surfbtyp   saboxid   sbboxid      sapr      sbpr
         2         1         3         3         0         0         0         0
$#      fs        fd        dc        vc       vdc    penchk        bt        dt
       0.2       0.2       0.0       0.0       0.0         0       0.0       0.0
$#    sfsa      sfsb      sast      sbst     sfsat     sfsbt       fsf       vsf
       1.0       1.0       0.0       0.0       1.0       1.0       1.0       1.0
$#    soft    sofscl    lcidab    maxpar     sbopt     depth     bsort    frcfrq
         1       0.1         0     1.025         2         2         0         1
$
$ ==== BOUNDARY / INITIAL ====
$
$ Plate all four edges (gen_mesh sid=15) fully clamped
*BOUNDARY_SPC_SET
$#    nsid       cid      dofx      dofy      dofz     dofrx     dofry     dofrz
        15         0         1         1         1         1         1         1
$
$ Block initial velocity: vz = -4000 mm/s (4 m/s drop, 5 mm gap)
*INITIAL_VELOCITY_GENERATION
$#      id      styp     omega        vx        vy        vz     ivatn      icid
         2         2       0.0       0.0       0.0   -4000.0         0         0
$#      xc        yc        zc        nx        ny        nz     phase    irigid
       0.0       0.0       0.0       0.0       0.0       0.0         0         0
$
$ ==== LOADS ====
$
$ Gravity: LOAD_BODY_Z positive value = acceleration acting in -z direction
*LOAD_BODY_Z
$#    lcid        sf    lciddr        xc        yc        zc       cid
       901       1.0         0       0.0       0.0       0.0         0
*DEFINE_CURVE
$#    lcid      sidr       sfa       sfo      offa      offo    dattyp     lcint
       901         0       1.0       1.0       0.0       0.0         0         0
$#                a1                  o1
                 0.0              9810.0
                 1.0              9810.0
*END
