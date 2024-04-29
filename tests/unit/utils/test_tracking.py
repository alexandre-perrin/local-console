from local_console.utils.tracking import TrackingVariable


def test_initialization():
    # Test initialization with no initial value
    var = TrackingVariable()
    assert var.value is None, "Initial value should be None if not provided"
    assert var.previous is None, "Previous value should be None initially"

    # Test initialization with an initial value
    var_with_init = TrackingVariable(10)
    assert var_with_init.value == 10, "Initial value should be as provided"
    assert var_with_init.previous is None, "Previous value should be None initially"


def test_value_update():
    var = TrackingVariable(100)
    assert var.value == 100, "Current value should be set to 100"
    assert (
        var.previous is None
    ), "Previous value should still be None after first update"

    # Update value again to test previous value tracking
    var.value = 200
    assert var.value == 200, "Current value should now be 200"
    assert var.previous == 100, "Previous value should now be 100"


def test_previous_value_tracking():
    var = TrackingVariable()
    values = ["hello", "world", "test"]
    previous_value = None

    for value in values:
        var.value = value
        assert var.value == value, f"Current value should be {value}"
        assert (
            var.previous == previous_value
        ), f"Previous value should be {previous_value}"
        previous_value = value
