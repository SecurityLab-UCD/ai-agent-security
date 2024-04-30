class Encoder:
    def __init__(
        self,
        encoding: list[str] = [str(num) for num in range(10)]
        + [chr(x) for x in range(ord("a"), ord("a") + 26)]
        + [chr(x) for x in range(ord("A"), ord("A") + 26)],
    ):
        """
        Args:
            encoding (list[str]): List containing alphabet of encoder. Indices are used for rotation.
        """
        self.encoding = encoding

    def en(self, char: str) -> str:
        """
        Encoding based on ROT13 letter substitution cipher. Uses ASCII values instead of alphabetical ordering to include other characters.
        This is meant to be a helper function for encode. Please call encode when trying to encode a string.

            Args:
                char (str): Character to encode. Should be a singular character in the encoder's alphabet.

            Returns:
                (str): Encoded char.
        """
        if char not in self.encoding:
            raise ValueError(f"Character {char} is not in the encoder's alphabet.")
        return self.encoding[
            (self.encoding.index(char) + len(self.encoding) // 2) % len(self.encoding)
        ]

    def encode(self, message: str) -> str:
        """
        Encodes a string of characters. Characters must be in the encoder's alphabet.
        Calling this function twice on the same string will return the original string.

            Args:
                message (str): String to encode.

            Returns:
                (str): Encoded string
        """
        return "".join(map(self.en, [char for char in message]))
