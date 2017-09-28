# resume module

This module provide a support for saving and restoring the same interpreter
state in different executions saving the locals and some internal status
like random state in a checkpoint file.

The integration as been designed to be seamless:

1. just create a checkpoint at the begging of the function
2. set the 1st run time variables
3. call restore() before the evolutionary process
4. performs any computation cycles
5. call sync() or save() meanwhile as your convenience to store current state.

If the code is interrupted for an reason, the next execution will:

1. use the same checkpoint definition to locate the saved state.
2. define the same variables as initial placeholders
3. calling restore() will load these variables from disk
4. the computation cycles continue from last saved state.
5. the same sync() or save() will keep your step forward work save.

**Notes**:

- the name of the checkpoint is auto-magically selected from the function name.
- sync() will save state only if the elapsed time from last save if bigger
  than a rate (passed in constructor)
- save() always dump state into disk
- use numpy.random module instead python random module due the lack of seed
  recovery in python library.
  On the contrary numpy provide a get_state() and set_state() for this propose.


## Abstract

In situations where we are developing an application or library that will be use to create long computation reports or results, we want to recover the progress of the computation in case of failure or environmental changes.

The integration with existing code must be seamless, hiding all the details to the user. Actually there is only 3 code lines you should insert in your existing code.

1. instantiate a checkpoint, usually at the begining of the function of code.
2. select the restoration point in case of re-run
3. decide when save the internal state within loop calculations.

## Show me an example

Let' say that we have this code for compute prime numbers:

```python
def compute_primes(n=10):
    "compute n 1st primes"
    # define initial state of the algorithm
    i = 2
    primes = [i]
    candidate = primes[-1]

    while n > 0:
        candidate += 1
        for p in primes:
            if not candidate % p:
                break
        else:
            primes.append(candidate)
            n -= 1
    return primes
```

We can reuse previous computation using checkpoint support.

The changes in the code are:

```python
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
```

and some code for testing

```python
>>> N=5
>>> primes_1 = compute_primes()
[2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]
>>> primes_2 = compute_primes(n=N)
[2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53]
>>> assert len(primes_1) > 0
>>> assert len(primes_2) == len(primes_1) + N
```

## Notes

- The checkpoint is stored in compressed pickle format
- Checkpoints preserve numpy random state to guarantee the same results as if the process will not be interrupted
- Checkpoints are stored in '.checkpoints/' hidden folder by default.
- checkpoints will be discarded if las update is beyond of CACHE_EXPIRE by default.
- checkpoints store all basic types and numpy types by default.
- The code is in alpha version, any comment of pull request is welcome.

## Install

```
$ pip install resume
```

or download and improve the code by yourself :) installing in develop mode in your home directory

```
 python setup.py develop --user
```


## Python versions

Is tested only in python 2.7 yet, but there is not any deliberated incompatibility with python 3.x versions.
