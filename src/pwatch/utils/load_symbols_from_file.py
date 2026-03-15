import os


def load_symbols_from_file(file_path):
    """
    Reads a file and returns a list of all non-empty lines.

    Args:
        file_path (str): Path to the file to read.

    Returns:
        list: A list of all non-empty lines in the file.
    """
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return []

    with open(file_path, "r") as file:
        return [line.strip() for line in file.readlines() if line.strip()]
