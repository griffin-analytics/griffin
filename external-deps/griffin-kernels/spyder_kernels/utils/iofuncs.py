# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Griffin Kernels Contributors
#
# 
# (see griffin_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Input/Output Utilities

Note: 'load' functions has to return a dictionary from which a globals()
      namespace may be updated
"""
# Standard library imports
import sys
import os
import os.path as osp
import tarfile
import tempfile
import shutil
import types
import json
import inspect
import dis
import copy
import glob
import pickle

# Local imports
from griffin_kernels.utils.lazymodules import (
    FakeObject, numpy as np, pandas as pd, PIL, scipy as sp)


# ---- For Matlab files
# -----------------------------------------------------------------------------
class MatlabStruct(dict):
    """
    Matlab style struct, enhanced.

    Supports dictionary and attribute style access.  Can be pickled,
    and supports code completion in a REPL.

    Examples
    ========
    >>> from griffin_kernels.utils.iofuncs import MatlabStruct
    >>> a = MatlabStruct()
    >>> a.b = 'spam'  # a["b"] == 'spam'
    >>> a.c["d"] = 'eggs'  # a.c.d == 'eggs'
    >>> print(a)
    {'c': {'d': 'eggs'}, 'b': 'spam'}

    """
    def __getattr__(self, attr):
        """Access the dictionary keys for unknown attributes."""
        try:
            return self[attr]
        except KeyError:
            msg = "'MatlabStruct' object has no attribute %s" % attr
            raise AttributeError(msg)

    def __getitem__(self, attr):
        """
        Get a dict value; create a MatlabStruct if requesting a submember.

        Do not create a key if the attribute starts with an underscore.
        """
        if attr in self.keys() or attr.startswith('_'):
            return dict.__getitem__(self, attr)
        frame = inspect.currentframe()
        # step into the function that called us
        if frame.f_back.f_back and self._is_allowed(frame.f_back.f_back):
            dict.__setitem__(self, attr, MatlabStruct())
        elif self._is_allowed(frame.f_back):
            dict.__setitem__(self, attr, MatlabStruct())
        return dict.__getitem__(self, attr)

    def _is_allowed(self, frame):
        """Check for allowed op code in the calling frame"""
        allowed = [dis.opmap['STORE_ATTR'], dis.opmap['LOAD_CONST'],
                   dis.opmap.get('STOP_CODE', 0)]
        bytecode = frame.f_code.co_code
        instruction = bytecode[frame.f_lasti + 3]
        return instruction in allowed

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    @property
    def __dict__(self):
        """Allow for code completion in a REPL"""
        return self.copy()


def get_matlab_value(val):
    """
    Extract a value from a Matlab file

    From the oct2py project, see
    https://pythonhosted.org/oct2py/conversions.html
    """
    # Extract each item of a list.
    if isinstance(val, list):
        return [get_matlab_value(v) for v in val]

    # Ignore leaf objects.
    if not isinstance(val, np.ndarray):
        return val

    # Convert user defined classes.
    if hasattr(val, 'classname'):
        out = dict()
        for name in val.dtype.names:
            out[name] = get_matlab_value(val[name].squeeze().tolist())
        cls = type(val.classname, (object,), out)
        return cls()

    # Extract struct data.
    elif val.dtype.names:
        out = MatlabStruct()
        for name in val.dtype.names:
            out[name] = get_matlab_value(val[name].squeeze().tolist())
        val = out

    # Extract cells.
    elif val.dtype.kind == 'O':
        val = val.squeeze().tolist()
        if not isinstance(val, list):
            val = [val]
        val = get_matlab_value(val)

    # Compress singleton values.
    elif val.size == 1:
        val = val.item()

    # Compress empty values.
    elif val.size == 0:
        if val.dtype.kind in 'US':
            val = ''
        else:
            val = []

    return val


def load_matlab(filename):
    if sp.io is FakeObject:
        return None, ''

    try:
        out = sp.io.loadmat(filename, struct_as_record=True)
        data = dict()
        for (key, value) in out.items():
            data[key] = get_matlab_value(value)
        return data, None
    except Exception as error:
        return None, str(error)


def save_matlab(data, filename):
    if sp.io is FakeObject:
        return

    try:
        sp.io.savemat(filename, data, oned_as='row')
    except Exception as error:
        return str(error)


# ---- For arrays
# -----------------------------------------------------------------------------
def load_array(filename):
    if np.load is FakeObject:
        return None, ''

    try:
        name = osp.splitext(osp.basename(filename))[0]
        data = np.load(filename)
        if isinstance(data, np.lib.npyio.NpzFile):
            return dict(data), None
        elif hasattr(data, 'keys'):
            return data, None
        else:
            return {name: data}, None
    except Exception as error:
        return None, str(error)


def __save_array(data, basename, index):
    """Save numpy array"""
    fname = basename + '_%04d.npy' % index
    np.save(fname, data)
    return fname


# ---- For PIL images
# -----------------------------------------------------------------------------
if sys.byteorder == 'little':
    _ENDIAN = '<'
else:
    _ENDIAN = '>'

DTYPES = {
    "1": ('|b1', None),
    "L": ('|u1', None),
    "I": ('%si4' % _ENDIAN, None),
    "F": ('%sf4' % _ENDIAN, None),
    "I;16": ('|u2', None),
    "I;16S": ('%si2' % _ENDIAN, None),
    "P": ('|u1', None),
    "RGB": ('|u1', 3),
    "RGBX": ('|u1', 4),
    "RGBA": ('|u1', 4),
    "CMYK": ('|u1', 4),
    "YCbCr": ('|u1', 4),
}


def __image_to_array(filename):
    img = PIL.Image.open(filename)
    try:
        dtype, extra = DTYPES[img.mode]
    except KeyError:
        raise RuntimeError("%s mode is not supported" % img.mode)
    shape = (img.size[1], img.size[0])
    if extra is not None:
        shape += (extra,)
    return np.array(img.getdata(), dtype=np.dtype(dtype)).reshape(shape)


def load_image(filename):
    if PIL.Image is FakeObject or np.array is FakeObject:
        return None, ''

    try:
        name = osp.splitext(osp.basename(filename))[0]
        return {name: __image_to_array(filename)}, None
    except Exception as error:
        return None, str(error)


# ---- For misc formats
# -----------------------------------------------------------------------------
def load_pickle(filename):
    """Load a pickle file as a dictionary"""
    try:
        if pd.read_pickle is not FakeObject:
            return pd.read_pickle(filename), None
        else:
            with open(filename, 'rb') as fid:
                data = pickle.load(fid)
            return data, None
    except Exception as err:
        return None, str(err)


def load_json(filename):
    """Load a json file as a dictionary"""
    try:
        with open(filename, 'r') as fid:
            data = json.load(fid)
        return data, None
    except Exception as err:
        return None, str(err)


# ---- For Spydata files
# -----------------------------------------------------------------------------
def save_dictionary(data, filename):
    """Save dictionary in a single file .spydata file"""
    filename = osp.abspath(filename)
    old_cwd = os.getcwd()
    os.chdir(osp.dirname(filename))
    error_message = None
    skipped_keys = []
    data_copy = {}

    try:
        # Copy dictionary before modifying it to fix #6689
        for obj_name, obj_value in data.items():
            # Skip modules, since they can't be pickled, users virtually never
            # would want them to be and so they don't show up in the skip list.
            # Skip callables, since they are only pickled by reference and thus
            # must already be present in the user's environment anyway.
            if not (callable(obj_value) or isinstance(obj_value,
                                                      types.ModuleType)):
                # If an object cannot be deepcopied, then it cannot be pickled.
                # Ergo, we skip it and list it later.
                try:
                    data_copy[obj_name] = copy.deepcopy(obj_value)
                except Exception:
                    skipped_keys.append(obj_name)
        data = data_copy
        if not data:
            raise RuntimeError('No supported objects to save')

        saved_arrays = {}
        if np.ndarray is not FakeObject:
            # Saving numpy arrays with np.save
            arr_fname = osp.splitext(filename)[0]
            for name in list(data.keys()):
                try:
                    if (isinstance(data[name], np.ndarray) and
                            data[name].size > 0):
                        # Save arrays at data root
                        fname = __save_array(data[name], arr_fname,
                                             len(saved_arrays))
                        saved_arrays[(name, None)] = osp.basename(fname)
                        data.pop(name)
                    elif isinstance(data[name], (list, dict)):
                        # Save arrays nested in lists or dictionaries
                        if isinstance(data[name], list):
                            iterator = enumerate(data[name])
                        else:
                            iterator = iter(list(data[name].items()))
                        to_remove = []
                        for index, value in iterator:
                            if (isinstance(value, np.ndarray) and
                                    value.size > 0):
                                fname = __save_array(value, arr_fname,
                                                     len(saved_arrays))
                                saved_arrays[(name, index)] = (
                                    osp.basename(fname))
                                to_remove.append(index)
                        for index in sorted(to_remove, reverse=True):
                            data[name].pop(index)
                except (RuntimeError, pickle.PicklingError, TypeError,
                        AttributeError, IndexError):
                    # If an array can't be saved with numpy for some reason,
                    # leave the object intact and try to save it normally.
                    pass
            if saved_arrays:
                data['__saved_arrays__'] = saved_arrays

        pickle_filename = osp.splitext(filename)[0] + '.pickle'
        # Attempt to pickle everything.
        # If pickling fails, iterate through to eliminate problem objs & retry.
        with open(pickle_filename, 'w+b') as fdesc:
            try:
                pickle.dump(data, fdesc, protocol=2)
            except (pickle.PicklingError, AttributeError, TypeError,
                    ImportError, IndexError, RuntimeError):
                data_filtered = {}
                for obj_name, obj_value in data.items():
                    try:
                        pickle.dumps(obj_value, protocol=2)
                    except Exception:
                        skipped_keys.append(obj_name)
                    else:
                        data_filtered[obj_name] = obj_value
                if not data_filtered:
                    raise RuntimeError('No supported objects to save')
                pickle.dump(data_filtered, fdesc, protocol=2)

        # Use PAX (POSIX.1-2001) format instead of default GNU.
        # This improves interoperability and UTF-8/long variable name support.
        with tarfile.open(filename, "w", format=tarfile.PAX_FORMAT) as tar:
            for fname in ([pickle_filename]
                          + [fn for fn in list(saved_arrays.values())]):
                tar.add(osp.basename(fname))
                os.remove(fname)
    except (RuntimeError, pickle.PicklingError, TypeError) as error:
        error_message = str(error)
    else:
        if skipped_keys:
            skipped_keys.sort()
            error_message = ('Some objects could not be saved: '
                             + ', '.join(skipped_keys))
    finally:
        os.chdir(old_cwd)
    return error_message


def is_within_directory(directory, target):
    """Check if a file is within a directory."""
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)
    prefix = os.path.commonprefix([abs_directory, abs_target])
    return prefix == abs_directory


def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
    """Safely extract a tar file."""
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not is_within_directory(path, member_path):
            raise Exception(
                f"Attempted path traversal in tar file {tar.name!r}"
            )
    tar.extractall(path, members, numeric_owner=numeric_owner)


def load_dictionary(filename):
    """Load dictionary from .spydata file"""
    filename = osp.abspath(filename)
    old_cwd = os.getcwd()
    tmp_folder = tempfile.mkdtemp()
    os.chdir(tmp_folder)
    data = None
    error_message = None
    try:
        with tarfile.open(filename, "r") as tar:
            safe_extract(tar)

        pickle_filename = glob.glob('*.pickle')[0]
        # 'New' format (Griffin >=2.2)
        with open(pickle_filename, 'rb') as fdesc:
            data = pickle.loads(fdesc.read())
        saved_arrays = {}
        if np.load is not FakeObject:
            # Loading numpy arrays saved with np.save
            try:
                saved_arrays = data.pop('__saved_arrays__')
                for (name, index), fname in list(saved_arrays.items()):
                    arr = np.load(osp.join(tmp_folder, fname), allow_pickle=True)
                    if index is None:
                        data[name] = arr
                    elif isinstance(data[name], dict):
                        data[name][index] = arr
                    else:
                        data[name].insert(index, arr)
            except KeyError:
                pass
    # Except AttributeError from e.g. trying to load function no longer present
    except (AttributeError, EOFError, ValueError) as error:
        error_message = str(error)
    # To ensure working dir gets changed back and temp dir wiped no matter what
    finally:
        os.chdir(old_cwd)
        try:
            shutil.rmtree(tmp_folder)
        except OSError as error:
            error_message = str(error)
    return data, error_message


# ---- For HDF5 files
# -----------------------------------------------------------------------------
def load_hdf5(filename):
    """
    Load an hdf5 file.

    Notes
    -----
    - This is a fairly dumb implementation which reads the whole HDF5 file into
      Griffin's variable explorer.  Since HDF5 files are designed for storing
      very large data-sets, it may be much better to work directly with the
      HDF5 objects, thus keeping the data on disk. Nonetheless, this gives
      quick and dirty but convenient access to them.
    - There is no support for creating files with compression, chunking etc,
      although these can be read without problem.
    - When reading an HDF5 file with sub-groups, groups in the file will
      correspond to dictionaries with the same layout.
    """
    def get_group(group):
        contents = {}
        for name, obj in list(group.items()):
            if isinstance(obj, h5py.Dataset):
                contents[name] = np.array(obj)
            elif isinstance(obj, h5py.Group):
                # it is a group, so call self recursively
                contents[name] = get_group(obj)
            # other objects such as links are ignored
        return contents

    try:
        import h5py

        f = h5py.File(filename, 'r')
        contents = get_group(f)
        f.close()
        return contents, None
    except Exception as error:
        return None, str(error)


def save_hdf5(data, filename):
    """
    Save an hdf5 file.

    Notes
    -----
    - All datatypes to be saved must be convertible to a numpy array, otherwise
      an exception will be raised.
    - Data attributes are currently ignored.
    - When saving data after reading it with load_hdf5, dictionaries are not
      turned into HDF5 groups.
    """
    try:
        import h5py

        f = h5py.File(filename, 'w')
        for key, value in list(data.items()):
            f[key] = np.array(value)
        f.close()
    except Exception as error:
        return str(error)


# ---- For DICOM files
# -----------------------------------------------------------------------------
def load_dicom(filename):
    """Load a DICOM files."""
    try:
        from pydicom import dicomio

        name = osp.splitext(osp.basename(filename))[0]
        try:
            # For Pydicom 3/Python 3.10+
            data = dicomio.dcmread(filename, force=True)
        except TypeError:
            data = dicomio.dcmread(filename)
        except AttributeError:
            # For Pydicom 2/Python 3.9-
            try:
                data = dicomio.read_file(filename, force=True)
            except TypeError:
                data = dicomio.read_file(filename)
        arr = data.pixel_array
        return {name: arr}, None
    except Exception as error:
        return None, str(error)


# ---- Class to group all IO functionality
# -----------------------------------------------------------------------------
class IOFunctions:
    def __init__(self):
        self.load_extensions = None
        self.save_extensions = None
        self.load_filters = None
        self.save_filters = None
        self.load_funcs = None
        self.save_funcs = None

    def setup(self):
        iofuncs = self.get_internal_funcs()
        load_extensions = {}
        save_extensions = {}
        load_funcs = {}
        save_funcs = {}
        load_filters = []
        save_filters = []
        load_ext = []

        for ext, name, loadfunc, savefunc in iofuncs:
            filter_str = str(name + " (*%s)" % ext)
            if loadfunc is not None:
                load_filters.append(filter_str)
                load_extensions[filter_str] = ext
                load_funcs[ext] = loadfunc
                load_ext.append(ext)
            if savefunc is not None:
                save_extensions[filter_str] = ext
                save_filters.append(filter_str)
                save_funcs[ext] = savefunc

        load_filters.insert(
            0, str("Supported files" + " (*" + " *".join(load_ext) + ")")
        )
        load_filters.append(str("All files (*.*)"))

        self.load_filters = "\n".join(load_filters)
        self.save_filters = "\n".join(save_filters)
        self.load_funcs = load_funcs
        self.save_funcs = save_funcs
        self.load_extensions = load_extensions
        self.save_extensions = save_extensions

    def get_internal_funcs(self):
        return [
            ('.spydata', "Griffin data files", load_dictionary, save_dictionary),
            ('.npy', "NumPy arrays", load_array, None),
            ('.npz', "NumPy zip arrays", load_array, None),
            ('.mat', "Matlab files", load_matlab, save_matlab),
            ('.csv', "CSV text files", 'import_wizard', None),
            ('.txt', "Text files", 'import_wizard', None),
            ('.jpg', "JPEG images", load_image, None),
            ('.png', "PNG images", load_image, None),
            ('.gif', "GIF images", load_image, None),
            ('.tif', "TIFF images", load_image, None),
            ('.pkl', "Pickle files", load_pickle, None),
            ('.pickle', "Pickle files", load_pickle, None),
            ('.json', "JSON files", load_json, None),
            ('.h5', "HDF5 files", load_hdf5, save_hdf5),
            ('.dcm', "DICOM images", load_dicom, None),
        ]

    def save(self, data, filename):
        ext = osp.splitext(filename)[1].lower()
        if ext in self.save_funcs:
            return self.save_funcs[ext](data, filename)
        else:
            return "<b>Unsupported file type '%s'</b>" % ext

    def load(self, filename):
        ext = osp.splitext(filename)[1].lower()
        if ext in self.load_funcs:
            return self.load_funcs[ext](filename)
        else:
            return None, "<b>Unsupported file type '%s'</b>" % ext

iofunctions = IOFunctions()
iofunctions.setup()


# ---- Test
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import datetime
    testdict = {'d': 1, 'a': np.random.rand(10, 10), 'b': [1, 2]}
    testdate = datetime.date(1945, 5, 8)
    example = {'str': 'kjkj kj k j j kj k jkj',
               'unicode': u'éù',
               'list': [1, 3, [4, 5, 6], 'kjkj', None],
               'tuple': ([1, testdate, testdict], 'kjkj', None),
               'dict': testdict,
               'float': 1.2233,
               'array': np.random.rand(4000, 400),
               'empty_array': np.array([]),
               'date': testdate,
               'datetime': datetime.datetime(1945, 5, 8),
               }
    import time
    t0 = time.time()
    save_dictionary(example, "test.spydata")
    print(" Data saved in %.3f seconds" % (time.time()-t0))
    t0 = time.time()
    example2, ok = load_dictionary("test.spydata")
    os.remove("test.spydata")

    print("Data loaded in %.3f seconds" % (time.time()-t0))
