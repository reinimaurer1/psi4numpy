"""
A simple to compute the first dipole hyperpolarizability $\beta$
from a restricted HF reference using the $2n+1$ rule from perturbation
theory.

References:
Equations taken from [Karna:1991:487], http://dx.doi.org/10.1002/jcc.540120409
"""

__authors__ = "Eric J. Berquist"
__credits__ = ["Eric J. Berquist"]

__copyright__ = "(c) 2014-2017, The Psi4NumPy Developers"
__license__ = "BSD-3-Clause"
__date__    = "2017-08-26"

import numpy as np
np.set_printoptions(precision=5, linewidth=200, suppress=True)
import psi4
from helper_CPHF import helper_CPHF

# Memory for Psi4 in GB
psi4.set_memory('2 GB')
psi4.core.set_output_file("output.dat", False)

mol = psi4.geometry("""
O
H 1 1.1
H 1 1.1 2 104
symmetry c1
""")

# Set options for CPHF
psi4.set_options({"basis": "aug-cc-pVDZ",
                  "scf_type": "direct",
                  "df_scf_guess": False,
                  "e_convergence": 1e-9,
                  "d_convergence": 1e-9,
                  "cphf_tasks": ['polarizability']})

helper = helper_CPHF(mol, method='direct')
# For the $2n+1$ rule, the quadratic response starting quantities must
# come from linear response.
helper.solve()

moenergies = helper.epsilon
C = np.asarray(helper.C)
Co = helper.Co
Cv = helper.Cv
nbf, norb = C.shape
nocc = Co.shape[1]
x = np.asarray(helper.x)
ncomp = x.shape[0]
integrals_ao = np.asarray([np.asarray(dipole_ao_component)
                           for dipole_ao_component in helper.tmp_dipoles])

# form full MO-basis dipole integrals
integrals_mo = np.empty(shape=(ncomp, norb, norb))
for i in range(ncomp):
    integrals_mo[i, ...] = np.dot(C.T, np.dot(integrals_ao[i, ...], C))

# repack response vectors to [norb, norb]; 1/2 is due to RHF
U = np.zeros_like(integrals_mo)
for i in range(ncomp):
    U[i, :nocc, nocc:] = 0.5 * x[i, ...]
    U[i, nocc:, :nocc] = -0.5 * x[i, ...].T

# form G matrices from perturbation and generalized Fock matrices; do
# one more Fock build for each response vector
jk = psi4.core.JK.build(helper.scf_wfn.basisset())
jk.initialize()
G = np.empty_like(U)
R = psi4.core.Matrix(nbf, nocc)
npR = np.asarray(R)
for i in range(ncomp):
    V = integrals_mo[i, ...]

    # eqn. (III-1b)
    # Note: this simplified handling of the response vector
    # transformation for the Fock build is insufficient for
    # frequency-dependent response. 1/2 is due to RHF
    jk.C_clear()
    L = Co
    npR[...] = np.dot(x[i, ...], np.asarray(Cv).T).T
    jk.C_left_add(L)
    jk.C_right_add(R)
    jk.compute()
    J = 0.5 * np.asarray(jk.J()[0])
    K = 0.5 * np.asarray(jk.K()[0])

    # eqn. (21b)
    F = (C.T).dot(4 * J - K.T - K).dot(C)
    G[i, ...] = V + F

# form epsilon matrices, eqn. (34)
E = G.copy()
omega = 0
for i in range(ncomp):
    eoU = (moenergies[..., np.newaxis] + omega) * U[i, ...]
    Ue = U[i, ...] * moenergies[np.newaxis, ...]
    E[i, ...] += (eoU - Ue)

# Assume some symmetry and calculate only part of the tensor.
# eqn. (VII-4)
hyperpolarizability = np.zeros(shape=(6, 3))
off1 = [0, 1, 2, 0, 0, 1]
off2 = [0, 1, 2, 1, 2, 2]
for r in range(6):
    b = off1[r]
    c = off2[r]
    for a in range(3):
        tl1 = 2 * np.trace(U[a, ...].dot(G[b, ...]).dot(U[c, ...])[:nocc, :nocc])
        tl2 = 2 * np.trace(U[a, ...].dot(G[c, ...]).dot(U[b, ...])[:nocc, :nocc])
        tl3 = 2 * np.trace(U[c, ...].dot(G[a, ...]).dot(U[b, ...])[:nocc, :nocc])
        tr1 = np.trace(U[c, ...].dot(U[b, ...]).dot(E[a, ...])[:nocc, :nocc])
        tr2 = np.trace(U[b, ...].dot(U[c, ...]).dot(E[a, ...])[:nocc, :nocc])
        tr3 = np.trace(U[c, ...].dot(U[a, ...]).dot(E[b, ...])[:nocc, :nocc])
        tr4 = np.trace(U[a, ...].dot(U[c, ...]).dot(E[b, ...])[:nocc, :nocc])
        tr5 = np.trace(U[b, ...].dot(U[a, ...]).dot(E[c, ...])[:nocc, :nocc])
        tr6 = np.trace(U[a, ...].dot(U[b, ...]).dot(E[c, ...])[:nocc, :nocc])
        tl = tl1 + tl2 + tl3
        tr = tr1 + tr2 + tr3 + tr4 + tr5 + tr6
        hyperpolarizability[r, a] = -2 * (tl - tr)


ref_static = np.array([
    [0.00000000,   0.00000000,   0.22845961],
    [0.00000000,   0.00000001, -25.35477024],
    [0.00000000,   0.00000000, -10.84022133],
    [0.00000000,   0.00000000,   0.00000000],
    [0.22845961,   0.00000000,   0.00000000],
    [0.00000000, -25.35477024,   0.00000000]
])

assert np.allclose(ref_static, hyperpolarizability, rtol=0.0, atol=1.0e-3)
print('\nFirst dipole hyperpolarizability (static):')
print(hyperpolarizability)
