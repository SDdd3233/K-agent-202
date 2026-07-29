*KEYWORD
*TITLE
SPH water column (D25x50mm) impact on clamped aluminum plate, 100 m/s, mm-kg-ms
$
$ ============================= CONTROL =============================
$
*CONTROL_TERMINATION
$#  endtim    endcyc     dtmin    endeng    endmas     nosol
       1.5         0       0.0       0.0  1.000E+8         0
*CONTROL_ENERGY
$#    hgen      rwen    slnten     rylen
         2         2         2         2
*CONTROL_TIMESTEP
$#  dtinit    tssfac      isdo    tslimt     dt2ms      lctm     erode     ms1st
       0.0       0.9         0       0.0       0.0         0         0         0
*CONTROL_SPH
$#    ncbs     boxid        dt      idim   nmneigh      form     start      maxv
         1         01.0000E+20         3       150         0       0.01.0000E+15
$
$ ============================= DATABASE =============================
$
*DATABASE_GLSTAT
$#      dt    binary      lcur     ioopt
    0.0075         0         0         1
*DATABASE_MATSUM
$#      dt    binary      lcur     ioopt
    0.0075         0         0         1
*DATABASE_NODOUT
$#      dt    binary      lcur     ioopt   option1   option2
    0.0075         0         0         1       0.0         0
*DATABASE_HISTORY_NODE
$#     id1       id2       id3       id4       id5       id6       id7       id8
  100480         0         0         0         0         0         0         0
*DATABASE_BINARY_D3PLOT
$#      dt      lcdt      beam     npltc    psetid
     0.075         0         0         0         0
$
$ ============================= MATERIALS =============================
$
$ --- Part 1: Aluminum 6061-T6 (units.py mm-kg-ms) ---
*MAT_PIECEWISE_LINEAR_PLASTICITY
$#     mid        ro         e        pr      sigy      etan      fail      tdel
         1 2.7000E-6      68.9      0.33     0.276       0.6       0.0       0.0
$#       c         p      lcss      lcsr        vp
       0.0       0.0         0         0       0.0
$#    eps1      eps2      eps3      eps4      eps5      eps6      eps7      eps8
       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0
$#     es1       es2       es3       es4       es5       es6       es7       es8
       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0
$
$ --- Part 2: Water = MAT_NULL + EOS_GRUNEISEN (units.py mm-kg-ms) ---
*MAT_NULL
$#     mid        ro        pc        mu     terod     cerod        ym        pr
         2 9.9800E-7 -1.000E-5 1.0000E-9       0.0       0.0       0.0       0.0
*EOS_GRUNEISEN
$#   eosid         c        s1        s2        s3    gamma0         a        e0
         2    1480.0     1.979       0.0       0.0      0.11       3.0       0.0
$#      v0
       1.0
$
$ ============================= SECTIONS / PARTS =============================
$
*SECTION_SHELL
$#   secid    elform      shrf       nip     propt   qr/irid     icomp     setyp
         1        16    0.8333         5         1         0         0         1
$#      t1        t2        t3        t4      nloc     marea      idof    edgset
       3.0       3.0       3.0       3.0       0.0       0.0       0.0         0
*SECTION_SPH
$#   secid      cslh      hmin      hmax    sphini     death     start   sphkern
         2       1.2       0.2       2.0       0.01.0000E+20       0.0         0
*PART
$# title
aluminum plate 150x150x3mm clamped
$#     pid     secid       mid     eosid      hgid      grav    adpopt      tmid
         1         1         1         0         0         0         0         0
*PART
$# title
SPH water column D25x50mm
$#     pid     secid       mid     eosid      hgid      grav    adpopt      tmid
         2         2         2         2         0         0         0         0
$
$ ============================= MESH INCLUDES =============================
$
*INCLUDE
mesh_plate.k
*INCLUDE
mesh_sph.k
$
$ ============================= CONTACT =============================
$
$ SPH particles (part 2, type=3 part id) as SURFA nodes vs plate (part 1) SURFB
*CONTACT_AUTOMATIC_NODES_TO_SURFACE
$#   surfa     surfb  surfatyp  surfbtyp   saboxid   sbboxid      sapr      sbpr
         2         1         3         3         0         0         0         0
$#      fs        fd        dc        vc       vdc    penchk        bt        dt
       0.0       0.0       0.0       0.0       0.0         0       0.0       0.0
$#    sfsa      sfsb      sast      sbst     sfsat     sfsbt       fsf       vsf
       1.0       1.0       0.0       0.0       1.0       1.0       1.0       1.0
$#    soft    sofscl    lcidab    maxpar     sbopt     depth     bsort    frcfrq
         1       0.1         0     1.025         2         2         0         1
$
$ ============================= BOUNDARY / INITIAL =============================
$
$ Clamp all four plate edges (node set 15 from gen_mesh plate, sid0=10 +5)
*BOUNDARY_SPC_SET
$#    nsid       cid      dofx      dofy      dofz     dofrx     dofry     dofrz
        15         0         1         1         1         1         1         1
$
$ Water column initial velocity vz = -100 mm/ms (= -100 m/s)
*INITIAL_VELOCITY_GENERATION
$#      id      styp     omega        vx        vy        vz     ivatn      icid
         2         2       0.0       0.0       0.0    -100.0         0         0
$#      xc        yc        zc        nx        ny        nz     phase    irigid
       0.0       0.0       0.0       0.0       0.0       0.0         0         0
$
$ ============================= LOADS =============================
$
$ (none - impact driven by initial velocity)
$
*END
