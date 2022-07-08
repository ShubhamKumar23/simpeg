import unittest
import SimPEG.electromagnetics.frequency_domain as fdem
from SimPEG import maps
import numpy as np
from scipy.constants import mu_0
from geoana.em.fdem import (
    MagneticDipoleHalfSpace,
    vertical_magnetic_field_horizontal_loop as mag_field,
)
import empymod

class EM1D_FD_FwdProblemTests(unittest.TestCase):
    def setUp(self):

        nearthick = np.logspace(-1, 1, 5)
        deepthick = np.logspace(1, 2, 10)
        thicknesses = np.r_[nearthick, deepthick]
        topo = np.r_[0.0, 0.0, 100.0]

        offset = 10.0
        src_location = np.array([[0.0, 0.0, 100.0 + 1e-5]])
        rx_location = np.array([[offset, 0.0, 100.0 + 1e-5]])
        frequencies = np.logspace(-1, 5, 61)

        # Receiver list
        receiver_list = []
        receiver_list.append(
            fdem.receivers.PointMagneticFieldSecondary(
                rx_location, orientation="z", component="real"
            )
        )
        receiver_list.append(
            fdem.receivers.PointMagneticFieldSecondary(
                rx_location, orientation="z", component="imag"
            )
        )
        receiver_list.append(
            fdem.receivers.PointMagneticFieldSecondary(
                rx_location, orientation="x", component="real"
            )
        )
        receiver_list.append(
            fdem.receivers.PointMagneticFieldSecondary(
                rx_location, orientation="x", component="imag"
            )
        )

        source_list = []
        for ii, frequency in enumerate(frequencies):
            src = fdem.sources.MagDipole(
                receiver_list, frequency, src_location, orientation="z"
            )
            source_list.append(src)

        # Survey
        survey = fdem.Survey(source_list)

        sigma = 1.0
        chi = 0.0
        tau = 1e-3
        eta = 2e-1
        c = 1.0

        self.topo = topo
        self.survey = survey
        self.sigma = sigma
        self.tau = tau
        self.eta = eta
        self.c = c
        self.chi = chi
        self.offset = offset
        self.frequencies = frequencies
        self.thicknesses = thicknesses
        self.nlayers = len(thicknesses) + 1

    def test_EM1DFDfwd_VMD_Halfspace(self):

        sigma_map = maps.ExpMap(nP=1)
        sim = fdem.Simulation1DLayered(
            survey=self.survey, sigmaMap=sigma_map, topo=self.topo
        )

        m_1D = np.array([np.log(self.sigma)])
        H = sim.dpred(m_1D)

        dip = MagneticDipoleHalfSpace(
            location=np.r_[0.0, 0.0, 0.0],
            orientation="z",
            frequency=self.frequencies,
            sigma=self.sigma,
            quasistatic=True,
        )
        H_analytic = np.squeeze(dip.magnetic_field(np.array([[self.offset, 0.0]])))
        Hx = H_analytic[:, 0]
        Hz = H_analytic[:, 2]
        H_analytic = np.c_[Hz.real, Hz.imag, Hx.real, Hx.imag].reshape(-1)

        err = np.linalg.norm(H - H_analytic) / np.linalg.norm(H_analytic)
        self.assertLess(err, 1e-5)

    def test_EM1DFDfwd_VMD_RealCond(self):

        sigma_map = maps.ExpMap(nP=self.nlayers)
        sim = fdem.Simulation1DLayered(
            survey=self.survey,
            thicknesses=self.thicknesses,
            sigmaMap=sigma_map,
            topo=self.topo,
        )

        m_1D = np.log(np.ones(self.nlayers) * self.sigma)
        H = sim.dpred(m_1D)

        dip = MagneticDipoleHalfSpace(
            location=np.r_[0.0, 0.0, 0.0],
            orientation="z",
            frequency=self.frequencies,
            sigma=self.sigma,
            quasistatic=True,
        )
        H_analytic = np.squeeze(dip.magnetic_field(np.array([[self.offset, 0.0]])))
        Hx = H_analytic[:, 0]
        Hz = H_analytic[:, 2]
        H_analytic = np.c_[Hz.real, Hz.imag, Hx.real, Hx.imag].reshape(-1)

        err = np.linalg.norm(H - H_analytic) / np.linalg.norm(H_analytic)
        self.assertLess(err, 1e-5)

    def test_EM1DFDfwd_VMD_ComplexCond(self):

        sigma_map = maps.IdentityMap(nP=self.nlayers)
        mu = mu_0 * np.ones(self.nlayers)
        tau = self.tau * np.ones(self.nlayers)
        c = self.c * np.ones(self.nlayers)
        eta = self.eta * np.ones(self.nlayers)

        sim = fdem.Simulation1DLayered(
            survey=self.survey,
            thicknesses=self.thicknesses,
            topo=self.topo,
            sigmaMap=sigma_map,
            eta=eta,
            tau=tau,
            c=c,
            mu=mu,
        )

        m_1D = self.sigma * np.ones(self.nlayers)
        H = sim.dpred(m_1D)

        sigmas = sim.compute_complex_sigma(self.frequencies)[0, :]

        H_analytic = []
        for sigma, frequency in zip(sigmas, self.frequencies):
            dip = MagneticDipoleHalfSpace(
                location=np.r_[0.0, 0.0, 0.0],
                orientation="z",
                frequency=[frequency],
                sigma=sigma,
                quasistatic=True,
            )
            hv = np.squeeze(dip.magnetic_field(np.array([[self.offset, 0.0]])))
            hx = hv[0]
            hz = hv[2]
            H_analytic.append([hz.real, hz.imag, hx.real, hx.imag])
        H_analytic = np.hstack(H_analytic)
        err = np.linalg.norm(H - H_analytic) / np.linalg.norm(H_analytic)
        self.assertTrue(err < 1e-5)

    def test_EM1DFDfwd_HMD_RealCond(self):

        src_location = np.array([0.0, 0.0, 100.0 + 1e-5])
        rx_location = np.array([self.offset, 0.0, 100.0 + 1e-5])
        frequencies = np.logspace(-1, 5, 61)

        # Receiver list
        receiver_list = []
        receiver_list.append(
            fdem.receivers.PointMagneticFieldSecondary(
                rx_location, orientation="z", component="real"
            )
        )
        receiver_list.append(
            fdem.receivers.PointMagneticFieldSecondary(
                rx_location, orientation="z", component="imag"
            )
        )

        source_list = []
        for ii, frequency in enumerate(frequencies):
            src = fdem.sources.MagDipole(
                receiver_list, frequency, src_location, orientation="x"
            )
            source_list.append(src)

        survey = fdem.Survey(source_list)

        sigma_map = maps.ExpMap(nP=self.nlayers)
        sim = fdem.Simulation1DLayered(
            survey=survey,
            thicknesses=self.thicknesses,
            sigmaMap=sigma_map,
            topo=self.topo,
        )

        m_1D = np.log(np.ones(self.nlayers) * self.sigma)
        Hz = sim.dpred(m_1D)

        dip = MagneticDipoleHalfSpace(
            location=np.r_[0.0, 0.0, 0.0],
            orientation="x",
            frequency=self.frequencies,
            sigma=self.sigma,
            quasistatic=True,
        )
        H_analytic = np.squeeze(dip.magnetic_field(np.array([[self.offset, 0.0]])))[
            :, 2
        ]
        H_analytic = np.c_[H_analytic.real, H_analytic.imag].reshape(-1)

        err = np.linalg.norm(Hz - H_analytic) / np.linalg.norm(H_analytic)
        self.assertLess(err, 1e-5)

    def test_EM1DFDfwd_CircularLoop_RealCond(self):

        src_location = np.array([0.0, 0.0, 100.0 + 1e-5])
        rx_location = np.array([0.0, 0.0, 100.0 + 1e-5])
        frequencies = np.logspace(-1, 5, 61)

        # Receiver list
        receiver_list = []
        receiver_list.append(
            fdem.receivers.PointMagneticFieldSecondary(
                rx_location, orientation="z", component="real"
            )
        )
        receiver_list.append(
            fdem.receivers.PointMagneticFieldSecondary(
                rx_location, orientation="z", component="imag"
            )
        )

        source_list = []
        for ii, frequency in enumerate(frequencies):
            src = fdem.sources.CircularLoop(
                receiver_list, frequency, src_location, radius=5.0
            )
            source_list.append(src)

        survey = fdem.Survey(source_list)

        sigma_map = maps.ExpMap(nP=self.nlayers)
        sim = fdem.Simulation1DLayered(
            survey=survey,
            thicknesses=self.thicknesses,
            sigmaMap=sigma_map,
            topo=self.topo,
        )

        m_1D = np.log(np.ones(self.nlayers) * self.sigma)
        Hz = sim.dpred(m_1D)

        hz = mag_field(self.frequencies, sigma=self.sigma, radius=5.0)
        H_analytic = np.c_[hz.real, hz.imag].reshape(-1)

        err = np.linalg.norm(Hz - H_analytic) / np.linalg.norm(H_analytic)
        self.assertLess(err, 1e-5)

    def test_EM1DFDfwd_CircularLoop_ComplexCond(self):

        src_location = np.array([0.0, 0.0, 100.0 + 1e-5])
        rx_location = np.array([0.0, 0.0, 100.0 + 1e-5])
        frequencies = np.logspace(-1, 5, 61)

        # Receiver list
        receiver_list = []
        receiver_list.append(
            fdem.receivers.PointMagneticFieldSecondary(
                rx_location, orientation="z", component="real"
            )
        )
        receiver_list.append(
            fdem.receivers.PointMagneticFieldSecondary(
                rx_location, orientation="z", component="imag"
            )
        )

        source_list = []
        for ii, frequency in enumerate(frequencies):
            src = fdem.sources.CircularLoop(
                receiver_list, frequency, src_location, radius=5.0
            )
            source_list.append(src)

        survey = fdem.Survey(source_list)

        sigma_map = maps.IdentityMap(nP=self.nlayers)
        mu = mu_0 * np.ones(self.nlayers)
        tau = self.tau * np.ones(self.nlayers)
        c = self.c * np.ones(self.nlayers)
        eta = self.eta * np.ones(self.nlayers)

        sim = fdem.Simulation1DLayered(
            survey=survey,
            thicknesses=self.thicknesses,
            topo=self.topo,
            sigmaMap=sigma_map,
            eta=eta,
            tau=tau,
            c=c,
            mu=mu,
        )

        m_1D = self.sigma * np.ones(self.nlayers)
        Hz = sim.dpred(m_1D)

        sigma_colecole = sim.compute_complex_sigma(self.frequencies)[0, :]
        hz = mag_field(self.frequencies, sigma=sigma_colecole, radius=5.0)
        H_analytic = np.c_[hz.real, hz.imag].reshape(-1)

        err = np.linalg.norm(Hz - H_analytic) / np.linalg.norm(H_analytic)

        self.assertLess(err, 1e-5)


class EM1D_FD_PiecewiseWireLoopTest(unittest.TestCase):

    def setUp(self):

        x_path = np.array([-2, -2, 2, 2, -2])
        y_path = np.array([-1, 1, 1, -1, -1])
        frequencies = np.logspace(0, 4)

        wire_paths= np.c_[x_path, y_path, np.ones(5) * 0.5]
        source_list = []
        receiver_list = []
        receiver_location = np.array([9.28, 0., 0.45])
        receiver_orientation = "z"
        receiver_list.append(
            fdem.receivers.PointMagneticFieldSecondary(
                receiver_location, orientation=receiver_orientation,
                data_type='field', component="both"
            )
        )

        for freq in frequencies:
            source = fdem.sources.PiecewiseWireLoop(receiver_list, wire_paths=wire_paths, frequency=freq)
            source_list.append(source)

        # Survey
        survey = fdem.Survey(source_list)
        background_conductivity = 1e-1
        layer_conductivity = 1e0
        sigma = np.ones(3) * background_conductivity
        sigma[1] = layer_conductivity
        thicknesses = np.array([20., 40.])

        self.frequencies = frequencies
        self.survey = survey
        self.sigma = sigma
        self.thicknesses = thicknesses

    def test_with_empymod(self):

        sigma_map = maps.ExpMap(nP=1)
        sim = fdem.Simulation1DLayered(
            survey=self.survey,
            sigmaMap=maps.IdentityMap(nP=3),
            thicknesses=self.thicknesses
        )
        H = sim.dpred(self.sigma)
        def solution(res):
            EM_left = empymod.model.bipole(
                src=[-2, -2, -1, 1, -0.5, -0.5],  # El. bipole source; half of one side.
                rec=[9.28, 0, -0.45, 0, 90],         # Receiver at the origin, vertical.
                depth=np.r_[0, np.cumsum(sim.thicknesses)],        # Depth-model, adding air-interface.
                res=res,         # Provided resistivity model, adding air.
                freqtime=self.frequencies,                # Required frequencies.
                mrec=True,                    # It is an el. source, but a magn. rec.
                strength=1,                   # To account for 1 side of square loop.
                srcpts=3,                     # Approx. the finite dip. with 3 points.
                htarg={'dlf': 'key_101_2009'},  # Short filter, so fast.
                verb=0
            )

            EM_right = empymod.model.bipole(
                src=[2, 2, 1, -1, -0.5, -0.5],  # El. bipole source; half of one side.
                rec=[9.28, 0, -0.45, 0, 90],         # Receiver at the origin, vertical.
                depth=np.r_[0, np.cumsum(sim.thicknesses)],        # Depth-model, adding air-interface.
                res=res,         # Provided resistivity model, adding air.
                freqtime=self.frequencies,                # Required frequencies.
                mrec=True,                    # It is an el. source, but a magn. rec.
                strength=1,                   # To account for 1 side of square loop.
                srcpts=3,                     # Approx. the finite dip. with 3 points.
                htarg={'dlf': 'key_101_2009'},  # Short filter, so fast.
                verb=0
            )

            EM_top = empymod.model.bipole(
                src=[-2, 2, 1, 1, -0.5, -0.5],  # El. bipole source; half of one side.
                rec=[9.28, 0, -0.45, 0, 90],         # Receiver at the origin, vertical.
                depth=np.r_[0, np.cumsum(sim.thicknesses)],        # Depth-model, adding air-interface.
                res=res,         # Provided resistivity model, adding air.
                freqtime=self.frequencies,                # Required frequencies.
                mrec=True,                    # It is an el. source, but a magn. rec.
                strength=2,                   # To account for 2 sides of square loop.
                srcpts=3,                     # Approx. the finite dip. with 3 points.
                htarg={'dlf': 'key_101_2009'},  # Short filter, so fast.
                verb=0
            )
            EM = EM_left+EM_right+EM_top
            return EM
        res = np.r_[2e14, 1./sim.sigma]
        resBG = np.ones(4) * 2e14
        EM = solution(res)-solution(resBG)
        H_analytic = np.c_[EM.real, EM.imag].reshape(-1)

        err = np.linalg.norm(H - H_analytic) / np.linalg.norm(H_analytic)
        self.assertLess(err, 1e-4)

if __name__ == "__main__":
    unittest.main()
