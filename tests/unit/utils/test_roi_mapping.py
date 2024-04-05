from wedge_cli.gui.utils.axis_mapping import as_normal_in_set
from wedge_cli.gui.utils.axis_mapping import DEFAULT_ROI
from wedge_cli.gui.utils.axis_mapping import pixel_roi_from_normals
from wedge_cli.gui.utils.axis_mapping import SENSOR_SIZE


def test_normalizing():
    low = 1
    high = 3
    assert as_normal_in_set(2, (low, high)) == 0.5
    assert as_normal_in_set(low, (low, high)) == 0
    assert as_normal_in_set(high, (low, high)) == 1
    assert as_normal_in_set(0, (low, high)) == -0.5
    assert as_normal_in_set(4, (low, high)) == 1.5


def test_normals():
    low = 0.2
    high = 0.7
    assert as_normal_in_set(0.1, (low, high)) < 0
    assert 0.9 < as_normal_in_set(0.65, (low, high)) < 1
    assert 0 < as_normal_in_set(0.21, (low, high)) < 0.1


def test_unit_roi_denormalization():
    denorm = pixel_roi_from_normals(DEFAULT_ROI)
    assert denorm == ((0, 0), (SENSOR_SIZE[0], SENSOR_SIZE[1]))


def test_reference_point_denormalization():
    unit_v_offset = 0.1
    roi = ((0.5, unit_v_offset), (0.5, 0.5))
    (h_offset, v_offset), (h_size, v_size) = pixel_roi_from_normals(roi)

    assert h_size == SENSOR_SIZE[0] / 2
    assert v_size == SENSOR_SIZE[1] / 2
    assert h_offset == (SENSOR_SIZE[0] / 2 - 1)
    assert v_offset == (4 * SENSOR_SIZE[1] / 10 - 1)
