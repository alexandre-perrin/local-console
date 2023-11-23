from pathlib import Path

import hypothesis.strategies as st


@st.composite
def path_strategy(draw):
    path_str = draw(
        st.text(
            min_size=1,
            max_size=5,
            alphabet=st.characters(
                blacklist_characters="/\0",  # Avoid / and null character
                whitelist_categories=(
                    "Lu",
                    "Ll",
                    "Nd",
                    "Pc",
                    "Zs",
                ),  # Unicode categories for letters, digits, punctuation, and spaces
            ),
        )
    )
    return Path(path_str)
