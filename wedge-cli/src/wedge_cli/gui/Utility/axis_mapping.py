from typing import Optional
from typing import Union

# Type of ROI units: raw pixel coordinates
PixelROI = tuple[tuple[int, int], tuple[int, int]]
# Type of ROI units: normalized (from 0 to 1) with
# respect to the pixel matrix dimensions
UnitROI = tuple[tuple[float, float], tuple[float, float]]

# Fundamental constant: IMX500 pixel matrix dimensions
SENSOR_SIZE = 4056, 3040

# Default Unit ROI
DEFAULT_ROI: UnitROI = ((0, 0), (1, 1))


def pixel_roi_from_normals(normal_roi: Optional[UnitROI]) -> PixelROI:
    """
    This function maps a normalized ROI (in units from 0 to 1)
    to pixel size coordinates in the IMX500 matrix.
    """
    sensor_size = SENSOR_SIZE

    if normal_roi is None:
        return (0, 0), (sensor_size[0], sensor_size[1])

    n_start, n_size = normal_roi

    h_offset = int(denormalize_in_set(n_start[0], (0, sensor_size[0] - 1)))
    # Whereas our ROI's start is its lower-left corner,
    # the camera's ROI start is its upper-left one.
    v_offset = int(
        denormalize_in_set(1 - (n_start[1] + n_size[1]), (0, sensor_size[1] - 1))
    )
    h_size = int(denormalize_in_set(n_size[0], (0, sensor_size[0])))
    v_size = int(denormalize_in_set(n_size[1], (0, sensor_size[1])))

    return (h_offset, v_offset), (h_size, v_size)


# Typing for the number mapping functions below
Number = Union[int, float]
NumberSet = tuple[Number, Number]


def as_normal_in_set(value: Number, set_: NumberSet) -> Number:
    return (value - set_[0]) / (set_[1] - set_[0])


def denormalize_in_set(value: Number, set_: NumberSet) -> Number:
    return set_[0] + (value * (set_[1] - set_[0]))


def delta(set_: NumberSet) -> Number:
    return set_[1] - set_[0]
