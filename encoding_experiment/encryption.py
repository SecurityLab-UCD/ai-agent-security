import fire
import pandas as pd
import numpy as np


def en(x):
    val = int(ord("a") - x)
    if val < 33:
        val = 94 + val
    return chr(val)


# Call encrypt a second time to undo encryption
def encrypt(nums: list[int]) -> str:
    return "".join(map(en, nums))


def encrypt_dataset(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Encrypts the specified columns of the dataframe
    Args:
        df (pd.DataFrame): dataframe to encrypt
        columns (list[str]): list of column names
    Returns:
        pd.DataFrame: dataframe with encrypted columns
    """
    for column in columns:
        df[column] = [encrypt([ord(a) for a in str(x)]) for x in df[column]]
    return df


def main(filename: str, columns: list[str]):
    # df = pd.read_csv("datasets/data.csv")
    # print(df["GY"][:10])
    # encrypted_ls = [encrypt([ord(a) for a in str(x)]) for x in df["GY"]]
    # print(encrypted_ls[:10])
    # print(encrypt_dataset(df, ["GY"])["GY"][:10])
    # print([encrypt([ord(a) for a in str(x)]) for x in encrypted_ls][:10])
    df = pd.read_csv(f"datasets/{filename}")
    new_df = encrypt_dataset(df, columns)
    new_df.to_csv(f"datasets/encrypted_{filename}")


if __name__ == "__main__":
    fire.Fire(main)
