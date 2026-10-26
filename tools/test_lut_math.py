"""Meaningful synthetic checks for CUBE channel order and interpolation."""
import numpy as np

from inspect_official_luts import parse_cube, trilinear


def identity_cube(size):
    lines = [f'LUT_3D_SIZE {size}']
    for b in range(size):
        for g in range(size):
            for r in range(size):
                lines.append(f'{r/(size-1):.9f} {g/(size-1):.9f} {b/(size-1):.9f}')
    return ('\n'.join(lines) + '\n').encode('ascii')


def main():
    rng = np.random.default_rng(20261024)
    samples = np.concatenate((rng.random((1000, 3)),
                              np.zeros((1, 3)), np.ones((1, 3)),
                              np.eye(3)))
    for size in (33, 65):
        _, cube = parse_cube(identity_cube(size))
        actual = trilinear(cube, samples)
        maximum = float(np.max(np.abs(actual - samples)))
        assert maximum < 1e-7, (size, maximum)
        print(f'{size}^3 identity cube: max absolute error {maximum:.2e}')


if __name__ == '__main__':
    main()
