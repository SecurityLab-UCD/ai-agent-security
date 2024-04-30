from encoding_experiment.experiment import generate_random_string
from encoding_experiment.encoder import Encoder


def test_generate_random_strings():
    encoder = Encoder()
    for _ in range(100):
        s = generate_random_string(encoder)
        assert isinstance(s, str)
        assert 1 < len(s) <= 40
        for char in s:
            assert char in encoder.encoding
