import numpy as np
import h5py

def getFileInfo(h5file):
    f = h5py.File(h5file, 'r')
    nTrials = len(f.keys())
    # assume that dims and time vector do not change, take values from the first trial
    ImageData = f[f.keys()[0]]['NeuralData']['ImageData']
    ImageDataTime = f[f.keys()[0]]['NeuralData']['ImageDataTime']
    # dimensions of data set as tuple
    dsetSz = ImageData.shape
    # sampling frequency
    sampF = 1/(ImageDataTime[1]-ImageDataTime[0])
    f.close()
    return dsetSz, sampF, nTrials


def readPixel_map(ix, h5file, dim=1, debug=False):
    # open file for reading
    f = h5py.File(h5file, 'r')
    for counter, iTrial in enumerate(f.keys()):
        ImageData = f[iTrial]['NeuralData']['ImageData']
        if not counter:
            if dim == 1:
                result = ImageData[:][ix,:]
            elif dim == 2:
                result = ImageData[:][:,ix]
        else:
            if dim == 1:
                result = np.append(result, ImageData[:][ix,:])
            elif dim == 2:
                result = np.append(result, ImageData[:][:, ix])
    if dim == 2:
        result = np.reshape(result, (np.size(result)/len(f), len(f)), order='F')
    if (debug == True) and dim == 1:
        import pylab as plt
        plt.plot(result); # for debugging in notebook
    f.close()
    return (ix, result)


def convert2RDD(sc, h5file, numPartitions=10, dim=1):
    dsetSz, sampF, nTrials = getFileInfo(h5file)
    # setup rdd frames
    frames = sc.parallelize(range(0, dsetSz[dim-1]), numPartitions)
    # read in the data from the HDF5 file into the rdd
    # note that this is lazily executed only once the data has to be accessed
    rdd = frames.map(lambda x: readPixel_map(x, h5file, dim), preservesPartitioning=True)
    # partition the rdd for faster lookup of elements
    rdd = rdd.partitionBy(numPartitions).cache()
    return rdd


def getReferenceImage(h5file, trial=0):
    f = h5py.File(h5file, 'r')
    refImage = f[f.keys()[trial]]['NeuralData']['ReferenceImage'][:]
    f.close()
    return refImage


def getStimData(h5file):
    f = h5py.File(h5file, 'r')
    for counter, iTrial in enumerate(f.keys()):
        stimData_trial = f[iTrial]['StimulusData']['StimulusData_001'][0]
        if not counter:
            stimNames = f[iTrial]['StimulusData']['StimNames_001'][:]
            stimData = stimData_trial
        else:
            stimData = np.append(stimData, stimData_trial)
    f.close()
    return stimData, stimNames
