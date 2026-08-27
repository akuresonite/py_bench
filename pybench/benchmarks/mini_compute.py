"""Classic CPU-bound kernels: float physics, numeric loops, allocation pressure."""

GROUP = "mini"

_SOLAR_MASS = 4 * 3.141592653589793 ** 2
_DAYS_PER_YEAR = 365.24


def _bodies():
    return [
        # x, y, z, vx, vy, vz, mass
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, _SOLAR_MASS],
        [4.84143144246472090e+00, -1.16032004402742839e+00, -1.03622044471123109e-01,
         1.66007664274403694e-03 * _DAYS_PER_YEAR, 7.69901118419740425e-03 * _DAYS_PER_YEAR,
         -6.90460016972063023e-05 * _DAYS_PER_YEAR, 9.54791938424326609e-04 * _SOLAR_MASS],
        [8.34336671824457987e+00, 4.12479856412430479e+00, -4.03523417114321381e-01,
         -2.76742510726862411e-03 * _DAYS_PER_YEAR, 4.99852801234917238e-03 * _DAYS_PER_YEAR,
         2.30417297573763929e-05 * _DAYS_PER_YEAR, 2.85885980666130812e-04 * _SOLAR_MASS],
        [1.28943695621391310e+01, -1.51111514016986312e+01, -2.23307578892655734e-01,
         2.96460137564761618e-03 * _DAYS_PER_YEAR, 2.37847173959480950e-03 * _DAYS_PER_YEAR,
         -2.96589568540237556e-05 * _DAYS_PER_YEAR, 4.36624404335156298e-05 * _SOLAR_MASS],
        [1.53796971148509165e+01, -2.59193146099879641e+01, 1.79258772950371181e-01,
         2.68067772490389322e-03 * _DAYS_PER_YEAR, 1.62824170038242295e-03 * _DAYS_PER_YEAR,
         -9.51592254519715870e-05 * _DAYS_PER_YEAR, 5.15138902046611451e-05 * _SOLAR_MASS],
    ]


def bench_nbody(loops):
    """N-body gravitational simulation step (float-heavy)."""
    bodies = _bodies()
    dt = 0.01
    pairs = [(a, b) for i, a in enumerate(bodies) for b in bodies[i + 1:]]
    for _ in range(loops):
        for body_a, body_b in pairs:
            dx = body_a[0] - body_b[0]
            dy = body_a[1] - body_b[1]
            dz = body_a[2] - body_b[2]
            distance = (dx * dx + dy * dy + dz * dz) ** 0.5
            magnitude = dt / (distance * distance * distance)
            mass_a = body_a[6] * magnitude
            mass_b = body_b[6] * magnitude
            body_a[3] -= dx * mass_b
            body_a[4] -= dy * mass_b
            body_a[5] -= dz * mass_b
            body_b[3] += dx * mass_a
            body_b[4] += dy * mass_a
            body_b[5] += dz * mass_a
        for body in bodies:
            body[0] += dt * body[3]
            body[1] += dt * body[4]
            body[2] += dt * body[5]
    return bodies[0][0]


def _eval_a(i, j):
    return 1.0 / (((i + j) * (i + j + 1)) // 2 + i + 1)


def bench_spectral_norm(loops):
    """Spectral-norm inner product (tight float loop)."""
    size = 24
    result = 0.0
    for _ in range(loops):
        u = [1.0] * size
        v = [0.0] * size
        for i in range(size):
            total = 0.0
            for j in range(size):
                total += _eval_a(i, j) * u[j]
            v[i] = total
        result = v[0]
    return result


def _make_tree(depth):
    if depth <= 0:
        return (None, None)
    return (_make_tree(depth - 1), _make_tree(depth - 1))


def _check_tree(node):
    left, right = node
    if left is None:
        return 1
    return 1 + _check_tree(left) + _check_tree(right)


def bench_binary_trees(loops):
    """Allocate and walk binary trees (allocation and GC pressure)."""
    total = 0
    for _ in range(loops):
        total += _check_tree(_make_tree(8))
    return total


def _fib(n):
    if n < 2:
        return n
    return _fib(n - 1) + _fib(n - 2)


def bench_fib_recursive(loops):
    """Recursive Fibonacci (call-stack depth)."""
    total = 0
    for _ in range(loops):
        total += _fib(15)
    return total


def bench_matrix_multiply(loops):
    """Nested-list matrix multiply."""
    size = 16
    left = [[float(i + j) for j in range(size)] for i in range(size)]
    right = [[float(i - j) for j in range(size)] for i in range(size)]
    result = None
    for _ in range(loops):
        result = [
            [sum(left[i][k] * right[k][j] for k in range(size)) for j in range(size)]
            for i in range(size)
        ]
    return result[0][0]
