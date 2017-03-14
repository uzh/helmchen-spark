import re
import dateutil.parser as dparser

def parseBehaviourLog(path_to_file, print_table=False):
    '''
    Parse the behaviour log file and return trial table (one row per trial)
    '''
    import re
    import dateutil.parser as dparser

    p = re.compile('(\S{5,20})\s\t(\S{5,20})\t(\d{1,3})\t')
    trial_list = []
    trial_count = 0
    with open(path_to_file) as fid:
        for line in fid:
            if line.startswith('Date'): # skip line 1
                pass
            else:
                parsed = p.split(line.strip())
                date_time = dparser.parse(parsed[1] + ' ' + parsed[2])
                trial = int(parsed[3])
                descr = parsed[4]
                if descr.startswith('Begin Trial'):
                    trial_count += 1
                    current_trial = trial
                    trial_start = date_time
                elif descr.startswith('Texture'):
                    current_stim = descr
                elif descr == 'Go' or descr == 'No Go' or descr == 'Inappropriate Response':
                    current_decision = descr
                elif descr == 'End Trial':
                    current_trial_list = [trial_count, current_trial, trial_start, current_stim, current_decision]
                    trial_list.append(current_trial_list)
                else:
                    pass
    # print table
    if print_table:
        print 'ID1\tID2\tStartTime\tStimulus\tDecision'
        for i_trial in trial_list:
            print '%1.0f\t%1.0f\t%s\t%s\t%s' % (i_trial[0], i_trial[1], i_trial[2], i_trial[3], i_trial[4])

    return trial_list


def analyzeBehaviourPerformance(trial_list, stim_decision, print_summary=False):
    '''
    Analyze behaviour performance for trials in trial_list and return:
        - number of Go trials
        - number of Nogo trials
        - number of correct responses
        - number of correct rejects
        - number of missed responses
        - number of false alarms
    The mapping of stimulus (i.e. texture) to appropriate decision is defined by stim_decision list, e.g.
        stim_decision = [
            ['Texture 1 P100', 'Go'],
            ['Texture 7 P1200', 'No Go']
            ]
    '''
    # analyse trial list for behavioural performance
    corr_response = 0
    corr_reject = 0
    false_alarm = 0
    miss_response = 0
    go_trials = 0
    nogo_trials = 0
    for i_trial in trial_list:
        current_stim = i_trial[3]
        current_dec = i_trial[4]
        appropriate_decision = [a for a in stim_decision if a[0] == current_stim][0][1]
        if appropriate_decision == 'Go' and current_dec == 'Go':
            go_trials += 1
            # correct response
            corr_response += 1
        if appropriate_decision == 'Go' and current_dec == 'No Go':
            go_trials += 1
            # missed response
            miss_response += 1
        if appropriate_decision == 'No Go' and current_dec == 'No Go':
            nogo_trials += 1
            # correct reject
            corr_reject += 1
        if appropriate_decision == 'No Go' and (current_dec == 'Go' or current_dec == 'Inappropriate Response'):
            nogo_trials += 1
            # false alarm
            false_alarm += 1
    if print_summary:
        print 'Go trials (%s): %1.0f' % ([a[0] for a in stim_decision if a[1] == 'Go'][0], go_trials)
        print 'No Go trials (%s): %1.0f' % ([a[0] for a in stim_decision if a[1] == 'No Go'][0], nogo_trials)
        print 'Correct responses: %1.0f' % (corr_response)
        print 'Correct rejects: %1.0f' % (corr_reject)
        print 'Missed responses: %1.0f' % (miss_response)
        print 'False alarms: %1.0f' % (false_alarm)

    return (go_trials, nogo_trials, corr_response, corr_reject, miss_response, false_alarm)
