import pytest
import numpy as np


def test_get_dpf_fields_by_beam_disp(beam_solution):
    fc, metadata = beam_solution._get_dpf_fields("DISPLACEMENT")
    assert metadata.components == [0, 1, 2]
    assert metadata.result_location == "Nodal"
    assert metadata.result_location == "Nodal"
    assert metadata.scope.size == 2566
    assert fc[-1].shape == (2566, 3)
    assert fc[-1].data[0][0] == pytest.approx(np.float64(2.364956612938758))
    assert fc[-1].data[0][1] == pytest.approx(np.float64(-6.560847444522356))
    assert fc[-1].data[0][2] == pytest.approx(np.float64(-0.48826001002984915))

    