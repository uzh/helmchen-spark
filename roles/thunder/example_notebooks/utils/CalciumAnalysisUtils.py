import numpy as np

def psAnalysis(data, stim, frameIx):
    """
    Compute peri-stimulus averages for different stims.
    """
    # figure out unique stims
    stimID = stim[stim>1] # first stim is air, which is ignored
    stimID = np.unique(stimID)
    nUniqueStims = len(np.unique(stimID))
    # collect psData for each stim
    for nStim in stimID:
        stimIx = np.where(stim==nStim)
        stimIx = stimIx[0]
        for ix, nStim2 in enumerate(stimIx):
            startFrame = nStim2 - frameIx[0]
            stopFrame = nStim2 + frameIx[1]
            if ix == 0:
                psData = data[startFrame:stopFrame]
            else:
                psData = np.vstack((psData, data[startFrame:stopFrame]))
        if nStim == np.min(stimID):
            psDataAllStims = [psData]
        else:
            psDataAllStims.append(psData)
    return psDataAllStims


def calculateDff(mov, f0_frames):
    """
    Calculate DF/F0 movie
    dff = ((mov-f0)/f0) * 100
    """
    f0 = np.mean(mov[:,:,f0_frames], axis=2)
    f0 = f0[:, :, np.newaxis]
    dff = ((mov - f0) / f0)
    return dff
