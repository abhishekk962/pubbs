import pandas as pd
import numpy as np
import gc
import yaml
from yaml.loader import SafeLoader


pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.precision', 2)



# with open('parameters.yml') as f:
#     data = yaml.load(f, Loader=SafeLoader)

# globals().update(data)

# dob = seatcap * min_c_lvl
# cob = int(seatcap * max_c_lvl)


def schedule(slack,traveltimeDN,departuretimeDN,departuretimeUP, traveltimeUP,pur,lay_overtime):

    slackTimeDN = pd.DataFrame(index=departuretimeDN.index, columns=departuretimeDN.columns)
    for i in range(0, len(departuretimeDN.index)):
        slackTimeDN.iloc[i, 0] = round((slack / 60), 3)

    slackTimeUP = pd.DataFrame(index=departuretimeUP.index, columns=departuretimeUP.columns)
    for i in range(0, len(departuretimeUP.index)):
        slackTimeUP.iloc[i, 0] = round((slack / 60), 3)

    slackTimeUP = slackTimeUP.round(3)
    slackTimeDN = slackTimeDN.round(3)
    # -----------------------------------------

    # -------------------------------------------------------------------------------------------------------------------------------------------------------
    #   Treminal Scheduling ALL DIRECTION
    # -------------------------------------------------------------------------------------------------------------------------------------------------------

    departuretimeDN['TT to Terminal2'] = traveltimeDN

    departuretimeDN['Arr_time T2'] = ""
    departuretimeDN['Slack time T2'] = slackTimeDN
    departuretimeDN['Ready_to_depart T2'] = ""

    departuretimeDN = departuretimeDN[
        ['Departure', 'TT to Terminal2', 'Arr_time T2', 'Slack time T2', 'Ready_to_depart T2']]

    for i in range(0, len(departuretimeDN.index)):
        departuretimeDN.loc[i, 'Arr_time T2'] = (
                    departuretimeDN.loc[i, 'Departure'] + departuretimeDN.loc[i, 'TT to Terminal2']).round(2)

        departuretimeDN.loc[i, 'Ready_to_depart T2'] = (
                    departuretimeDN.loc[i, 'Arr_time T2'] + departuretimeDN.loc[i, 'Slack time T2'] + (
                        lay_overtime / 60)).round(2)

    departuretimeUP['TT to Terminal1'] = traveltimeUP

    departuretimeUP['Arr_time T1'] = ""
    departuretimeUP['Slack time T1'] = slackTimeUP
    departuretimeUP['Ready_to_depart T1'] = ""

    departuretimeUP = departuretimeUP[
        ['Departure', 'TT to Terminal1', 'Arr_time T1', 'Slack time T1', 'Ready_to_depart T1']]

    for i in range(0, len(departuretimeUP.index)):
        departuretimeUP.loc[i, 'Arr_time T1'] = (
                    departuretimeUP.loc[i, 'Departure'] + departuretimeUP.loc[i, 'TT to Terminal1']).round(2)

        departuretimeUP.loc[i, 'Ready_to_depart T1'] = (
                    departuretimeUP.loc[i, 'Arr_time T1'] + departuretimeUP.loc[i, 'Slack time T1'] + (
                        lay_overtime / 60)).round(2)

    departuretimeDN.drop(['Slack time T2', 'TT to Terminal2'], axis=1, inplace=True)
    departuretimeUP.drop(['Slack time T1', 'TT to Terminal1'], axis=1, inplace=True)

    # TERMINAL 1
    # ------------------------------------
    arrivalDN = pd.DataFrame(index=departuretimeUP.index)
    arrivalDN['Dep T1'] = departuretimeUP.index + 1
    arrivalDN['Pool T1'] = 0
    arrivalDN['Dep/Arrival'] = 'Arrival'
    arrivalDN['bus_name'] = ''
    arrivalDN['bus_num'] = ''
    arrivalDN['Time of Dep/Arr'] = departuretimeUP[['Arr_time T1']]
    arrivalDN['Ready_to_depart'] = departuretimeUP[['Ready_to_depart T1']]
    departuretimeDN1 = pd.DataFrame(index=departuretimeDN.index)
    departuretimeDN1['Dep T1'] = departuretimeDN.index + 1
    departuretimeDN1['Pool T1'] = 0
    departuretimeDN1['Dep/Arrival'] = 'Departure'
    departuretimeDN1['bus_name'] = ''
    departuretimeDN1['bus_num'] = ''
    departuretimeDN1['Time of Dep/Arr'] = departuretimeDN['Departure'].round(3)
    departuretimeDN1['Ready_to_depart'] = 0
    #time table for terminal 1
    departuretime1 = pd.concat([departuretimeDN1, arrivalDN], axis=0, ignore_index=True)
    departuretime1 = departuretime1.sort_values(by=['Time of Dep/Arr']).reset_index(drop=True)

    # TERMINAL 2
    # ------------------------------------
    arrivalUP = pd.DataFrame(index=departuretimeDN.index)
    arrivalUP['Dep T2'] = departuretimeDN.index + 1
    arrivalUP['Pool T2'] = 0
    arrivalUP['Dep/Arrival'] = 'Arrival'
    arrivalUP['bus_name'] = ''
    arrivalUP['bus_num'] = ''
    arrivalUP['Time of Dep/Arr'] = departuretimeDN[['Arr_time T2']]
    arrivalUP['Ready_to_depart'] = departuretimeDN[['Ready_to_depart T2']]
    departuretimeUP1 = pd.DataFrame(index=departuretimeUP.index)
    departuretimeUP1['Dep T2'] = departuretimeUP.index + 1
    departuretimeUP1['Pool T2'] = 0
    departuretimeUP1['Dep/Arrival'] = 'Departure'
    departuretimeUP1['bus_name'] = ''
    departuretimeUP1['bus_num'] = ''
    departuretimeUP1['Time of Dep/Arr'] = departuretimeUP['Departure'].round(3)
    departuretimeUP1['Ready_to_depart'] = 0
    # time table for terminal 2
    departuretime2 = pd.concat([departuretimeUP1, arrivalUP], axis=0, ignore_index=True)
    departuretime2 = departuretime2.sort_values(by=['Time of Dep/Arr']).reset_index(drop=True)

    departuretime1['Ready_to_depart'] = departuretime1['Ready_to_depart'].astype('float64')
    departuretime2['Ready_to_depart'] = departuretime2['Ready_to_depart'].astype('float64')
    departuretime1['Time of Dep/Arr'] = departuretime1['Time of Dep/Arr'].astype('float64')
    departuretime2['Time of Dep/Arr'] = departuretime2['Time of Dep/Arr'].astype('float64')
    departuretime1['Fleet T1'] = 0
    departuretime2['Fleet T2'] = 0
    departuretime1['priority'] = 0
    departuretime2['priority'] = 0

    ppt1 = 0
    pool1 = 0
    num_bus_T1 = 0

    ppt2 = 0
    pool2 = 0
    num_bus_T2 = 0

    for i in range(0, len(departuretime1.index)):
        if i == 0:

            departuretime1.loc[i, 'bus_name'] = "A"
            num_bus_T1 = num_bus_T1 + 1
            departuretime1.loc[i, 'bus_num'] = num_bus_T1
            departuretime1.loc[i, 'Fleet T1'] = 1

            departuretime2.loc[i, 'bus_name'] = "B"
            num_bus_T2 = num_bus_T2 + 1
            departuretime2.loc[i, 'bus_num'] = num_bus_T2
            departuretime2.loc[i, 'Fleet T2'] = 1
        elif i < len(departuretime1.index) - 1:
            if departuretime1.loc[i, 'Dep/Arrival'] == 'Departure':
                if departuretime1.loc[i, 'Pool T1'] == 0:  # and departuretime1.loc[:i,'priority' ].max()==0:
                    departuretime1.loc[i, 'bus_name'] = "A"
                    num_bus_T1 = num_bus_T1 + 1
                    departuretime1.loc[i, 'bus_num'] = num_bus_T1
                    departuretime1.loc[i, 'Fleet T1'] = 1
                    departuretime1.loc[i + 1, 'Pool T1'] = departuretime1.loc[i, 'Pool T1']
                else:

                    m = departuretime1['priority'][departuretime1['priority'].gt(0)].min(0)
                    j = departuretime1.index[departuretime1['priority'] == m].tolist()
                    j = j[0]
                    if departuretime1.loc[i, 'Time of Dep/Arr'] < departuretime1.loc[j, 'Ready_to_depart']:
                        departuretime1.loc[i, 'bus_name'] = "A"
                        num_bus_T1 = num_bus_T1 + 1
                        departuretime1.loc[i, 'bus_num'] = num_bus_T1
                        departuretime1.loc[i, 'Fleet T1'] = 1
                        departuretime1.loc[i + 1, 'Pool T1'] = departuretime1.loc[i, 'Pool T1']

                    else:
                        departuretime1.loc[i, 'bus_name'] = departuretime1.loc[j, 'bus_name']
                        departuretime1.loc[i, 'bus_num'] = departuretime1.loc[j, 'bus_num']
                        pool1 = pool1 - 1
                        departuretime1.loc[i, 'Pool T1'] = departuretime1.loc[i, 'Pool T1'] - 1
                        departuretime1.loc[i + 1, 'Pool T1'] = departuretime1.loc[i, 'Pool T1']
                        departuretime1.loc[j, 'priority'] = 0
            else:
                for m in range(0, i):
                    if departuretime2.loc[m, 'Dep T2'] == departuretime1.loc[i, 'Dep T1']:
                        departuretime1.loc[i, 'bus_name'] = departuretime2.loc[m, 'bus_name']
                        departuretime1.loc[i, 'bus_num'] = departuretime2.loc[m, 'bus_num']
                        pool1 = pool1 + 1
                        ppt1 = ppt1 + 1
                        departuretime1.loc[i, 'Pool T1'] = pool1
                        departuretime1.loc[i + 1, 'Pool T1'] = pool1
                        departuretime1.loc[i, 'priority'] = ppt1

                        break
                    else:
                        pass
            if departuretime2.loc[i, 'Dep/Arrival'] == 'Departure':
                if departuretime2.loc[i, 'Pool T2'] == 0:  # and departuretime2.loc[:i,'priority' ].max()==0:
                    departuretime2.loc[i, 'bus_name'] = "B"
                    num_bus_T2 = num_bus_T2 + 1
                    departuretime2.loc[i, 'bus_num'] = num_bus_T2
                    departuretime2.loc[i, 'Fleet T2'] = 1
                    departuretime2.loc[i + 1, 'Pool T2'] = departuretime2.loc[i, 'Pool T2']
                else:
                    m = departuretime2['priority'][departuretime2['priority'].gt(0)].min(0)
                    j = departuretime2.index[departuretime2['priority'] == m].tolist()
                    j = j[0]

                    if departuretime2.loc[i, 'Time of Dep/Arr'] < departuretime2.loc[j, 'Ready_to_depart']:
                        departuretime2.loc[i, 'bus_name'] = "B"
                        num_bus_T2 = num_bus_T2 + 1
                        departuretime2.loc[i, 'bus_num'] = num_bus_T2
                        departuretime2.loc[i, 'Fleet T2'] = 1
                        departuretime2.loc[i + 1, 'Pool T2'] = departuretime2.loc[i, 'Pool T2']
                    else:
                        departuretime2.loc[i, 'bus_name'] = departuretime2.loc[j, 'bus_name']
                        departuretime2.loc[i, 'bus_num'] = departuretime2.loc[j, 'bus_num']
                        pool2 = pool2 - 1
                        departuretime2.loc[i, 'Pool T2'] = departuretime2.loc[i, 'Pool T2'] - 1
                        departuretime2.loc[i + 1, 'Pool T2'] = departuretime2.loc[i, 'Pool T2']
                        departuretime2.loc[j, 'priority'] = 0

            else:

                for m in range(0, i):
                    if departuretime1.loc[m, 'Dep T1'] == departuretime2.loc[i, 'Dep T2']:
                        departuretime2.loc[i, 'bus_name'] = departuretime1.loc[m, 'bus_name']
                        departuretime2.loc[i, 'bus_num'] = departuretime1.loc[m, 'bus_num']
                        pool2 = pool2 + 1
                        ppt2 = ppt2 + 1
                        departuretime2.loc[i, 'Pool T2'] = pool2
                        departuretime2.loc[i + 1, 'Pool T2'] = pool2
                        departuretime2.loc[i, 'priority'] = ppt2

                        break
                    else:
                        pass

        else:
            if departuretime1.loc[i, 'Dep/Arrival'] == 'Arrival':
                for m in range(0, i):
                    if departuretime2.loc[m, 'Dep T2'] == departuretime1.loc[i, 'Dep T1']:
                        departuretime1.loc[i, 'bus_name'] = departuretime2.loc[m, 'bus_name']
                        departuretime1.loc[i, 'bus_num'] = departuretime2.loc[m, 'bus_num']
                        pool1 = pool1 + 1
                        ppt1 = ppt1 + 1
                        departuretime1.loc[i, 'Pool T1'] = pool1

                        departuretime1.loc[i, 'priority'] = ppt1
                    else:
                        pass
            else:
                pass
            if departuretime2.loc[i, 'Dep/Arrival'] == 'Arrival':
                for m in range(0, i):
                    if departuretime1.loc[m, 'Dep T1'] == departuretime2.loc[i, 'Dep T2']:
                        departuretime2.loc[i, 'bus_name'] = departuretime1.loc[m, 'bus_name']
                        departuretime2.loc[i, 'bus_num'] = departuretime1.loc[m, 'bus_num']
                        pool2 = pool2 + 1
                        ppt2 = ppt2 + 1
                        departuretime2.loc[i, 'Pool T2'] = pool2

                        departuretime2.loc[i, 'priority'] = ppt2
                        break
                    else:
                        pass
            else:
                pass

    departuretime1['bus_name'] = departuretime1['bus_name'].map(str) + departuretime1['bus_num'].map(str)
    departuretime2['bus_name'] = departuretime2['bus_name'].map(str) + departuretime2['bus_num'].map(str)

    departuretime1.drop(['bus_num'], axis=1, inplace=True)
    departuretime2.drop(['bus_num'], axis=1, inplace=True)

    departuretime1.drop(['priority', 'Ready_to_depart'], axis=1, inplace=True)
    departuretime2.drop(['priority', 'Ready_to_depart'], axis=1, inplace=True)


    timetable = pd.concat([departuretime1, departuretime2], axis=1, ignore_index=True)
    timetable.columns = ['Dep T1', 'Pool T1', 'Dep/Arrival T1', 'bus_name1',  'Time of Dep/Arr T1',
                             'Fleet T1', 'Dep T2', 'Pool T2', 'Dep/Arrival T2', 'bus_name2',
                             'Time of Dep/Arr T2', 'Fleet T2']
    if pur=='GA':
        pass
    else:
        # VEHICLE SCHEDULING

        # T1 TO T2
        veh_sch1 = pd.DataFrame(index=departuretimeDN.index,
                                columns=['Origin', 'Departure_time', 'Destination', 'Arrival_Time', 'bus_name'])
        veh_sch1['Origin'] = 'T1'
        veh_sch1['Destination'] = 'T2'
        veh_sch1['Departure_time'] = departuretimeDN.loc[:, 'Departure']
        veh_sch1['Arrival_Time'] = departuretimeDN.loc[:, 'Arr_time T2']

        temp_bn = []
        for i in range(0, len(timetable.index)):
            if timetable.loc[i, 'Dep/Arrival T1'] == 'Departure':
                temp_bn.append(timetable.loc[i, 'bus_name1'])

        veh_sch1['bus_name'] = temp_bn
        # T2 TO T1

        veh_sch2 = pd.DataFrame(index=departuretimeUP.index,
                                columns=['Origin', 'Departure_time', 'Destination', 'Arrival_Time', 'bus_name'])
        veh_sch2['Origin'] = 'T2'
        veh_sch2['Destination'] = 'T1'
        veh_sch2['Departure_time'] = departuretimeUP.loc[:, 'Departure']
        veh_sch2['Arrival_Time'] = departuretimeUP.loc[:, 'Arr_time T1']

        temp_bn = []
        for i in range(0, len(timetable.index)):
            if timetable.loc[i, 'Dep/Arrival T2'] == 'Departure':
                temp_bn.append(timetable.loc[i, 'bus_name2'])

        veh_sch2['bus_name'] = temp_bn

        veh_sch = pd.concat([veh_sch1, veh_sch2], axis=0, ignore_index=True)
        veh_sch = veh_sch.sort_values(by=['Departure_time']).reset_index(drop=True)

        bus_name = veh_sch.bus_name.unique()
        j = [veh_sch.iloc[1, :4]]

        d = {}
        for i in range(0, len(bus_name)):
            d[bus_name[i]] = pd.DataFrame(index=np.arange(0),
                                          columns=['Origin', 'Departure_time', 'Destination', 'Arrival_Time'])
            for j in range(0, len(veh_sch.index)):
                if veh_sch.loc[j, 'bus_name'] == bus_name[i]:
                    li = []
                    li.append(veh_sch.iloc[j, 0])
                    li.append(veh_sch.iloc[j, 1])
                    li.append(veh_sch.iloc[j, 2])
                    li.append(veh_sch.iloc[j, 3])

                    d[bus_name[i]].loc[len(d[bus_name[i]])] = li

        reformed_dict = {}
        for outerKey, innerDict in d.items():
            for innerKey, values in innerDict.items():
                reformed_dict[(outerKey,
                               innerKey)] = values

        veh_schedule = pd.DataFrame(reformed_dict)



    for i in range(0, len(departuretime1.index)):
        if departuretime1.loc[i, 'Dep/Arrival'] == 'Arrival':
            departuretime1.loc[i, 'Dep T1'] = "------"
        if departuretime2.loc[i, 'Dep/Arrival'] == 'Arrival':
            departuretime2.loc[i, 'Dep T2'] = "------"


    busreq_at_Terminal1 = timetable['Fleet T1'].sum()
    busreq_at_Terminal2 = timetable['Fleet T2'].sum()
    poolsize_at_Terminal1 = len(departuretimeDN.index) - busreq_at_Terminal1
    poolsize_at_Terminal2 = len(departuretimeDN.index) - busreq_at_Terminal1
    #converting time  in hrs to clock time
    timetable['Time of Dep/Arr T1'] = np.floor(timetable['Time of Dep/Arr T1']) + (
                timetable['Time of Dep/Arr T1'] - (np.floor(timetable['Time of Dep/Arr T1']))) / 100 * 60
    timetable['Time of Dep/Arr T2'] = np.floor(timetable['Time of Dep/Arr T2']) + (
                timetable['Time of Dep/Arr T2'] - (np.floor(timetable['Time of Dep/Arr T2']))) / 100 * 60



    del departuretime2
    del departuretime1
    del ppt1
    del pool1
    del num_bus_T1

    del ppt2
    del pool2
    del num_bus_T2
    del arrivalUP
    del departuretimeUP1
    del arrivalDN
    del departuretimeDN
    del departuretimeUP
    del slackTimeUP
    del slackTimeDN




    gc.collect()

    if pur=='GA':
        return (timetable, busreq_at_Terminal1, busreq_at_Terminal2, poolsize_at_Terminal1, poolsize_at_Terminal2)
    else:
        return (
        timetable, busreq_at_Terminal1, busreq_at_Terminal2, poolsize_at_Terminal1, poolsize_at_Terminal2, veh_sch1,
        veh_sch2, veh_schedule)






