from functools import reduce
from itertools import accumulate, tee

import pickle


def write_pickle(filename, data):
    with open(filename, 'wb') as file_handle:
        pickle.dump(data, file_handle, protocol=pickle.HIGHEST_PROTOCOL)


def load_pickle(path):
    with open(path, 'rb') as f:
        data = pickle.load(f)
    return data


def assoc(_d, key, value):
    # return a modified object or dictionary
    from copy import deepcopy
    d = deepcopy(_d)
    if isinstance(d, dict):
        d[key] = value
    else:
        d.__dict__[key] = value
    return d


def compose(*funs):
    """ Takes functions as arguments and their composition as a single function. """

    def compose2(f, g):
        return lambda x: f(g(x))

    return reduce(compose2, funs, lambda x: x)


def memoize(f):
    """ Memoization decorator for functions taking one or more arguments.
    :param f: a function
    """

    class MemoDict(dict):
        def __init__(self, f_, **kwargs):
            super().__init__(**kwargs)
            self.f = f_

        def __call__(self, *args):
            return self[args]

        def __missing__(self, key):
            ret = self[key] = self.f(*key)
            return ret

    return MemoDict(f)


def rescale(x, in_min, in_max, out_min, out_max):
    return (((x - in_min) * (out_max - out_min)) / (in_max - in_min)) + out_min


def delta_to_absolute(values):
    return list(accumulate(values))


def absolute_to_delta(values):
    return [y - x for x, y in zip([0] + values, values)]


def do_on_key(func, key):
    def set_key_value(obj, value):
        return assoc(obj, key, value)

    def modified_values(objs):
        return func([x.__dict__[key] for x in objs])

    return lambda objs: list(map(set_key_value, objs, modified_values(objs)))


def d_to_a_on_time(events):
    def set_time(event, time):
        return assoc(event, 'time', time)

    abs_times = delta_to_absolute(x.time for x in events)
    return list(map(set_time, events, abs_times))