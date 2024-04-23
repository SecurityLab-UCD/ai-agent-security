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


def test_encode():
    word1 = "Hello World!"
    assert encode(word1) == "w..."
