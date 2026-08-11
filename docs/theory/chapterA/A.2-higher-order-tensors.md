# A.2 Higher Order Tensors

Note that $\mathbf{a}\cdot\mathbf{T}\cdot\mathbf{b}=\mathbf{a}\otimes\mathbf{b}:\mathbf{T}=\mathbf{T}:\mathbf{a}\otimes\mathbf{b}$, and $\mathbf{a}\otimes\mathbf{b}:\mathbf{c}\otimes\mathbf{d}=\left(\mathbf{a}\cdot\mathbf{c}\right)\left(\mathbf{b}\cdot\mathbf{d}\right)$. Similarly, $\left(\mathbf{a}\otimes\mathbf{b}\right)\cdot\left(\mathbf{c}\otimes\mathbf{d}\right)=\left(\mathbf{b}\cdot\mathbf{c}\right)\mathbf{a}\otimes\mathbf{d}$. We will be using generalizations of these relations when examining higher order tensors.

## Third-Order Tensors

A third-order tensor $\mathbb{T}$ is a linear transformation that transforms any vector $\mathbf{a}$ into a second-order tensor $\mathbf{S}$,

\[ \begin{equation} \boxed{\mathbb{T}\cdot\mathbf{a}=\mathbf{S}}\label{eq62-1} \end{equation} \]

In general, the dyadic product of three vectors is a third-order tensor which satisfies

\[ \begin{equation} \boxed{\left(\mathbf{a}\otimes\mathbf{b}\otimes\mathbf{c}\right)\cdot\left(\alpha\mathbf{u}+\beta\mathbf{v}\right)=\left(\alpha\mathbf{c}\cdot\mathbf{u}+\beta\mathbf{c}\cdot\mathbf{v}\right)\left(\mathbf{a}\otimes\mathbf{b}\right)}\quad\forall\,\mathbf{u},\mathbf{v}\,.\label{eq62b} \end{equation} \]

Any third-order tensor $\mathbb{T}$ can be expressed in terms of its Cartesian components $T_{ijk}$ as

\[ \begin{equation} \boxed{\mathbb{T}=T_{ijk}\mathbf{e}_{i}\otimes\mathbf{e}_{j}\otimes\mathbf{e}_{k}}\label{eq62d} \end{equation} \]

and the Cartesian components of a third-order tensor may be evaluated from

\[ \begin{equation} \boxed{T_{ijk}=\mathbf{e}_{i}\cdot\left(\mathbb{T}\cdot\mathbf{e}_{k}\right)\cdot\mathbf{e}_{j}}\label{eq62c} \end{equation} \]

It follows from Eqs.\eqref{eq62b} and \eqref{eq62d} that

\[ \mathbb{T}\cdot\mathbf{a}=T_{ijk}\left(\mathbf{e}_{i}\otimes\mathbf{e}_{j}\otimes\mathbf{e}_{k}\right)\cdot\mathbf{a}=T_{ijk}\left(\mathbf{e}_{k}\cdot\mathbf{a}\right)\left(\mathbf{e}_{i}\otimes\mathbf{e}_{j}\right)=T_{ijk}a_{k}\left(\mathbf{e}_{i}\otimes\mathbf{e}_{j}\right)=\mathbf{S}=S_{ij}\left(\mathbf{e}_{i}\otimes\mathbf{e}_{j}\right) \]

so that the indicial form of eq.\eqref{eq62-1} is

\[ \begin{equation} T_{ijk}a_{k}=S_{ij}\label{eq62e} \end{equation} \]

In particular,

\[ \begin{equation} \mathbb{T}\cdot\mathbf{e}_{k}=T_{ijk}\mathbf{e}_{i}\otimes\mathbf{e}_{j}\label{eq62f} \end{equation} \]

The double dot product of a third-order tensor with a second-order tensor is defined by

\[ \boxed{\left(\mathbf{a}\otimes\mathbf{b}\otimes\mathbf{c}\right):\left(\mathbf{d}\otimes\mathbf{e}\right)=\left(\mathbf{b}\cdot\mathbf{d}\right)\left(\mathbf{c}\cdot\mathbf{e}\right)\mathbf{a}}\,, \]

and

\[ \boxed{\left(\mathbf{a}\otimes\mathbf{b}\right):\left(\mathbf{c}\otimes\mathbf{d}\otimes\mathbf{e}\right)=\left(\mathbf{a}\cdot\mathbf{c}\right)\left(\mathbf{b}\cdot\mathbf{d}\right)\mathbf{e}}\,. \]

Therefore, the double dot product of a third-order tensor with a second-order tensor is a vector given by

\[ \begin{equation} \mathbb{T}:\left(\mathbf{a}\otimes\mathbf{b}\right)=\left(\mathbb{T}\cdot\mathbf{b}\right)\cdot\mathbf{a}\,.\label{eq63f} \end{equation} \]

Proof: Using $\mathbb{T}\cdot\mathbf{b}=T_{ijk}b_{k}\left(\mathbf{e}_{i}\otimes\mathbf{e}_{j}\right)$, we find that $\left(\mathbb{T}\cdot\mathbf{b}\right)\cdot\mathbf{a}=T_{ijk}b_{k}\left(\mathbf{e}_{i}\otimes\mathbf{e}_{j}\right)\cdot\mathbf{a}=T_{ijk}b_{k}\left(\mathbf{a}\cdot\mathbf{e}_{j}\right)\mathbf{e}_{i}=T_{ijk}a_{j}b_{k}\mathbf{e}_{i}$. Similarly, $\mathbb{T}:\left(\mathbf{a}\otimes\mathbf{b}\right)=T_{ijk}\left(\mathbf{e}_{i}\otimes\mathbf{e}_{j}\otimes\mathbf{e}_{k}\right):\left(\mathbf{a}\otimes\mathbf{b}\right)=T_{ijk}\left(\mathbf{e}_{j}\cdot\mathbf{a}\right)\left(\mathbf{e}_{k}\cdot\mathbf{b}\right)\mathbf{e}_{i}=T_{ijk}a_{j}b_{k}\mathbf{e}_{i}$, thus completing the proof.

For any second-order tensor $\mathbf{S}$, it also follows that

\[ \mathbb{T}:\mathbf{S}=T_{ijk}S_{jk}\mathbf{e}_{i}\,. \]

**Example 1.** If we introduce the notation $\mathbb{E}$ as the third-order (pseudo-)tensor of Cartesian components $\varepsilon_{ijk}$, the relation between an antisymmetric tensor and its dual vector can also be written as

\[ \begin{equation} \boxed{\boldsymbol{\Omega}=-\mathbb{E}\cdot\boldsymbol{\omega}}\label{eq26b} \end{equation} \]

Similarly,

\[ \begin{equation} \boxed{\boldsymbol{\omega}=-\frac{1}{2}\mathbb{E}:\boldsymbol{\Omega}}\label{eq27b} \end{equation} \]

## Fourth-Order Tensors {: #subsec:Fourth-Order-Tensors }

The dyadic product of four vectors is a fourth-order tensor $\mathbf{a}\otimes\mathbf{b}\otimes\mathbf{c}\otimes\mathbf{d}$, defined as

\[ \begin{equation} \left(\mathbf{a}\otimes\mathbf{b}\otimes\mathbf{c}\otimes\mathbf{d}\right)\cdot\mathbf{v}=\left(\mathbf{d}\cdot\mathbf{v}\right)\left(\mathbf{a}\otimes\mathbf{b}\otimes\mathbf{c}\right)\label{eq:63g} \end{equation} \]

The Cartesian components of a fourth-order tensor $\mathcal{T}$ are given by

\[ \begin{equation} T_{ijkl}=\left(\mathbf{e}_{i}\otimes\mathbf{e}_{j}\right):\mathcal{T}:\left(\mathbf{e}_{k}\otimes\mathbf{e}_{l}\right)\label{eq:63h} \end{equation} \]

such that

\[ \begin{equation} \mathcal{T}=T_{ijkl}\mathbf{e}_{i}\otimes\mathbf{e}_{j}\otimes\mathbf{e}_{k}\otimes\mathbf{e}_{l}\label{eq:63i} \end{equation} \]

Therefore, a fourth-order tensor transforms a vector into a third-order tensor,

\[ \begin{equation} \mathcal{T}\cdot\mathbf{a}=\left(T_{ijkl}\mathbf{e}_{i}\otimes\mathbf{e}_{j}\otimes\mathbf{e}_{k}\otimes\mathbf{e}_{l}\right)\cdot\mathbf{a}=T_{ijkl}a_{l}\mathbf{e}_{i}\otimes\mathbf{e}_{j}\otimes\mathbf{e}_{k}\equiv S_{ijk}\mathbf{e}_{i}\otimes\mathbf{e}_{j}\otimes\mathbf{e}_{k}=\mathbb{S}\label{eq:63j} \end{equation} \]

The double dot product of a fourth-order tensor with a second-order tensor is a second-order tensor defined as

\[ \begin{equation} \boxed{\mathcal{T}:\left(\mathbf{a}\otimes\mathbf{b}\right)=\left(\mathcal{T}\cdot\mathbf{b}\right)\cdot\mathbf{a}}\label{eq:63k} \end{equation} \]

from which it can be shown that

\[ \begin{equation} \mathcal{T}:\mathbf{S}=T_{ijmn}S_{mn}\mathbf{e}_{i}\otimes\mathbf{e}_{j}\label{eq:63l} \end{equation} \]

or equivalently, $\left(\mathcal{T}:\mathbf{S}\right)_{ij}=T_{ijkl}S_{kl}$.

A fourth-order tensor can exhibit three levels of symmetry, which can be represented using Cartesian components as

\[ \begin{equation} \begin{aligned}T_{ijkl} & =T_{jikl} & \text{left minor symmetry}\\ T_{ijkl} & =T_{ijlk} & \text{right minor symmetry}\\ T_{ijkl} & =T_{klij} & \text{major symmetry} \end{aligned} \label{eq:tens4-symmetries} \end{equation} \]

Whereas a general fourth-order tensor may have 81 distinct components, a tensor with one minor symmetry has 54 distinct components; a tensor with both minor symmetries has 36 distinct components; and a tensor with minor and major symmetries has 21distinct components. We may represent the major symmetry of $\mathcal{T}$ as $\mathcal{T}=\mathcal{T}^{T}$, whose Cartesian representation is provided above. It follows from this definition that

\[ \begin{aligned}\mathbf{S}:\mathcal{T} & =\mathcal{T}^{T}:\mathbf{S}\\ \left(\mathbf{S}:\mathcal{T}\right)_{ij} & =S_{kl}T_{klij}=T_{ijkl}^{T}S_{kl} \end{aligned} \]

## Additional Tensor Products

Earlier we saw that the dyadic product of vectors can produce tensors. Similarly, we can define dyadic products of tensors which produce higher-order tensors. In particular, the following products of second-order tensors $\mathbf{A}$ and $\mathbf{B}$ produce fouth-order tensors, satisfying

\[ \begin{equation} \begin{aligned}\left(\mathbf{A}\otimes\mathbf{B}\right):\mathbf{S} & =\left(\mathbf{B}:\mathbf{S}\right)\mathbf{A}\\ \left(\mathbf{A}\oslash\mathbf{B}\right):\mathbf{S} & =\mathbf{A}\cdot\mathbf{S}\cdot\mathbf{B}^{T}\\ \left(\mathbf{A}\obslash\mathbf{B}\right):\mathbf{S} & =\mathbf{A}\cdot\mathbf{S}^{T}\cdot\mathbf{B}^{T}\\ \left(\mathbf{A}\odot\mathbf{B}\right):\mathbf{S} & =\frac{1}{2}\left(\mathbf{A}\oslash\mathbf{B}+\mathbf{A}\obslash\mathbf{B}\right):\mathbf{S}=\frac{1}{2}\left(\mathbf{A}\cdot\mathbf{S}\cdot\mathbf{B}^{T}+\mathbf{A}\cdot\mathbf{S}^{T}\cdot\mathbf{B}^{T}\right) \end{aligned} \label{eq:tensor-products} \end{equation} \]

where $\mathbf{S}$ is any second-order tensor. Using Cartesian components of tensors, the indicial form of these tensor products are

\[ \begin{equation} \begin{aligned}\left(\mathbf{A}\otimes\mathbf{B}\right)_{ijkl} & =A_{ij}B_{kl}\\ \left(\mathbf{A}\oslash\mathbf{B}\right)_{ijkl} & =A_{ik}B_{jl}\\ \left(\mathbf{A}\obslash\mathbf{B}\right)_{ijkl} & =A_{il}B_{jk}\\ \left(\mathbf{A}\odot\mathbf{B}\right)_{ijkl} & =\frac{1}{2}\left(A_{ik}B_{jl}+A_{il}B_{jk}\right) \end{aligned} \label{eq:tensor-products-Cartesian} \end{equation} \]
