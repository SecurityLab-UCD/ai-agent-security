def en(x: int):
    # Based on ROT13 letter substitution cipher
    # Uses ASCII values instead of alphabetical ordering to include special
    # characters and numbers
    assert 33 <= x <= 126
    val = int(ord("a") - x)
    if val < 33:
        val = 94 + val
    return chr(val)


# Call encode a second time to undo encoding
def encode(message: str) -> str:
    return "".join(map(en, [ord(char) for char in message]))
