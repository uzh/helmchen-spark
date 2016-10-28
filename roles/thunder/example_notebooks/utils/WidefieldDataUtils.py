from __future__ import print_function

import numpy as np
from scipy.ndimage.filters import gaussian_filter
import scipy.optimize as opt
from scipy import stats
from scipy.misc import imresize
import h5py
from matplotlib import pylab as plt
import matplotlib.animation as animation
from SwiftStorageUtils import uploadItems
import os
import tempfile
import shutil


def importDCAM(filename, dims, timepoints):
    """
    Import data from DCAM (binary) file and return as 3D numpy array (movie).

    filename ... full path to the DCAM file
    dims ... dimensions of output array (width, height)
    timepoints ... number of timepoints
    """
    with open(filename, 'rb') as fid:
        fid.seek(233)
        A = np.fromfile(fid, dtype='>u2')
#         A = np.fromfile(fid, dtype=np.uint16).byteswap()
    # TODO: consider using np.memmap here
    A = A[:dims[0]*dims[1]*timepoints]
    assert(len(A)==(dims[0]*dims[1]*timepoints))
    mov = np.fliplr(A.reshape([dims[0], dims[1], timepoints], order='F'))
    # hack to remove strange pixels with very high intensity
    mov[np.where(mov > 60000)] = 0
    return mov


def Gaussian2D((x, y), amplitude, xo, yo, sigma_x, sigma_y, theta, offset):
    """
    Return a 2D Gaussian

    This function is used for fitting during background estimation.
    """
    xo = float(xo)
    yo = float(yo)
    a = (np.cos(theta)**2)/(2*sigma_x**2) + (np.sin(theta)**2)/(2*sigma_y**2)
    b = -(np.sin(2*theta))/(4*sigma_x**2) + (np.sin(2*theta))/(4*sigma_y**2)
    c = (np.sin(theta)**2)/(2*sigma_x**2) + (np.cos(theta)**2)/(2*sigma_y**2)
    g = offset + amplitude*np.exp( - (a*((x-xo)**2) + 2*b*(x-xo)*(y-yo)
                            + c*((y-yo)**2)))
    return g.ravel()


def estimateBackground(img, bg_sd_pixel):
    """
    Background estimation for raw widefield data.

    img ... 2D numpy array
    bg_sd_pixel ... SD of gaussion filter in pixel

    Algorithm:
    1. Smooth the image
    2. Perform 2D Gaussian fit
    3. Return the fitted offset as background estimate
    """
    img_smoothed = gaussian_filter(img, bg_sd_pixel)

    # Fit Gaussian to the smoothed image
    # initial guesses
    amplitude = np.max(img_smoothed)
    xo = np.shape(img_smoothed)[0] / 2
    yo = np.shape(img_smoothed)[1] / 2
    sigma_x = np.shape(img_smoothed)[0] / 10
    sigma_y = np.shape(img_smoothed)[1] / 10
    theta = 0
    offset = np.min(img_smoothed)
    initial_guess = (amplitude, xo, yo, sigma_x, sigma_y, theta, offset)

    # Fit
    x = np.linspace(0, img.shape[0]-1, img.shape[0])
    y = np.linspace(0, img.shape[1]-1, img.shape[1])
    x, y = np.meshgrid(x, y)

    popt, pcov = opt.curve_fit(Gaussian2D, (x, y), img_smoothed.ravel(), p0=initial_guess)
    offset_fit = popt[6]
    return offset_fit


def segmentBackground(mov, cutoff=0.0001, plot=False):
    """
    Background segmentation for raw widefield data.

    mov ... 3d numpy array
    cutoff ... histogram threshold for separating background / foreground pixels
    plot ... plot histogram (for debugging)

    Determine black background pixel (outside brain), to be discarded during subsequent analysis.
    Return mov with backfround set to np.nan
    """

    # calculate average image (across frames)
    avg_img = np.mean(mov, axis=2)

    # kernel density estimate (KDE) of average image intensity values
    kernel = stats.gaussian_kde(avg_img.ravel(), bw_method=None)

    positions = np.linspace(0, np.max(avg_img), 500)
    kde_positions = kernel(positions)

    if plot:
        plt.plot(positions, kde_positions)

    # determine cut off for background
    bg_thresh = positions[np.where(kde_positions<cutoff)[0]][0]

    avg_img_masked = avg_img.copy()
    avg_img_masked[avg_img<bg_thresh] = np.nan

    mov[np.isnan(avg_img_masked),:] = np.nan

    return mov


def resizeMovie(mov, resolution, interp='bilinear'):
    """
    Resize all frames in movie to new resolution.
    """
    if not resolution:
        return mov
    if (mov.shape[0] == resolution[0]) and (mov.shape[1] == resolution[1]):
        return mov

    mov_resized = np.empty((resolution[0], resolution[1], mov.shape[2]))
    for iFrame in range(mov.shape[2]):
        mov_resized[:,:,iFrame] = imresize(mov[:,:,iFrame], resolution, interp=interp, mode='F')
    return mov_resized


def importTrialIndices(filename):
    """
    Import trial indices from a mat-file.

    Assume newer (i.e. > v7.3) mat-file which is HDF5-based.
    Return a dictionary with trial types as keys and index arrays as values.
    """
    trial_ind = dict()
    with h5py.File(filename, 'r') as f:
        trial_types = f.keys()
        for trial_type in trial_types:
            trial_ind[trial_type] = f[trial_type][:].astype(int).flatten()
    return trial_ind


def getTrialType(filename, trial_indices):
    """
    Get trial type from file name and index dictionary.
    """
    trial_index = int(filename[filename.rfind('_')+1:])
    for trial_type in trial_indices:
        if np.any(trial_indices[trial_type]==trial_index):
            return trial_type


def importMatlabRois(roi_file, roi_dict, roi_dims, output_dims):
    """
    Import Roi coordinates from Matlab file.

    This function only works for the newer (> v7.3) mat files format that is HDF5 based.
    It returns Roi coordinates in a dictionary with Roi names as keys.

    Args:
        roi_file (str): The full path to the mat-file.
        roi_dict (dict): A dict with Roi names as keys.
        roi_dims (tuple): Dimensions of Rois encoded in mat-file (e.g. (256,256)).
        output_dims (tuple): Output dimensions for Roi coordinates (e.g. (512,512)).

    Returns:
        roi_dict: A dict with Roi names as keys and coordinates as values.
    """
    with h5py.File(roi_file, 'r') as f:
        for roi_name in f.keys():
            if roi_name in roi_dict:
                roi_pixel = f[roi_name][:].astype(int)
                roi_coords = np.unravel_index(roi_pixel, roi_dims)
                # adjust for Matlab 1-based indexing
                row_indices = roi_coords[0] - 1
                col_indices = roi_coords[1] - 1
                # fliplr on the Roi coordinates
                col_indices = col_indices + 2 * (roi_dims[1]/2 - col_indices)
                # create Roi mask and resize as appropriate
                mask = np.zeros(roi_dims)
                mask[row_indices.astype(int), col_indices.astype(int)] = 1
                mask = imresize(mask, output_dims, interp='bilinear', mode='F')

                roi_dict[roi_name] =  np.where(mask>0)
    return roi_dict


def saveMovie(A, trial_type, movie_id, sample_rate, t_axis, file_params):

    mp4_filename = "%s_%s_movie.mp4" % (trial_type, movie_id)
    fig = plt.figure('Average movie')
    ax = fig.add_subplot(111)

    xy = (A.shape[0]/1.05, A.shape[1] - (A.shape[1]/1.1))

    # ims is a list of lists, each row is a list of artists to draw in the
    # current frame; here we are just animating one artist, the image, in
    # each frame
    print("Building movie frames", end="")
    ims = []
    vmin = np.nanmin(A)
    vmax = np.nanmax(A)
    for iFrame in range(A.shape[2]):
        frame =  ax.imshow(A[:,:,iFrame], cmap='jet', animated=True, vmin=vmin, vmax=vmax, interpolation='sinc')
        txt = ax.annotate('%1.2fs' % (t_axis[iFrame]), xy=xy, fontsize=14, color='black', horizontalalignment='right')
        ims.append([frame, txt]) # add both the image and the text to the list of artists

    ani = animation.ArtistAnimation(fig, ims, interval=(1/sample_rate)*1000, repeat_delay=500, blit=True)

    # Set up formatting for the movie files
    Writer = animation.writers['ffmpeg']
    writer = Writer(fps=15, metadata=dict(artist='Me'), bitrate=1800)
    print(" - Done")

    # Save the movie file in a temporary directory
    print("Saving movie", end="")
    temp_dir = tempfile.mkdtemp() + os.path.sep
    mp4_filename = "%s%s" % (temp_dir, mp4_filename)
    ani.save(mp4_filename, writer=writer)
    print(" - Done")

    # Upload to Swift
    print('Uploading file %s' % (mp4_filename))
    uploadItems(file_params['swift_container'], 'animations', temp_dir, [mp4_filename], file_params)

    # delete the temp directory
    shutil.rmtree(temp_dir)

    print("Color scale: %1.2f - %1.2f" % (vmin, vmax))

    plt.close()

    print("Done\n\n")
