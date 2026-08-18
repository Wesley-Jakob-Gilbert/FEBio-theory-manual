# B.1 Standard Data Fields

FEBio Studio defines the following list of standard data fields that can be added to a post model.

<a id="tab3-1"></a>

<div markdown="1" style="display: flex; justify-content: center;">

| **Name** | **Description** |
|---|---|
| Initial Position | The initial nodal position of the model |
| Aspect ratio | The element's aspect ratio |
| 1-Princ curvature | The first principal curvature of the surface |
| 2-Princ curvature | The second principal curvature of the surface |
| Gaussian curvature | The Gaussian curvature of the surface |
| Mean curvature | The mean curvature |
| RMS curvature | The Root-Mean-Square curvature |
| Princ Curvature difference | The difference of the principal curvatures |
| Congruency | The congruency |
| 1-Princ curvature vector | The first principal curvature vector |
| 2-Princ curvature vector | The second principal curvature vector |

</div>

The following data fields require a “displacement” field.

<a id="tab3-1-1"></a>

<div markdown="1" style="display: flex; justify-content: center;">

| **Name** | **Description** |
|---|---|
| Position | The current nodal position of the deformed model |
| Deformation gradient | The deformation gradient of the deformation map |
| Infinitesimal strain | The infinitesimal (engineering) strain tensor |
| Lagrange strain | The Green-Lagrange strain tensor |
| Right Cauchy-Green | The right Cauchy-Green deformation tensor |
| Right stretch | The right stretch tensor |
| Biot strain | The Biot strain tensor |
| Right Hencky | The Right Hencky tensor |
| Left Cauchy-Green | The left Cauchy-Green strain tensor |
| Left stretch | The left stretch tensor |
| Left Hencky | The left Hencky tensr |
| Almansi strain | The Almansi strain tensor |
| Volume | The element's (approximate) volume |
| Volume ratio | The ratio of current over initial element volume |
| Volume strain | The volumetric strain |

</div>

The following data fields require a “stress” field.

<a id="tab3-1-2"></a>

<div markdown="1" style="display: flex; justify-content: center;">

| **Name** | **Description** |
|---|---|
| pressure | Calculated from the “stress” field: $p=-tr\boldsymbol{\sigma}$ |

</div>
