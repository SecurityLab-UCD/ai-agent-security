from hypothesis import given
from hypothesis import strategies as st

from agents.HE_agent import (
    add_encrypted_numbers,
    multiply_encrypted_numbers,
    initialize_ciphertexts,
)
from HE_data.HE_data import serialize_ciphertext, load_ciphertext, load_encoder
from bfv.int_encoder import IntegerEncoder
from bfv.bfv_decryptor import BFVDecryptor


# Default data creation uses a plaintext modulus of 401. This means that the
# numbers that will be encrypted are 0 through 20.
@given(st.integers(min_value=0, max_value=20), st.integers(min_value=0, max_value=20))
def test_add_encrypted_numbers(num1, num2):
    # Setup
    ciphtexts = initialize_ciphertexts("./HE_data")
    params, key_generator = load_encoder("HE_data/HE.txt")
    encoder = IntegerEncoder(params, 10)
    decryptor = BFVDecryptor(params, key_generator.secret_key)

    # Test
    result = add_encrypted_numbers(
        [
            serialize_ciphertext(ciphtexts[num1]),
            serialize_ciphertext(ciphtexts[num2]),
        ]
    )
    assert num1 + num2 == encoder.decode(
        decryptor.decrypt(load_ciphertext(serialization=result))
    )


# Default data creation uses a plaintext modulus of 401. This means that the
# numbers that will be encrypted are 0 through 20.
@given(st.integers(min_value=0, max_value=20), st.integers(min_value=0, max_value=20))
def test_multiply_encrypted_numbers(num1, num2):
    # Setup
    ciphtexts = initialize_ciphertexts("./HE_data")
    params, key_generator = load_encoder("HE_data/HE.txt")
    encoder = IntegerEncoder(params, 10)
    decryptor = BFVDecryptor(params, key_generator.secret_key)

    # Test
    result = multiply_encrypted_numbers(
        [
            serialize_ciphertext(ciphtexts[num1]),
            serialize_ciphertext(ciphtexts[num2]),
        ]
    )
    assert num1 * num2 == encoder.decode(
        decryptor.decrypt(load_ciphertext(serialization=result))
    )
