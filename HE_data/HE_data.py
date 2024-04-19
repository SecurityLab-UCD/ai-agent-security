from bfv.int_encoder import IntegerEncoder
from bfv.bfv_decryptor import BFVDecryptor
from bfv.bfv_encryptor import BFVEncryptor
from bfv.bfv_key_generator import BFVKeyGenerator
from bfv.bfv_parameters import BFVParameters
from util.polynomial import Polynomial
from util.ciphertext import Ciphertext


def serialize_polynomial(polynomial: Polynomial) -> str:
    """
    Serializes the ring degree and coefficients of a polynomial into a string

    Format:
    <ring_degree> <coeff_1> ... <coeff_n>
    """
    serialization = str(polynomial.ring_degree)
    for coeff in polynomial.coeffs:
        serialization += f" {coeff}"
    return serialization


def serialize_encoder(params: BFVParameters, key_generator: BFVKeyGenerator) -> str:
    """
    Serializes params and key generator of an encryptor into a string.

    Note: The tuple elements of the relin_key keys are comma-separated.\n
    Format:\n
    <params.poly_degree> <params.plain_modulus> <params.ciph_modulus>\n
    <public_key.p0>|<public_key.p1>\n
    <secret_key.s>\n
    <relin_key.base>-<relin_key.keys[0]>|...|<relin_key.keys[len(relin_key.keys) - 1]>
    """
    # Serialize params
    serialization = (
        f"{params.poly_degree} {params.plain_modulus} {params.ciph_modulus}\n"
    )
    # Serialize public key
    serialization += f"{serialize_polynomial(key_generator.public_key.p0)}|{serialize_polynomial(key_generator.public_key.p1)}\n"
    # Serialize secret key
    serialization += serialize_polynomial(key_generator.secret_key.s)
    serialization += "\n"

    # Serialize relin key
    serialization += str(key_generator.relin_key.base) + "-"
    # List of tuples of polynomials
    for tup in key_generator.relin_key.keys:
        for polynomial in tup:
            serialization += serialize_polynomial(polynomial) + ","
        serialization = serialization.strip(",")
        serialization += "|"
    return serialization.strip("|")


def serialize_ciphertext(ciphertext: Ciphertext) -> str:
    """
    Serializes a ciphertext into a string representation.

    Format:
    <ciphertext.c0>w<ciphertext.c1>
    """
    return (
        serialize_polynomial(ciphertext.c0) + "w" + serialize_polynomial(ciphertext.c1)
    )


def load_ciphertext(serialization: str = None, filename: str = None) -> Ciphertext:
    """
    Recreates ciphertext from serialization.\n
    If filename is provided, prioritizes loading from file.
    """
    if filename:
        with open(filename, "r") as f:
            lines = f.readlines()
        tokens = [x.split(" ") for x in lines[0].split("w")]
    else:
        tokens = [x.split(" ") for x in serialization.split("w")]
    c0 = Polynomial(int(tokens[0][0]), [int(x) for x in tokens[0][1:]])
    c1 = Polynomial(int(tokens[1][0]), [int(x) for x in tokens[1][1:]])
    return Ciphertext(c0, c1)


def save_encoder(filename: str, serialized_encoder: str):
    """Saves an encoder's serialization to a file."""
    with open(filename, "w") as f:
        f.write(serialized_encoder)


def load_encoder(filename: str):
    """
    Recreates encoder from serialization stored in a file.

    Note: The tuple elements of the relin_key keys are comma-separated.\n
    Format:\n
    <params.poly_degree> <params.plain_modulus> <params.ciph_modulus>\n
    <public_key.p0>|<public_key.p1>\n
    <secret_key.s>\n
    <relin_key.base>-<relin_key.keys[0]>|...|<relin_key.keys[len(relin_key.keys) - 1]>
    """
    with open(filename, "r") as f:
        lines = f.readlines()
    # Parse serializations
    params_serialization = lines[0].split(" ")
    pk_serialization = [x.split(" ") for x in lines[1].split("|")]
    sk_serialization = lines[2].split(" ")
    rk_serialization = lines[3].split("-")
    # Recreate params object
    params = BFVParameters(
        poly_degree=int(params_serialization[0]),
        plain_modulus=int(params_serialization[1]),
        ciph_modulus=int(params_serialization[2]),
    )
    # Recreate key generator by setting all necessary member variables
    key_generator = BFVKeyGenerator(params)
    key_generator.public_key.p0.ring_degree = int(pk_serialization[0][0])
    key_generator.public_key.p0.coeffs = [int(x) for x in pk_serialization[0][1:]]
    key_generator.public_key.p1.ring_degree = int(pk_serialization[1][0])
    key_generator.public_key.p1.coeffs = [int(x) for x in pk_serialization[1][1:]]

    key_generator.secret_key.s.ring_degree = int(sk_serialization[0])
    key_generator.secret_key.s.coeffs = [int(x) for x in sk_serialization[1:]]

    key_generator.relin_key.base = int(rk_serialization[0])
    tuples = rk_serialization[1].split("|")
    key_generator.relin_key.keys = []
    for tup in tuples:
        cur_tuple = []
        polynomials = tup.split(",")
        for polynomial in polynomials:
            poly_params = polynomial.split(" ")
            cur_tuple.append(
                Polynomial(int(poly_params[0]), [int(x) for x in poly_params[1:]])
            )
        key_generator.relin_key.keys.append(tuple(cur_tuple))

    return params, key_generator


def check_load_relin_key(k1, k2):
    if k1.base != k2.base or len(k1.keys) != len(k2.keys):
        return False
    for i in range(len(k1.keys)):
        if len(k1.keys[i]) != len(k2.keys[i]):
            return False
        for j in range(len(k1.keys[i])):
            if serialize_polynomial(k1.keys[i][j]) != serialize_polynomial(
                k2.keys[i][j]
            ):
                return False
    return True


def main():
    # Setup of encryptor
    degree = 8
    # Increase plain modulus to work with larger numbers
    # Must be a prime congruent to 1 modulo 16
    plain_modulus = 401  # Can only handle numbers in interval [0, 400]
    ciph_modulus = 8000000000000
    params = BFVParameters(
        poly_degree=degree, plain_modulus=plain_modulus, ciph_modulus=ciph_modulus
    )
    key_generator = BFVKeyGenerator(params)
    public_key = key_generator.public_key
    secret_key = key_generator.secret_key
    relin_key = key_generator.relin_key
    # Save encryptor parameters to file
    save_encoder("HE.txt", serialize_encoder(params, key_generator))
    # Test loading encryptor back in
    loaded_params, loaded_key_generator = load_encoder("HE.txt")
    assert loaded_params.scaling_factor == params.scaling_factor
    assert str(loaded_key_generator.public_key) == str(public_key)
    assert str(loaded_key_generator.secret_key) == str(secret_key)
    assert check_load_relin_key(relin_key, loaded_key_generator.relin_key)

    encoder = IntegerEncoder(params, 10)
    encryptor = BFVEncryptor(params, public_key)
    decryptor = BFVDecryptor(params, secret_key)

    # Generate and save numbers
    for num in range(20):
        plaintext = encoder.encode(num)
        ciphtext = encryptor.encrypt(plaintext)
        with open(f"{num}.txt", "w") as f:
            f.write(serialize_ciphertext(ciphtext))
        # Verify save works
        loaded_ciphertext = load_ciphertext(filename=f"{num}.txt")
        assert encoder.decode(decryptor.decrypt(loaded_ciphertext)) == num


if __name__ == "__main__":
    main()