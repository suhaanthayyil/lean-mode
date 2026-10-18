"""Timing prototype for exact certificate checkers (feasibility only)."""
import itertools, time, random
import numpy as np


def golomb_ok(marks):
    d = set()
    for a, b in itertools.combinations(sorted(marks), 2):
        if b - a in d:
            return False
        d.add(b - a)
    return True


def labs_energy(s):
    s = np.asarray(s, dtype=np.int64)
    n = len(s)
    return int(sum(int(np.dot(s[:n - k], s[k:])) ** 2 for k in range(1, n)))


def covering_ok(v, t, blocks):
    # every t-subset of range(v) contained in some block (bitmask)
    masks = [sum(1 << x for x in b) for b in blocks]
    covered = set()
    for m in masks:
        elems = [i for i in range(v) if m >> i & 1]
        for c in itertools.combinations(elems, t):
            covered.add(c)
    from math import comb
    return len(covered) == comb(v, t)


def min_distance_binary(G):
    # G: k x n 0/1 numpy array; enumerate all 2^k - 1 nonzero codewords via Gray code
    k, n = G.shape
    rows = [int(''.join(map(str, r)), 2) for r in G]
    best = n
    cw = 0
    for i in range(1, 1 << k):
        # gray code: flip bit index of lowest set bit of i
        j = (i & -i).bit_length() - 1
        cw ^= rows[j]
        w = cw.bit_count()
        if w < best:
            best = w
    return best


def has_clique(adj, s):
    # simple branch-and-bound clique existence check, adj as list of int bitmasks
    n = len(adj)
    def expand(cand, size):
        if size == s:
            return True
        while cand:
            if size + cand.bit_count() < s:
                return False
            v = cand.bit_length() - 1
            cand &= ~(1 << v)
            if expand(cand & adj[v], size + 1):
                return True
        return False
    return expand((1 << n) - 1, 0)


if __name__ == '__main__':
    t = time.time(); ok = golomb_ok([0, 1, 4, 9, 15, 22, 32, 34]); print('golomb n=8', ok, f'{time.time()-t:.4f}s')
    s = [random.choice([-1, 1]) for _ in range(300)]
    t = time.time(); e = labs_energy(s); print('labs N=300 energy', e, f'{time.time()-t:.4f}s')
    # covering design check: random blocks for v=30,k=10,t=4 (not a real covering)
    v, k, tt = 30, 10, 4
    blocks = [random.sample(range(v), k) for _ in range(400)]
    t = time.time(); ok = covering_ok(v, tt, blocks); print('covering v=30 k=10 t=4 400 blocks', ok, f'{time.time()-t:.3f}s')
    G = np.random.randint(0, 2, size=(20, 60))
    t = time.time(); d = min_distance_binary(G); print('linear code k=20 n=60 dmin', d, f'{time.time()-t:.2f}s')
    # Paley graph p=101 (self-complementary), check K_s for s=6
    p = 101
    qr = {(x * x) % p for x in range(1, p)}
    adj = [sum(1 << j for j in range(p) if j != i and ((i - j) % p) in qr) for i in range(p)]
    for s_ in (5, 6, 7):
        t = time.time(); r = has_clique(adj, s_); print(f'Paley(101) has K_{s_}:', r, f'{time.time()-t:.2f}s')
