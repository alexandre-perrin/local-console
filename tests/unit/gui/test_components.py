from kivy.clock import Clock
from local_console.gui.view.common.components import CodeInputCustom


def test_code_input_custom():
    code_input = CodeInputCustom()

    assert tuple(code_input.cursor) == (0, 0)
    code_input.text = "my input text"
    assert tuple(code_input.cursor) != (0, 0)
    Clock.tick()
    assert tuple(code_input.cursor) == (0, 0)
