from __future__ import print_function, division
import types
import numpy as np
from functools import wraps
import warnings
import properties

from discretize.utils import asArray_N_x_Dim

# scooby is a soft dependency for SimPEG
try:
    from scooby import Report as ScoobyReport
except ImportError:

    class ScoobyReport:
        def __init__(self, additional, core, optional, ncol, text_width, sort):
            print(
                "\n  *ERROR*: `SimPEG.Report` requires `scooby`."
                "\n           Install it via `pip install scooby` or"
                "\n           `conda install -c conda-forge scooby`.\n"
            )


def create_wrapper_from_class(input_class, *fun_names):
    """Create wrapper class with memory profiler.

    Using *memory_profiler.profile*, this function creates a wrapper class
    from the input class and function names specified.
    
    Parameters
    ----------
    input_class : class
        Input class being used to create the wrapper
    fun_names: list of str
        Names of the functions that will be wrapped to the wrapper class. These names must
        correspond to methods of the input class.  
    
    Returns
    -------
    class :
        Wrapper class

    Examples
    --------

    >>> foo_mem = create_wrapper_from_class(foo,['my_func'])
    >>> fooi = foo_mem()
    >>> for i in range(5):
    >>>     fooi.my_func()

    Then run it from the command line

    ``python -m memory_profiler exampleMemWrapper.py``
    """
    from memory_profiler import profile

    attrs = {}
    for f in fun_names:
        if hasattr(input_class, f):
            attrs[f] = profile(getattr(input_class, f))
        else:
            print("{0!s} not found in {1!s} Class".format(f, input_class.__name__))

    return type(input_class.__name__ + "MemProfileWrap", (input_class,), attrs)


def hook(obj, method, name=None, overwrite=False, silent=False):
    """Dynamically bind on class's method to an instance of a different class.

    Parameters
    ----------
    obj : class
        Instance of a class that will be binded to a new method
    method : method
        The method that will be binded to `obj`; i.e. ClassName.method_name
    name : str
        Provide a different name for the method being binded to `obj`. If ``None``,
        the original method name is used. 
    overwrite : bool
        Overwrite previous hook
    silent: bool
        Print whether a previous hook was overwritten
    """
    if name is None:
        name = method.__name__
        if name == "<lambda>":
            raise Exception("Must provide name to hook lambda functions.")
    if not hasattr(obj, name) or overwrite:
        setattr(obj, name, types.MethodType(method, obj))
        if getattr(obj, "debug", False):
            print("Method " + name + " was added to class.")
    elif not silent or getattr(obj, "debug", False):
        print("Method " + name + " was not overwritten.")


def set_kwargs(obj, ignore=None, **kwargs):
    """
    Set key word arguments for an object or throw an error if any don't exist.
    
    Parameters
    ----------
    obj : class
        Instance of a class
    ignore : str
        List of strings denoting kwargs that are ignored (not being set)
    """
    if ignore is None:
        ignore = []
    for attr in kwargs:
        if attr in ignore:
            continue
        if hasattr(obj, attr):
            setattr(obj, attr, kwargs[attr])
        else:
            raise Exception("{0!s} attr is not recognized".format(attr))

    # hook(obj, hook, silent=True)
    # hook(obj, setKwargs, silent=True)


def print_done(obj, printers, name="Done", pad=""):
    titles = ""
    widths = 0
    for printer in printers:
        titles += ("{{:^{0:d}}}".format(printer["width"])).format(printer["title"]) + ""
        widths += printer["width"]
    print(pad + "{0} {1} {0}".format("=" * ((widths - 1 - len(name)) // 2), name))
    # print(pad + "%s" % '-'*widths)


def print_titles(obj, printers, name="Print Titles", pad=""):
    titles = ""
    widths = 0
    for printer in printers:
        titles += ("{{:^{0:d}}}".format(printer["width"])).format(printer["title"]) + ""
        widths += printer["width"]
    print(pad + "{0} {1} {0}".format("=" * ((widths - 1 - len(name)) // 2), name))
    print(pad + titles)
    print(pad + "%s" % "-" * widths)


def print_line(obj, printers, pad=""):
    values = ""
    for printer in printers:
        values += ("{{:^{0:d}}}".format(printer["width"])).format(
            printer["format"] % printer["value"](obj)
        )
    print(pad + values)


def check_stoppers(obj, stoppers):
    # check stopping rules
    optimal = []
    critical = []
    for stopper in stoppers:
        l = stopper["left"](obj)
        r = stopper["right"](obj)
        if stopper["stopType"] == "optimal":
            optimal.append(l <= r)
        if stopper["stopType"] == "critical":
            critical.append(l <= r)

    if obj.debug:
        print("checkStoppers.optimal: ", optimal)
    if obj.debug:
        print("checkStoppers.critical: ", critical)

    return (len(optimal) > 0 and all(optimal)) | (len(critical) > 0 and any(critical))


def print_stoppers(obj, stoppers, pad="", stop="STOP!", done="DONE!"):
    print(pad + "{0!s}{1!s}{2!s}".format("-" * 25, stop, "-" * 25))
    for stopper in stoppers:
        l = stopper["left"](obj)
        r = stopper["right"](obj)
        print(pad + stopper["str"] % (l <= r, l, r))
    print(pad + "{0!s}{1!s}{2!s}".format("-" * 25, done, "-" * 25))


def call_hooks(match, mainFirst=False):
    """
    Use this to wrap a funciton::

        @callHooks('doEndIteration')
        def doEndIteration(self):
            pass

    This will call everything named _doEndIteration* at the beginning of the function call.
    By default the main method (doEndIteration) is run after all of the sub methods (_doEndIteration*).
    This can be reversed by adding the mainFirst=True kwarg.
    """

    def callHooksWrap(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):

            if not mainFirst:
                for method in [
                    posible for posible in dir(self) if ("_" + match) in posible
                ]:
                    if getattr(self, "debug", False):
                        print((match + " is calling self." + method))
                    getattr(self, method)(*args, **kwargs)

                return f(self, *args, **kwargs)
            else:
                out = f(self, *args, **kwargs)

                for method in [
                    posible for posible in dir(self) if ("_" + match) in posible
                ]:
                    if getattr(self, "debug", False):
                        print((match + " is calling self." + method))
                    getattr(self, method)(*args, **kwargs)

                return out

        extra = """
            If you have things that also need to run in the method {0!s}, you can create a method::

                def _{1!s}*(self, ... ):
                    pass

            Where the * can be any string. If present, _{2!s}* will be called at the start of the default {3!s} call.
            You may also completely overwrite this function.
        """.format(
            match, match, match, match
        )
        doc = wrapper.__doc__
        wrapper.__doc__ = ("" if doc is None else doc) + extra
        return wrapper

    return callHooksWrap


def dependent_property(name, value, children, doc):
    def fget(self):
        return getattr(self, name, value)

    def fset(self, val):
        if (np.isscalar(val) and getattr(self, name, value) == val) or val is getattr(
            self, name, value
        ):
            return  # it is the same!
        for child in children:
            if hasattr(self, child):
                delattr(self, child)
        setattr(self, name, val)

    return property(fget=fget, fset=fset, doc=doc)


def requires(var):
    """
    Use this to wrap a funciton::

        @requires('prob')
        def dpred(self):
            pass

    This wrapper will ensure that a problem has been bound to the data.
    If a problem is not bound an Exception will be raised, and an nice error message printed.
    """

    def requiresVar(f):
        if var == "prob":
            extra = """

        .. note::

            To use survey.{0!s}(), SimPEG requires that a problem be bound to the survey.
            If a problem has not been bound, an Exception will be raised.
            To bind a problem to the Data object::

                survey.pair(myProblem)

            """.format(
                f.__name__
            )
        else:
            extra = """
                To use *{0!s}* method, SimPEG requires that the {1!s} be specified.
            """.format(
                f.__name__, var
            )

        @wraps(f)
        def requiresVarWrapper(self, *args, **kwargs):
            if getattr(self, var, None) is None:
                raise Exception(extra)
            return f(self, *args, **kwargs)

        doc = requiresVarWrapper.__doc__
        requiresVarWrapper.__doc__ = ("" if doc is None else doc) + extra

        return requiresVarWrapper

    return requiresVar


class Report(ScoobyReport):
    """Print date, time, and version information.

    Use scooby to print date, time, and package version information in any
    environment (Jupyter notebook, IPython console, Python console, QT
    console), either as html-table (notebook) or as plain text (anywhere).

    Always shown are the OS, number of CPU(s), ``numpy``, ``scipy``,
    ``SimPEG``, ``cython``, ``properties``, ``vectormath``, ``discretize``,
    ``pymatsolver``, ``sys.version``, and time/date.

    Additionally shown are, if they can be imported, ``IPython``,
    ``matplotlib``, and ``ipywidgets``. It also shows MKL information, if
    available.

    All modules provided in ``add_pckg`` are also shown.


    Parameters
    ----------
    add_pckg : packages, optional
        Package or list of packages to add to output information (must be
        imported beforehand).

    ncol : int, optional
        Number of package-columns in html table (no effect in text-version);
        Defaults to 3.

    text_width : int, optional
        The text width for non-HTML display modes

    sort : bool, optional
        Sort the packages when the report is shown


    Examples
    --------

    >>> import pytest
    >>> import dateutil
    >>> from SimPEG import Report
    >>> Report()                            # Default values
    >>> Report(pytest)                      # Provide additional package
    >>> Report([pytest, dateutil], ncol=5)  # Define nr of columns

    """

    def __init__(self, add_pckg=None, ncol=3, text_width=80, sort=False):
        """Initiate a scooby.Report instance."""

        # Mandatory packages.
        core = [
            "SimPEG",
            "discretize",
            "pymatsolver",
            "vectormath",
            "properties",
            "numpy",
            "scipy",
            "cython",
        ]

        # Optional packages.
        optional = ["IPython", "matplotlib", "ipywidgets"]

        super().__init__(
            additional=add_pckg,
            core=core,
            optional=optional,
            ncol=ncol,
            text_width=text_width,
            sort=sort,
        )


def deprecate_class(removal_version=None, new_location=None, future_warn=False):
    def decorator(cls):
        my_name = cls.__name__
        parent_name = cls.__bases__[0].__name__
        message = f"{my_name} has been deprecated, please use {parent_name}."
        if removal_version is not None:
            message += f" It will be removed in version {removal_version} of SimPEG."
        else:
            message += " It will be removed in a future version of SimPEG."

        # stash the original initialization of the class
        cls._old__init__ = cls.__init__

        def __init__(self, *args, **kwargs):
            if future_warn:
                warnings.warn(message, FutureWarning)
            else:
                warnings.warn(message, DeprecationWarning)
            self._old__init__(*args, **kwargs)

        cls.__init__ = __init__
        if new_location is not None:
            parent_name = f"{new_location}.{parent_name}"
        cls.__doc__ = f""" This class has been deprecated, see `{parent_name}` for documentation"""
        return cls

    return decorator


def deprecate_module(old_name, new_name, removal_version=None, future_warn=False):
    message = f"The {old_name} module has been deprecated, please use {new_name}."
    if removal_version is not None:
        message += f" It will be removed in version {removal_version} of SimPEG"
    else:
        message += " It will be removed in a future version of SimPEG."
    message += " Please update your code accordingly."
    if future_warn:
        warnings.warn(message, FutureWarning)
    else:
        warnings.warn(message, DeprecationWarning)


def deprecate_property(
    prop, old_name, new_name=None, removal_version=None, future_warn=False
):

    if isinstance(prop, property):
        if new_name is None:
            new_name = prop.fget.__qualname__
        cls_name = new_name.split(".")[0]
        old_name = f"{cls_name}.{old_name}"
    elif isinstance(prop, properties.GettableProperty):
        if new_name is None:
            new_name = prop.name
        prop = prop.get_property()

    message = f"{old_name} has been deprecated, please use {new_name}."
    if removal_version is not None:
        message += f" It will be removed in version {removal_version} of SimPEG."
    else:
        message += " It will be removed in a future version of SimPEG."

    def get_dep(self):
        if future_warn:
            warnings.warn(message, FutureWarning)
        else:
            warnings.warn(message, DeprecationWarning)
        return prop.fget(self)

    def set_dep(self, other):
        if future_warn:
            warnings.warn(message, FutureWarning)
        else:
            warnings.warn(message, DeprecationWarning)
        prop.fset(self, other)

    doc = f"`{old_name}` has been deprecated. See `{new_name}` for documentation"

    return property(get_dep, set_dep, prop.fdel, doc)


def deprecate_method(method, old_name, removal_version=None, future_warn=False):
    new_name = method.__qualname__
    split_name = new_name.split(".")
    if len(split_name) > 1:
        old_name = f"{split_name[0]}.{old_name}"

    message = f"{old_name} has been deprecated, please use {new_name}."
    if removal_version is not None:
        message += f" It will be removed in version {removal_version} of SimPEG."
    else:
        message += " It will be removed in a future version of SimPEG."

    def new_method(*args, **kwargs):
        if future_warn:
            warnings.warn(message, FutureWarning)
        else:
            warnings.warn(message, DeprecationWarning)
        return method(*args, **kwargs)

    doc = f"`{old_name}` has been deprecated. See `{new_name}` for documentation"
    new_method.__doc__ = doc
    return new_method


def deprecate_function(new_function, old_name, removal_version=None):
    new_name = new_function.__name__
    if removal_version is not None:
        tag = f" It will be removed in version {removal_version} of SimPEG."
    else:
        tag = " It will be removed in a future version of SimPEG."

    def dep_function(*args, **kwargs):
        warnings.warn(
            f"{old_name} has been deprecated, please use {new_name}." + tag,
            DeprecationWarning,
        )
        return new_function(*args, **kwargs)

    doc = f"""
    `{old_name}` has been deprecated. See `{new_name}` for documentation

    See Also
    --------
    {new_name}
    """
    dep_function.__doc__ = doc
    return dep_function




# DEPRECATIONS
memProfileWrapper = deprecate_function(create_wrapper_from_class, "memProfileWrapper", removal_version="0.16.0")
setKwargs = deprecate_function(set_kwargs, "setKwargs", removal_version="0.16.0")
printTitles = deprecate_function(print_titles, "printTitles", removal_version="0.16.0")
printLine = deprecate_function(print_line, "printLine", removal_version="0.16.0")
printStoppers = deprecate_function(print_stoppers, "printStoppers", removal_version="0.16.0")
checkStoppers = deprecate_function(check_stoppers, "checkStoppers", removal_version="0.16.0")
printDone = deprecate_function(print_done, "printDone", removal_version="0.16.0")
callHooks = deprecate_function(call_hooks, "callHooks", removal_version="0.16.0")
dependentProperty = deprecate_function(dependent_property, "dependentProperty", removal_version="0.16.0")
