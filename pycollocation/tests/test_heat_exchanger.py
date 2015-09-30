import unittest

import numpy as np

from .. problems import bvp
from .. import solvers


class HeatExchanger(unittest.TestCase):

    @staticmethod
    def bcs_lower(A, T1, T2, T10, **params):
        return [T1 - T10]

    @staticmethod
    def bcs_upper(A, T1, T2, T2Ahx, **params):
        return [T2 - T2Ahx]

    @staticmethod
    def q(A, T1, T2, U):
        return (T1 - T2) * U

    @classmethod
    def create_mesh(cls, basis_kwargs, num, problem):
        ts = np.linspace(*basis_kwargs['domain'], num=num)
        T1s = np.repeat(0.5 * (problem.params['T10'] + problem.params['T2Ahx']), num)
        return ts, T1s, T1s

    @classmethod
    def fit_initial_polys(cls, basis_kwargs, num, problem):
        As, T1s, T2s = cls.create_mesh(basis_kwargs, num, problem)
        basis_poly = getattr(np.polynomial, basis_kwargs['kind'])
        T1_poly = basis_poly.fit(As, T1s, basis_kwargs['degree'],
                                 basis_kwargs['domain'])
        T2_poly = basis_poly.fit(As, T2s, basis_kwargs['degree'],
                                 basis_kwargs['domain'])
        return T1_poly, T2_poly

    @classmethod
    def rhs(cls, A, T1, T2, U, **params):
        return [-cls.q(A, T1, T2, U), -0.5 * cls.q(A, T1, T2, U)]

    def setUp(self):
        """Set up a Solow model to solve."""
        params = {'T10': 130, 'T2Ahx': 70, 'U': 1.0}
        self.bvp = bvp.TwoPointBVP(self.bcs_lower, self.bcs_upper, 1, 2,
                                   params, self.rhs)

    def _test_polynomial_collocation(self, basis_kwargs):
        """Test collocation solver using Chebyshev polynomials for basis."""
        nodes = solvers.PolynomialSolver.collocation_nodes(**basis_kwargs)
        initial_polys = self.fit_initial_polys(basis_kwargs, 1000, self.bvp)
        capital_poly, consumption_poly = initial_polys
        initial_coefs = np.hstack([capital_poly.coef, consumption_poly.coef])

        solution = solvers.PolynomialSolver.solve(basis_kwargs,
                                                  initial_coefs,
                                                  nodes,
                                                  self.bvp)

        # check that solver terminated successfully
        self.assertTrue(solution.result.success, msg="Solver failed!")

        # compute the residuals
        ts, _, _ = self.create_mesh(basis_kwargs, 1000, self.bvp)
        normed_residuals = solution.normalize_residuals(ts)

        # check that residuals are close to zero on average
        mesg = "Normed residuals:\n{}\n\nDictionary of model params: {}"
        self.assertTrue(np.mean(normed_residuals) < 1e-6,
                        msg=mesg.format(normed_residuals, self.bvp.params))

    def test_chebyshev_collocation(self):
        """Test collocation solver using Chebyshev polynomials for basis."""
        basis_kwargs = {'kind': 'Chebyshev', 'degree': 15, 'domain': (0, 5)}
        self._test_polynomial_collocation(basis_kwargs)

    def test_legendre_collocation(self):
        """Test collocation solver using Legendre polynomials for basis."""
        basis_kwargs = {'kind': 'Legendre', 'degree': 15, 'domain': (0, 5)}
        self._test_polynomial_collocation(basis_kwargs)

    def test_standard_collocation(self):
        """Test collocation solver using Standard polynomials for basis."""
        basis_kwargs = {'kind': 'Polynomial', 'degree': 5, 'domain': (0, 5)}
        self._test_polynomial_collocation(basis_kwargs)