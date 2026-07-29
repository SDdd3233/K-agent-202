*KEYWORD
*TITLE
penetration: 4340 steel cylinder 800 m/s perforating 2024-T3 aluminum plate (cm-g-us)
$
$ ==== CONTROL ====
$
*CONTROL_TERMINATION
$#  endtim    endcyc     dtmin    endeng    endmas     nosol
      30.0         0       0.0       0.01.000000E8         0
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
      0.15         0         0         1
*DATABASE_MATSUM
$#      dt    binary      lcur     ioopt
      0.15         0         0         1
*DATABASE_BINARY_D3PLOT
$#      dt      lcdt      beam     npltc    psetid
       1.5         0         0         0         0
$
$ ==== MATERIALS ====
$
$ Part 1: Aluminum 2024-T3 (units.py cm-g-us aluminum_2024t3_jc)
$ VP=1 viscoplastic rate form; JC damage D1-D5; stress unit Mbar
*MAT_JOHNSON_COOK
$#     mid        ro         g         e        pr       dtf        vp    rateop
         1      2.77     0.276      0.73      0.33       0.0       1.0       0.0
$#       a         b         n         c         m        tm        tr      eps0
   0.00369   0.00684      0.73    0.0083       1.7     775.0     293.0    1.0E-6
$#      cp        pc     spall        it        d1        d2        d3        d4
   8.75E-6       0.0       2.0       0.0      0.13      0.13      -1.5     0.011
$#      d5                erod     efmin    numint
       0.0                 0.0    1.0E-6         0
*EOS_GRUNEISEN
$#   eosid         c        s1        s2        s3    gamma0         a        e0
         1    0.5328     1.338       0.0       0.0       2.0      0.48       0.0
$#      v0              lcid
       1.0                 0
$ Backstop erosion for distorted target elements:
$ EFFEPS < 0 -> |EFFEPS| = effective PLASTIC strain at failure (manual Vol II p.2-82)
*MAT_ADD_EROSION
$#     mid      excl    mxpres     mneps    effeps    voleps    numfip       ncs
         1       0.0       0.0       0.0      -1.5       0.0       1.0       1.0
$#  mnpres     sigp1     sigvm     mxeps     epssh     sigth   impulse    failtm
       0.0       0.0       0.0       0.0       0.0       0.0       0.0       0.0
$
$ Part 2: AISI 4340 steel projectile (units.py cm-g-us steel_4340_jc)
*MAT_JOHNSON_COOK
$#     mid        ro         g         e        pr       dtf        vp    rateop
         2      7.83      0.77       2.0      0.29       0.0       1.0       0.0
$#       a         b         n         c         m        tm        tr      eps0
   0.00792    0.0051      0.26     0.014      1.03    1793.0     293.0    1.0E-6
$#      cp        pc     spall        it        d1        d2        d3        d4
   4.77E-6       0.0       2.0       0.0      0.05      3.44     -2.12     0.002
$#      d5                erod     efmin    numint
      0.61                 0.0    1.0E-6         0
*EOS_GRUNEISEN
$#   eosid         c        s1        s2        s3    gamma0         a        e0
         2    0.4569      1.49       0.0       0.0      2.17      0.46       0.0
$#      v0              lcid
       1.0                 0
$
$ ==== SECTIONS / PARTS ====
$
*SECTION_SOLID
$#   secid    elform       aet
         1         1         0
*SECTION_SOLID
$#   secid    elform       aet
         2         1         0
$ Flanagan-Belytschko stiffness hourglass control (IHQ=4), QM=0.03
$ (swept IHQ 2-6 / QM 0.01-1.0; this combo keeps HG/IE below 10%)
*HOURGLASS
$#    hgid       ihq        qm       ibq        q1        q2    qb/vdc        qw
         1         4      0.03         0       1.5      0.06       0.0       0.0
*PART
$# title
aluminum 2024-T3 target plate 4x4x0.6 cm
$#     pid     secid       mid     eosid      hgid      grav    adpopt      tmid
         1         1         1         1         1         0         0         0
*PART
$# title
4340 steel projectile r0.4 h1.2 cm
$#     pid     secid       mid     eosid      hgid      grav    adpopt      tmid
         2         2         2         2         1         0         0         0
$
$ ==== MESH INCLUDES ====
$
*INCLUDE
mesh_target.k
*INCLUDE
mesh_projectile.k
$
$ ==== CONTACT ====
$
$ Eroding contact: SURFA=projectile part 2, SURFB=target part 1 (both by part id)
$ Card 4 (ISYM/EROSOP/IADJ) is mandatory for ERODING contacts and precedes opt. card A
*CONTACT_ERODING_SURFACE_TO_SURFACE
$#   surfa     surfb  surfatyp  surfbtyp   saboxid   sbboxid      sapr      sbpr
         2         1         3         3         0         0         0         0
$#      fs        fd        dc        vc       vdc    penchk        bt        dt
       0.1       0.1       0.0       0.0       0.0         0       0.0       0.0
$#    sfsa      sfsb      sast      sbst     sfsat     sfsbt       fsf       vsf
       1.0       1.0       0.0       0.0       1.0       1.0       1.0       1.0
$#    isym    erosop      iadj
         0         1         1
$#    soft    sofscl    lcidab    maxpar     sbopt     depth     bsort    frcfrq
         1       0.1         0     1.025         2         2         0         1
$
$ ==== BOUNDARY / INITIAL ====
$
$ Target four lateral faces fully clamped (gen_mesh box sid0=10: 11=xmin,12=xmax,13=ymin,14=ymax)
*BOUNDARY_SPC_SET
$#    nsid       cid      dofx      dofy      dofz     dofrx     dofry     dofrz
        11         0         1         1         1         1         1         1
*BOUNDARY_SPC_SET
$#    nsid       cid      dofx      dofy      dofz     dofrx     dofry     dofrz
        12         0         1         1         1         1         1         1
*BOUNDARY_SPC_SET
$#    nsid       cid      dofx      dofy      dofz     dofrx     dofry     dofrz
        13         0         1         1         1         1         1         1
*BOUNDARY_SPC_SET
$#    nsid       cid      dofx      dofy      dofz     dofrx     dofry     dofrz
        14         0         1         1         1         1         1         1
$
$ Projectile initial velocity: vz = -0.08 cm/us (= 800 m/s downward)
*INITIAL_VELOCITY_GENERATION
$#      id      styp     omega        vx        vy        vz     ivatn      icid
         2         2       0.0       0.0       0.0     -0.08         0         0
$#      xc        yc        zc        nx        ny        nz     phase    irigid
       0.0       0.0       0.0       0.0       0.0       0.0         0         0
$
$ ==== LOADS ====
$
$ (none - free flight impact)
$
*END
