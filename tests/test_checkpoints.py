"""
Tests for checkpoint support

It check:
- restore local vars seamless.
- generate the same random numbers after restoring.

"""
import numpy as np
import numpy.random as random  # use this lib instead python random one
from os import sys, path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from resume import Checkpoint


def test_checkpoint():
    "Test basic checkpoint"
    chp = Checkpoint(clean=True)

    foo = 'bar'
    chp.save()

    filename = chp.filename
    del chp

    chp2 = Checkpoint(filename)
    foo = 'buzz'
    chp2.restore()

    assert foo == 'bar'


def test_radom_seed():
    "Check numpy random recovery state"
    chp = Checkpoint(clean=True)
    seq_1 = np.arange(100)
    np.random.shuffle(seq_1)
    foo = random.random()
    chp.save()  # force save checkpoint and random initial state
    del chp

    chp = Checkpoint()
    seq_2 = np.arange(100)
    np.random.shuffle(seq_2)
    bar = random.random()

    assert np.allclose(seq_1, seq_2)
    assert foo == bar


def compute_primes(n=10):
    "compute n next primes"
    chp = Checkpoint()
    # define initial state of the algorithm
    i = 2
    primes = [i]
    candidate = primes[-1]

    # restore previous work (if any)
    chp.restore()  # note that 'n' preserve the current calling value

    # continue from last time (or initial state)
    while n > 0:
        candidate += 1
        for p in primes:
            if not candidate % p:
                break
        else:
            primes.append(candidate)
            n -= 1

    # dump current state to disk. Next call will continue from here
    chp.save()
    return primes


def test_continue_work():
    N = 5
    primes_1 = compute_primes()
    primes_2 = compute_primes(n=N)

    assert len(primes_1) > 0
    assert len(primes_2) == len(primes_1) + N



if __name__ == '__main__':
    test_checkpoint()
    test_radom_seed()
    test_continue_work()
