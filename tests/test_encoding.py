from hypothesis import given
from hypothesis import strategies as st

from encoding_experiment.encoding import en, encode


def test_en():
    mappings = set()
    for i in range(33, 127):  # Printable ASCII range
        code = en(i)
        assert code not in mappings
        mappings.add(code)
        assert 33 <= ord(code) <= 126

    assert len(mappings) == 127 - 33
    assert ord(en(33)) == 64
    assert ord(en(70)) == 121
    assert ord(en(ord(en(70)))) == 70


# Using only ASCII 33 to 126 because LLMs use whitespace as separator, so can't
# use whitespace as part of ciphertext
@given(st.text(alphabet=[chr(x) for x in range(33, 127)], min_size=1))
def test_encode(s):
    assert encode(s) != s
    assert encode(encode(s)) == s
