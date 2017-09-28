"""
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
"""
from __future__ import print_function
# -------------------------------------------------
# Recovery Checkpoint support
# -------------------------------------------------
import inspect
import os
import time
import re
# import bz2
import gzip
import cPickle as pickle
import ctypes
import types
import numpy as np

NUMPY_RAND_SEED = '__rand_seed__'
FUNC_TYPES = (types.FunctionType, types.GeneratorType, types.MethodType)


def find(pattern):
    "find the 1st matched file"
    regexp = re.compile(pattern)
    for root, _, files in os.walk('.'):
        for name in files:
            if regexp.search(name):
                return os.path.join(root, name)


class NullCheckpoint(dict):
    "A null checkpoint that does nothing"
    def __init__(self, filename=''):
        self.filename = filename

    def save(self, **data):
        "save the dict to disk"
        pass

    def load(self):
        "load dict from disk"
        return self


class Checkpoint(dict):
    """A simple class for saving and retrieve info
    to continue interrupted works.
    CACHE_EXPIRE: controls when data is discarded (but not deleted)
    """
    CACHE_EXPIRE = 24 * 3600  # cache will be discarded beyond this time
    folder = '.checkpoints'
    # ext = '.pbz2'
    ext = '.pzip'
    reg_exclude = re.compile(r'\b_|.*_$', re.DOTALL | re.I)

    # compressor = bz2.BZ2File
    compressor = gzip.GzipFile

    ALLOWED_TYPES = (
        # basic types
        types.BooleanType, types.ComplexType, types.DictionaryType,
        types.FloatType, types.IntType, types.ListType, types.LongType,
        types.NoneType, types.StringType, types.TupleType, types.UnicodeType,

        # numpy
        np.ndarray, np.generic,
    )

    @classmethod
    def add_types(cls, *new_types):
        "dynamically add new allowed types to be serialized"
        allowed = set(cls.ALLOWED_TYPES)
        allowed.update(new_types)
        cls.ALLOWED_TYPES = tuple(allowed)

    def __init__(self, filename=None, clean=False, rate=30):
        self.modified = 0
        self.rate = rate
        if not filename:
            filename = inspect.stack()[1][3]

        if not filename.endswith(self.ext):
            filename += self.ext

        # search the checkpoints under the current folder
        # because some times pytest is executed in the project's root folder
        # and sometime from tests folder, so the checkpoints files could be in
        # different places.
        # To avoid it, this will use the fist deepest checkpoint found.
        # This way we can get the cached data no matter where the
        # process has been launched
        location = find(filename)
        if location:
            filename = location
        else:
            folder, _ = os.path.split(filename)
            if not folder:
                filename = os.path.join(self.folder, filename)

            filename = os.path.expanduser(filename)
            filename = os.path.expandvars(filename)
            filename = os.path.abspath(filename)

        self.filename = filename

        # load any initial state like np.random seed
        self._cached = self._load(clean)
        self._recover_internal_status()

    def save(self, **data):
        "save the dict to disk"
        # print(">> Saving checkpoint: %s" % self.filename)

        context = self.context
        context.update(self)
        context.update(data)

        folder = os.path.split(self.filename)[0]
        if not os.path.exists(folder):
            os.makedirs(folder)

        with self.compressor(self.filename, 'wb') as file_:
            pickle.dump(context, file_, protocol=2)

        self.modified = time.time()

    def _load(self, clean=False):
        "load dict from disk"
        data = dict()
        if os.access(self.filename, os.F_OK):
            mtime = os.stat(self.filename).st_mtime
            if clean or time.time() - mtime > self.CACHE_EXPIRE:
                # print("** Ignored or Expired checkpoint data: %s **" %
                        # os.path.basename(self.filename))
                pass
            else:
                # print("<< Loading checkpoint: %s" % self.filename)
                with self.compressor(self.filename, 'rb') as file_:
                    data = pickle.load(file_)
        return data

    def _recover_internal_status(self, **data):
        data.update(self._cached)
        # update other internal states save in checkpoint
        seed = data.get(NUMPY_RAND_SEED)
        if seed is not None:
            # print "** Setting random seed: %s" %  sum(seed[1])
            np.random.set_state(seed)
            self[NUMPY_RAND_SEED] = seed
        else:
            seed = np.random.get_state()
            self[NUMPY_RAND_SEED] = seed
            # print "-- Saving random seed: %s" %  sum(seed[1])

            self.save()  # save initial states like NUMPY_RAND_SEED

    def restore(self, **data):
        "Restore the stack frame variables from disk"
        data.update(self._cached)

        # sync data with caller frame
        frame = inspect.stack()[1][0]
        code = frame.f_code
        loc = frame.f_locals
        # don't consider any argument variable as if we try to
        # modify the update will fail
        calling_args = code.co_varnames[:code.co_argcount]
        for key, value in data.items():
            if key in calling_args:
                continue
            if key in loc:
                loc[key] = value
            elif key in self:
                try:
                    self[key][:] = value
                except TypeError:
                    self[key] = value

        # let cpython to update the frame locals
        ctypes.pythonapi.PyFrame_LocalsToFast(
            ctypes.py_object(frame),
            ctypes.c_int(1))

        # save memory forgetting initial state after restoring
        self._cached.clear()

    # def __del__(self):
        # self.save()  # last try to sync data if needed

    def must_save(self, key, value):
        "Check if data must be saved in checkpoint"
        if self.reg_exclude.match(key):
            return False

        if hasattr(value, '__dict__'):
            return False

        return isinstance(value, self.ALLOWED_TYPES)

    def sync(self):
        "save state to disk from time to time"
        now = time.time()
        if now - self.modified >= self.rate:
            self.save()

    @property
    def context(self):
        "Return a dict with the caller frame locals"
        # get the first stack frame out from this module scope
        frame = inspect.stack()[0][0]
        this = frame.f_globals["__name__"]
        while frame.f_globals["__name__"] == this:
            frame = frame.f_back

        data = dict(self)
        loc = frame.f_locals
        code = frame.f_code
        calling_args = code.co_varnames[:code.co_argcount]
        for key, value in loc.items():
            # TODO: calling arguments is also saved now for validating
            # TODO: that the 2nd call has the same arguments
            # TODO: or to check if signature has changed and may invalidate
            # TODO: the checkpoint
            if key in calling_args:
                continue  # don't save by now

            if self.must_save(key, value):
                # print "saving: %s" % (key, )
                data[key] = loc[key]
            # else:
                # print "ignoring %s = %s" % (key, value.__class__.__name__)
        return data
