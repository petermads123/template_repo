"""This is a test script."""

import pandas as pd
import numpy as np


def test_func(
    input_value: int,
    input_2: int,
    input_3: int,
    input_4: int,
    input_5: int,
    input_6: int,
) -> list:
    """A test function that does nothing."""
    return [input_value, input_2, input_3, input_4, input_5, input_6]


if __name__ == "__main__":
    output = test_func(1, 2, 3, 4, 5, 6)
    print(output)
