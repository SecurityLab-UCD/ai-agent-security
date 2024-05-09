from hypothesis import given
from hypothesis import strategies as st

from encoding_experiment.encoder import Encoder


def test_en():
    encoder = Encoder()
    for char in encoder.encoding:
        new_char = encoder.en(char)
        assert new_char in encoder.encoding
        assert encoder.en(new_char) == char


@given(
    st.text(
        alphabet=[str(num) for num in range(10)]
        + [chr(x) for x in range(ord("a"), ord("a") + 26)]
        + [chr(x) for x in range(ord("A"), ord("A") + 26)],
        min_size=1,
    )
)
def test_encode(s):
    encoder = Encoder()
    assert encoder.encode(s) != s
    assert encoder.encode(encoder.encode(s)) == s
