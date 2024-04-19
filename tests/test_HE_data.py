from bfv.int_encoder import IntegerEncoder
from bfv.bfv_decryptor import BFVDecryptor
from bfv.bfv_encryptor import BFVEncryptor
from bfv.bfv_key_generator import BFVKeyGenerator
from bfv.bfv_parameters import BFVParameters
from util.polynomial import Polynomial
from util.ciphertext import Ciphertext

from hypothesis import given
from hypothesis import strategies as st

import os

from HE_data.HE_data import (
    serialize_encoder,
    save_encoder,
    load_encoder,
    check_load_relin_key,
    serialize_ciphertext,
    load_ciphertext,
    serialize_polynomial,
)


@given(st.integers(min_value=0, max_value=400))
def test_serialize_polynomial(num):
    # Setup
    degree = 8
    plain_modulus = 401
    ciph_modulus = 8000000000000
    params = BFVParameters(
        poly_degree=degree, plain_modulus=plain_modulus, ciph_modulus=ciph_modulus
    )
    key_generator = BFVKeyGenerator(params)
    encoder = IntegerEncoder(params, 10)
    encryptor = BFVEncryptor(params, key_generator.public_key)

    # Test
    plaintext = encoder.encode(num)
    ciphtext = encryptor.encrypt(plaintext)
    serialized_c0 = serialize_polynomial(ciphtext.c0)
    sc0_elements = serialized_c0.split(" ")
    serialized_c1 = serialize_polynomial(ciphtext.c1)
    sc1_elements = serialized_c1.split(" ")
    assert (
        len(sc0_elements) == int(sc0_elements[0]) + 1
        and len(sc1_elements) == int(sc1_elements[0]) + 1
    )
    new_c0 = Polynomial(int(sc0_elements[0]), [int(x) for x in sc0_elements[1:]])
    new_c1 = Polynomial(int(sc1_elements[0]), [int(x) for x in sc1_elements[1:]])
    new_ciphtext = Ciphertext(new_c0, new_c1)
    assert str(ciphtext) == str(new_ciphtext)


@given(st.integers(min_value=0, max_value=400))
def test_ciphertext_functions(num):
    # Setup
    degree = 8
    plain_modulus = 401
    ciph_modulus = 8000000000000
    params = BFVParameters(
        poly_degree=degree, plain_modulus=plain_modulus, ciph_modulus=ciph_modulus
    )
    key_generator = BFVKeyGenerator(params)
    encoder = IntegerEncoder(params, 10)
    encryptor = BFVEncryptor(params, key_generator.public_key)
    decryptor = BFVDecryptor(params, key_generator.secret_key)

    # Test
    plaintext = encoder.encode(num)
    ciphtext = encryptor.encrypt(plaintext)
    serialization = serialize_ciphertext(ciphtext)
    deserialized = load_ciphertext(serialization=serialization)
    assert str(deserialized) == str(ciphtext)
    assert encoder.decode(decryptor.decrypt(deserialized)) == num


def test_encoder_functions():
    # Setup
    degree = 8
    plain_modulus = 401
    ciph_modulus = 8000000000000
    params = BFVParameters(
        poly_degree=degree, plain_modulus=plain_modulus, ciph_modulus=ciph_modulus
    )
    key_generator = BFVKeyGenerator(params)
    serialization = serialize_encoder(params, key_generator)
    # assert check_load_relin_key()
    save_encoder("temp_encoder.txt", serialization)
    loaded_params, loaded_key_generator = load_encoder("temp_encoder.txt")
    assert loaded_params.ciph_modulus == params.ciph_modulus
    assert loaded_params.plain_modulus == params.plain_modulus
    assert loaded_params.poly_degree == params.poly_degree
    assert loaded_params.scaling_factor == params.scaling_factor
    assert serialize_polynomial(key_generator.public_key.p0) == serialize_polynomial(
        loaded_key_generator.public_key.p0
    ) and serialize_polynomial(key_generator.public_key.p1) == serialize_polynomial(
        loaded_key_generator.public_key.p1
    )
    assert serialize_polynomial(key_generator.secret_key.s) == serialize_polynomial(
        loaded_key_generator.secret_key.s
    )
    assert check_load_relin_key(key_generator.relin_key, loaded_key_generator.relin_key)

    # Cleanup
    os.remove("temp_encoder.txt")
