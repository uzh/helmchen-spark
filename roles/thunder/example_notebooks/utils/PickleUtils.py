import pickle
import os

def serialize(obj, file_name, path, obj_id):
    """
    Pickle a Python object
    """
    file_name = '%s_%s.pkl' % (file_name, obj_id)
    file_path = path + os.path.sep + file_name
    with open(file_path, "wb") as pfile:
        pickle.dump(obj, pfile, 2)


def deserialize(file_path):
    """
    Extracts a pickled Python object and returns it
    """
    with open(file_path, "rb") as pfile:
        obj = pickle.load(pfile)
    return obj
