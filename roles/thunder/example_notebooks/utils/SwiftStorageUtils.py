from __future__ import print_function

import swiftclient
from swiftclient.service import SwiftService, SwiftError, SwiftUploadObject
from swiftclient.multithreading import OutputManager

import os
import tempfile
import shutil
import h5py

import logging
logging.basicConfig(level=logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("swiftclient").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

def listItems(container, conn_opts):
    """
    Test if specified container exists. Return container items as list.

    conn_opts is a dict with connection settings for Swift.
    """
    container_is_empty = True
    item_list = []
    with SwiftService(options=conn_opts) as swift:
        try:
            list_parts_gen = swift.list(container=container)
            for page in list_parts_gen:
                if page["success"]:
                    container_is_empty = False
                    for item in page["listing"]:
                        i_name = item["name"]
                        i_size = int(item["bytes"])
                        item_list.append(i_name)
                        # print("%s [size: %s bytes]" % (i_name, i_size))
        except SwiftError as e:
            print("Could not access container %s. Make sure it has been created." % container)
    if container_is_empty:
        print("Container %s exists but appears to be empty" % container)
    return item_list

def uploadItems(container, folder, source_dir, file_list, conn_opts):
    """
    Upload files to a pseudofolder in Swift container.

    Need to specify both source_dir and full path for each file.
    conn_opts is a dict with connection settings for Swift.
    """

    # Create list of SwiftUploadObjects
    objs = [
            SwiftUploadObject(
                o, object_name='%s/%s' % (folder, o.replace(source_dir, '', 1))
            ) for o in file_list
        ]
    # Upload files to storage
    with SwiftService(options=conn_opts) as swift, OutputManager() as out_manager:
        try:
            for r in swift.upload(container, objs):
                if r['success']:
                    if 'object' in r:
                        print('Finished upload of object %s to container %s' %
                              (r['object'], container))
                    elif 'for_object' in r:
                        print(
                            '%s segment %s' % (r['for_object'],
                                               r['segment_index'])
                            )
                else:
                    error = r['error']
                    if r['action'] == "create_container":
                        logger.warning(
                            'Warning: failed to create container '
                            "'%s'%s", container, error
                        )
                    elif r['action'] == "upload_object":
                        logger.error(
                            "Failed to upload object %s to container %s: %s" %
                            (container, r['object'], error)
                        )
                    else:
                        logger.error("%s" % error)
        except SwiftError as e:
            logger.error(e.value)


def downloadItems(container, objects, conn_opts, down_opts):
    """
    Download objects in container.

    objects is a list of objects to be deleted.
    conn_opts is a dict with connection settings for Swift.
    down_opts is a dict with download settings for Swift.
    """
    try:
        with SwiftService(options=conn_opts) as swift:
            for down_res in swift.download(container=container, objects=objects, options=down_opts):
                if down_res['success']:
                    print("'%s' downloaded to %s" % (down_res['object'], down_opts['out_directory']))
                    status = 1
                else:
                    print("'%s' download failed" % down_res['object'])
                    status = 0
    except SwiftError as e:
        logger.error(e.value)
        status = 0
    return status


def deleteItems(container, objects, conn_opts):
    """
    Delete objects in container without confirmation.

    objects is a list of objects to be deleted.
    conn_opts is a dict with connection settings for Swift.
    """
    with SwiftService(options=conn_opts) as swift:
        del_iter = swift.delete(container=container, objects=objects)
        for del_res in del_iter:
            c = del_res.get('container', '')
            o = del_res.get('object', '')
            a = del_res.get('attempts')
            if del_res['success'] and not del_res['action'] == 'bulk_delete':
                rd = del_res.get('response_dict')
                if rd is not None:
                    t = dict(rd.get('headers', {}))
                    if t:
                        print(
                            'Successfully deleted {0}/{1} in {2} attempts '
                            '(transaction id: {3})'.format(c, o, a, t)
                        )
                    else:
                        print(
                            'Successfully deleted {0}/{1} in {2} '
                            'attempts'.format(c, o, a)
                        )


def deleteExistingFolder(container, folder_name, conn_opts, confirm=True):
    """
    Check Swift container for pseudofolder with name folder_name and delete after confirmation.

    conn_opts is a dict with connection settings for Swift.
    confirm ... whether to ask for confirmation or not when deleting existing folders
    """
    container_items = listItems(container, conn_opts)
    objects_to_delete = [i for i in container_items if i.startswith(folder_name)]
    if objects_to_delete:
        if confirm:
            print('Matching objects:')
            for i in objects_to_delete:
                print(i)
            delete_yn = raw_input('Delete matching objects (Y/N)?')
        else:
            delete_yn = 'Y'
        if delete_yn == 'Y':
            deleteItems(container, objects_to_delete, conn_opts)
    else:
        print('No matching objects.')


def saveAsH5(A, file_name, dataset_name, swift_folder, conn_opts):
    """
    Save numpy array A as dataset_name in HDF5 file temp_dir/file_name.h5 and upload to Swift folder

    conn_opts is a dict with connection settings for Swift.
    """
    # create a temporary directory
    temp_dir = tempfile.mkdtemp()

    h5file = '%s%s.h5' % (temp_dir, file_name)
    print('Saving file %s' % (h5file), end="")
    with h5py.File(h5file, 'w') as hf:
        hf.create_dataset(dataset_name, data=A, compression="gzip")
    print(' - Done')
    # upload file to Swift container
    print('Uploading file %s' % (h5file), end="")
    uploadItems(conn_opts['swift_container'], swift_folder, temp_dir, [h5file], conn_opts)
    print(' - Done')

    # delete temp dir
    shutil.rmtree(temp_dir)
    
    
def saveAsMat(A, file_name, dataset_name, swift_folder, conn_opts, trial_list=None):
    """
    Save numpy array A as dataset_name in Matlab file temp_dir/file_name.mat and upload to Swift folder

    conn_opts is a dict with connection settings for Swift.
    
    Optionally, provide a trial_list, in which case the file name is derived from trial ID and stim type
    """
    from scipy.io import savemat
    from SwiftStorageUtils import uploadItems
    
    if trial_list is not None:
        # figure out trial ID and condition
        trial_id = int(file_name[file_name.rfind('_')+1:])
        trial_stim = [a for a in trial_list if a[0] == trial_id][0][3]

        # this makes up the mat-file name
        matfile_name = 'cond_%s_trial%1.0f.mat' % (trial_stim[trial_stim.rfind(' ')+1:], trial_id)
    else:
        matfile_name = file_name
    
    # create a temporary directory
    temp_dir = tempfile.mkdtemp()

    matfile = '%s%s' % (temp_dir, matfile_name)
    print('Saving file %s' % (matfile_name))
    
    # store variable to be saved in dict
    var_dict = dict()
    var_dict[dataset_name] = A
    
    # save mat-file to temp dir
    savemat(matfile, var_dict)
    
    # upload file to Swift container
    # print('Uploading file %s' % (matfile), end="")
    uploadItems(conn_opts['swift_container'], swift_folder, temp_dir, [matfile], conn_opts)

    # delete temp dir
    shutil.rmtree(temp_dir)
