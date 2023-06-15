
import pandas as pd
import numpy as np
import gc
import yaml
from yaml.loader import SafeLoader
import os
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from natsort import natsort_keygen

#Joint optimisation of timetables for 2 routes

#function 1 to generate the timetable for both terminals
def tt1(traveltimeDN,traveltimeUP, departuretimeDN, departuretimeUP, terminalarrivalDN,terminalarrivalUP,A,B):

    # -------------------------------------------------------------------------------------------------------------------------------------------------------
    #   Treminal Scheduling ALL DIRECTION
    # -------------------------------------------------------------------------------------------------------------------------------------------------------
    departuretimeDN['Departure'].round(3)
    departuretimeUP['Departure'].round(3)
    departuretimeDN['Arrival_T1'] = terminalarrivalDN
    departuretimeDN['TT to Terminal2'] = traveltimeDN
    departuretimeDN['Arr_time T2'] = ""
    departuretimeDN = departuretimeDN[
        ['Arrival_T1', 'Departure', 'TT to Terminal2', 'Arr_time T2']]

    for i in range(0, len(departuretimeDN.index)):
        departuretimeDN.loc[i, 'Arr_time T2'] = (
                departuretimeDN.loc[i, 'Departure'] + departuretimeDN.loc[i, 'TT to Terminal2']).round(2)

    departuretimeUP['Arrival_T2'] = terminalarrivalUP
    departuretimeUP['TT to Terminal1'] = traveltimeUP
    departuretimeUP['Arr_time T1'] = ""
    departuretimeUP = departuretimeUP[
        ['Arrival_T2', 'Departure', 'TT to Terminal1', 'Arr_time T1']]

    for i in range(0, len(departuretimeUP.index)):
        departuretimeUP.loc[i, 'Arr_time T1'] = (
                departuretimeUP.loc[i, 'Departure'] + departuretimeUP.loc[i, 'TT to Terminal1']).round(2)

    # TERMINAL 1
    # ------------------------------------
    arrivalDN = pd.DataFrame(index=departuretimeUP.index)
    arrivalDN['Dep'] = departuretimeUP.index + 1
    arrivalDN['Pool'] = 0
    arrivalDN['Dep/Arrival'] = 'Arrival'
    arrivalDN['bus_name'] = ''

    arrivalDN['Time of Arrival'] = departuretimeUP[['Arr_time T1']]
    departuretimeDN1 = pd.DataFrame(index=departuretimeDN.index)
    departuretimeDN1['Dep'] = departuretimeDN.index + 1
    departuretimeDN1['Pool'] = 0
    departuretimeDN1['Dep/Arrival'] = 'Departure'
    departuretimeDN1['bus_name'] = ''
    departuretimeDN1['Departure_time'] = departuretimeDN['Departure'].round(3)
    departuretimeDN1['Time of Arrival'] = departuretimeDN['Arrival_T1'].round(3)
    # time table for terminal 1
    tt_terminal1 = pd.concat([departuretimeDN1, arrivalDN], axis=0, ignore_index=True)
    tt_terminal1 = tt_terminal1.sort_values(by=['Time of Arrival']).reset_index(drop=True)

    # TERMINAL 2
    # ------------------------------------
    arrivalUP = pd.DataFrame(index=departuretimeDN.index)
    arrivalUP['Dep'] = departuretimeDN.index + 1
    arrivalUP['Pool'] = 0
    arrivalUP['Dep/Arrival'] = 'Arrival'
    arrivalUP['bus_name'] = ''

    arrivalUP['Time of Arrival'] = departuretimeDN[['Arr_time T2']]
    departuretimeUP1 = pd.DataFrame(index=departuretimeUP.index)
    departuretimeUP1['Dep'] = departuretimeUP.index + 1
    departuretimeUP1['Pool'] = 0
    departuretimeUP1['Dep/Arrival'] = 'Departure'
    departuretimeUP1['bus_name'] = ''
    departuretimeUP1['Departure_time'] = departuretimeUP['Departure'].round(3)
    departuretimeUP1['Time of Arrival'] = departuretimeUP['Arrival_T2'].round(3)

    # time table for terminal 2
    tt_terminal2 = pd.concat([departuretimeUP1, arrivalUP], axis=0, ignore_index=True)
    tt_terminal2 = tt_terminal2.sort_values(by=['Time of Arrival']).reset_index(drop=True)

    tt_terminal1['Time of Arrival'] = tt_terminal1['Time of Arrival'].astype('float64')
    tt_terminal2['Time of Arrival'] = tt_terminal2['Time of Arrival'].astype('float64')
    tt_terminal1['Fleet'] = 0
    tt_terminal2['Fleet'] = 0

    # T1 TO T2--------------------------------------------------------------------------------------------------------------
    # veh_sch1= schedule of vehicles starting from terminal 1
    veh_sch1 = pd.DataFrame(index=departuretimeDN.index,
                            columns=['bus_name', 'start', 'end', 'remarks'])
    veh_sch1['start'] = departuretimeDN['Arrival_T1']  # time at which bus arrives at origin for a trip
    veh_sch1['end'] = departuretimeDN['Arr_time T2']  # time at which bus arrives at destination end of the trip
    veh_sch1['remarks'] = A + '_to_' + B
    # T2 TO T1--------------------------------------------------------------------------------------------------------------
    # veh_sch2= schedule of vehicles starting from terminal 2
    veh_sch2 = pd.DataFrame(index=departuretimeUP.index,
                            columns=['bus_name', 'start', 'end', 'remarks'])
    veh_sch2['remarks'] = B + '_to_' + A
    veh_sch2['start'] = departuretimeUP['Arrival_T2']
    veh_sch2['end'] = departuretimeUP['Arr_time T1']


    return(tt_terminal1,tt_terminal2,veh_sch1,veh_sch2)


#function 2 to generate vehicle assignement for both timetables
def schedule(r1_terminal1,r1_terminal2, r1_veh_sch1,r1_veh_sch2,r2_terminal1,r2_terminal2, r2_veh_sch1,r2_veh_sch2,data,r1_ttDN, r1_ttUP,r2_ttDN, r2_ttUP):

    globals().update(data)


    num_bus_T = 0

    depot_pool = pd.DataFrame(index=np.arange(0),
                              columns=['bus_name', 'departure_to_depo', 'from_terminal', 'TT_depot', 'layover',
                                       'TT_terminal1', 'TT_terminal2', 'nxt_shift'])
    depot_tt = pd.DataFrame(index=np.arange(0),
                            columns=['bus_name', 'departure_to_depo','departure_from_depo', 'terminal_arrival', 'terminal'])
    laydf1 = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'start', 'end', 'remarks'])
    fleet = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'shift_no', 'start_shift1', 'end_shift', 'crew'])

    r1pool_t1 = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'Ready_to_depart'])
    r1pool_t2 = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'Ready_to_depart'])
    r2pool_t1 = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'Ready_to_depart'])
    r2pool_t2 = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'Ready_to_depart'])

    #vehiclle assignment
    if len(r1_terminal1.index)>len(r2_terminal2.index):
        le=len(r1_terminal1.index)
    else:
        le=len(r2_terminal1.index)

    for i in range(0, le):
        for k in range(0, 2): #2 = number of terminals

            if k == 0: #1st route details
                tt_terminal1 = r1_terminal1
                tt_terminal2 = r1_terminal2
                pool_t1 = r1pool_t1
                pool_t2 = r1pool_t2
                ttDN = r1_ttDN
                ttUP = r1_ttUP
                dead_todepot_t1 = dead_todepot_r1t1
                dead_todepot_t2 = dead_todepot_r1t2
                bus_name = 'R00'
                if i < len(r1_terminal1.index) :
                    pass
                else:
                    break
            elif k==1: #1= 2nd route details
                tt_terminal1 = r2_terminal1
                tt_terminal2 = r2_terminal2
                pool_t1 = r2pool_t1
                pool_t2 = r2pool_t2
                ttDN = r2_ttDN
                ttUP = r2_ttUP
                dead_todepot_t1 = dead_todepot_r2t1
                dead_todepot_t2 = dead_todepot_r2t2
                bus_name = 'R00'
                if i < len(r2_terminal1.index):
                    pass
                else:
                    break
            else:
                pass
            for j in range(0, 2):

                if j == 0:
                    or_terminal = tt_terminal1
                    des_terminal = tt_terminal2
                    pool = pool_t1
                    traveltime = ttDN
                else:
                    or_terminal = tt_terminal2
                    des_terminal = tt_terminal1
                    pool = pool_t2
                    traveltime = ttUP

                if or_terminal.loc[i, 'Dep/Arrival'] == 'Departure':
                    # CHECK FOR BUSES TO RETURN TO DEPOT AFTER A SHIFT
                    temp_pool = pool[pool['Ready_to_depart'] <= or_terminal.loc[i, 'Time of Arrival']]
                    max = or_terminal.loc[i, 'Departure_time'] + traveltime.iloc[or_terminal.loc[i, 'Dep'] - 1, 0]

                    if len(temp_pool.index) > 0 and max >= fleet.loc[0, 'end_shift']:
                        pl_dropidx = []
                        for ind in range(0, len(temp_pool.index)):
                            k = temp_pool.index[ind]
                            y1 = fleet[fleet['bus_name'] == temp_pool.loc[k, 'bus_name']].copy()
                            y1.sort_values(by=['shift_no'], ascending=False, inplace=True)
                            y1.reset_index(drop=True, inplace=True)

                            if len(y1.index) > 0:
                                y1 = y1[:1]

                                x1 = or_terminal.loc[i, 'Departure_time'] + traveltime.iloc[
                                    or_terminal.loc[i, 'Dep'] - 1, 0]

                                if x1 >= y1.loc[0, 'end_shift']:
                                    bus_name_d = temp_pool.loc[k, 'bus_name']
                                    departure_to_depo = or_terminal.loc[i, 'Departure_time']
                                    from_terminal = 'T1'
                                    if j == 0:
                                        arrival_depot = dead_todepot_t1 + departure_to_depo
                                    else:
                                        arrival_depot = dead_todepot_t2 + departure_to_depo

                                    depo_layover = layover_depot / 60
                                    departure_from_depo = arrival_depot + depo_layover
                                    TTdepo_ter1 = arrival_depot + depo_layover + dead_todepot_t1
                                    TTdepo_ter2 = arrival_depot + depo_layover + dead_todepot_t2
                                    shift_nxt = y1.loc[0, 'shift_no'] + 1
                                    depot_pool.loc[len(depot_pool.index)] = [bus_name_d, departure_to_depo,
                                                                             from_terminal,
                                                                             arrival_depot, depo_layover, TTdepo_ter1,
                                                                             TTdepo_ter2, shift_nxt]
                                    depot_tt.loc[len(depot_tt.index)] = [bus_name_d, departure_to_depo,
                                                                         departure_from_depo,
                                                                         22, 0]
                                    pl_dropidx.append(k)

                                else:
                                    pass
                        pool.drop(index=pl_dropidx, inplace=True)
                        pool.reset_index(drop=True, inplace=True)
                    # ------------------------------------------------------------------------------------------
                    # CHECK THE AVALIABLE BUSES IN THE POOL

                    temp_pool = pool[pool['Ready_to_depart'] <= or_terminal.loc[i, 'Time of Arrival']]
                    temp_pool.reset_index(drop=True, inplace=True)
                    if len(temp_pool.index) == 0:
                        if j == 0:
                            temp_depool = depot_pool[
                                depot_pool['TT_terminal1'] < tt_terminal1.loc[i, 'Time of Arrival']].copy()
                            temp_depool.sort_values(by=['TT_terminal1'], ascending=True, inplace=True)
                            temp_depool.reset_index(drop=True, inplace=True)
                        else:
                            temp_depool = depot_pool[
                                depot_pool['TT_terminal2'] < tt_terminal2.loc[i, 'Time of Arrival']].copy()
                            temp_depool.sort_values(by=['TT_terminal2'], ascending=True, inplace=True)
                            temp_depool.reset_index(drop=True, inplace=True)

                        if len(temp_depool.index) == 0:  # check for bus in depot pool
                            or_terminal.loc[i, 'bus_name'] = bus_name + str(num_bus_T)
                            num_bus_T = num_bus_T + 1
                            or_terminal.loc[i, 'Fleet'] = 1
                            shift_str = np.floor(or_terminal.loc[i, 'Time of Arrival'])
                            shift_end = np.floor(shift + tt_terminal1.loc[i, 'Time of Arrival'])
                            if shift_end > end_ser:
                                shift_end = end_ser + 2
                            else:
                                pass
                            shift_no = 1
                            or_terminal.loc[i, 'Pool'] = len(temp_pool.index)
                        else:
                            or_terminal.loc[i, 'bus_name'] = temp_depool.loc[0, 'bus_name']
                            or_terminal.loc[i, 'Fleet'] = 0

                            if j == 0:
                                shift_str = np.floor(temp_depool.loc[0, 'TT_terminal1'])
                                depot_tt.loc[(depot_tt['bus_name'] == temp_depool.loc[0, 'bus_name']) & (
                                        depot_tt['departure_to_depo'] == temp_depool.loc[
                                    0, 'departure_to_depo']), 'terminal_arrival'] = temp_depool.loc[
                                    0, 'TT_terminal1']

                                depot_tt.loc[(depot_tt['bus_name'] == temp_depool.loc[0, 'bus_name']) & (
                                        depot_tt['departure_to_depo'] == temp_depool.loc[
                                    0, 'departure_to_depo']), 'terminal'] = 'T1'

                            else:
                                shift_str = np.floor(temp_depool.loc[0, 'TT_terminal2'])
                                depot_tt.loc[(depot_tt['bus_name'] == temp_depool.loc[0, 'bus_name']) & (
                                        depot_tt['departure_to_depo'] == temp_depool.loc[
                                    0, 'departure_to_depo']), 'terminal_arrival'] = temp_depool.loc[
                                    0, 'TT_terminal2']

                                depot_tt.loc[(depot_tt['bus_name'] == temp_depool.loc[0, 'bus_name']) & (
                                        depot_tt['departure_to_depo'] == temp_depool.loc[
                                    0, 'departure_to_depo']), 'terminal'] = 'T2'

                            shift_end = np.floor(shift + or_terminal.loc[i, 'Time of Arrival'])
                            if shift_end > end_ser:
                                shift_end = end_ser + 2
                            else:
                                pass
                            shift_no = temp_depool.loc[0, 'nxt_shift']

                            depot_pool.drop(depot_pool[depot_pool['bus_name'] == temp_depool.loc[0, 'bus_name']].index,
                                            inplace=True)

                            depot_pool.reset_index(drop=True, inplace=True)
                            or_terminal.loc[i, 'Pool'] = len(temp_pool.index)

                        fleet.loc[len(fleet.index)] = [or_terminal.loc[i, 'bus_name'], shift_no,
                                                       shift_str, shift_end, crewperbus]

                    else:
                        # random selection from terminal pool
                        random_selc = np.random.randint(0, len(temp_pool.index), 1)
                        k = random_selc[0]
                        or_terminal.loc[i, 'bus_name'] = temp_pool.loc[k, 'bus_name']
                        pool.drop(pool[pool['bus_name'] == temp_pool.loc[k, 'bus_name']].index, inplace=True)
                        pool.reset_index(drop=True, inplace=True)
                        or_terminal.loc[i, 'Pool'] = len(temp_pool.index)

                else:
                    df2 = des_terminal[des_terminal['Dep'] == or_terminal.loc[i, 'Dep']]
                    df2 = df2[df2['Dep/Arrival'] == 'Departure'].copy()
                    df2.reset_index(drop=True, inplace=True)
                    or_terminal.loc[i, 'bus_name'] = df2.loc[0, 'bus_name']
                    ready_for_depart = or_terminal.loc[i, 'Time of Arrival'] + (lay_overtime + slack) / 60
                    if j == 0:
                        x2 = 'layover T1'
                    else:
                        x2 = 'layover T2'
                    laydf1.loc[len(laydf1.index)] = [or_terminal.loc[i, 'bus_name'],
                                                     or_terminal.loc[i, 'Time of Arrival'], ready_for_depart, x2]
                    pool.loc[len(pool.index)] = [or_terminal.loc[i, 'bus_name'], ready_for_depart]
                    temp_pool = pool[pool['Ready_to_depart'] <= or_terminal.loc[i, 'Time of Arrival']]
                    or_terminal.loc[i, 'Pool'] = len(temp_pool.index)




    r1_timetable = pd.concat([r1_terminal1,r1_terminal2], axis=1, ignore_index=True)
    r1_timetable.columns = ['Dep T1', 'Pool T1', 'Dep/Arrival T1', 'bus_name1', 'Departure_from_T1', 'Time of Arr T1',
                         'Fleet T1', 'Dep T2', 'Pool T2', 'Dep/Arrival T2', 'bus_name2', 'Departure_from_T2',
                         'Time of Arr T2', 'Fleet T2']
    r2_timetable = pd.concat([r2_terminal1, r2_terminal2], axis=1, ignore_index=True)
    r2_timetable.columns = ['Dep T1', 'Pool T1', 'Dep/Arrival T1', 'bus_name1', 'Departure_from_T1', 'Time of Arr T1',
                            'Fleet T1', 'Dep T2', 'Pool T2', 'Dep/Arrival T2', 'bus_name2', 'Departure_from_T2',
                            'Time of Arr T2', 'Fleet T2']

    # CREW SCHEDULING---------------------
    total_crew = fleet['crew'].sum()

    crew = pd.DataFrame(index=np.arange(0), columns=['Time', 'Crew', 'buses to be dispatched '])
    time_period = start_ser - 1
    for i in range(start_ser - 1, end_ser):
        df5 = fleet[fleet['start_shift1'] == i]
        bus = df5.loc[:, 'bus_name'].tolist()
        crew_hr = df5['crew'].sum()
        time = str(i + .00) + '-' + str(i + .59)
        crew.loc[len(crew.index)] = [time, crew_hr, bus]


    # VEHICLE SCHEDULE GENERATION
    #ROUTE 1
    # T1 TO T2-------------------------------------------------------------
    temp_bn = []
    for i in range(0, len(r1_timetable.index)):
        if r1_timetable.loc[i, 'Dep/Arrival T1'] == 'Departure':
            temp_bn.append(r1_timetable.loc[i, 'bus_name1'])

    r1_veh_sch1['bus_name'] = temp_bn
    # T2 TO T1-------------------------------------------------------------
    temp_bn = []
    for i in range(0, len(r1_timetable.index)):
        if r1_timetable.loc[i, 'Dep/Arrival T2'] == 'Departure':
            temp_bn.append(r1_timetable.loc[i, 'bus_name2'])
    r1_veh_sch2['bus_name'] = temp_bn
    # ROUTE 2
    # T1 TO T2-------------------------------------------------------------
    temp_bn = []
    for i in range(0, len(r2_timetable.index)):
        if r2_timetable.loc[i, 'Dep/Arrival T1'] == 'Departure':
            temp_bn.append(r2_timetable.loc[i, 'bus_name1'])

    r2_veh_sch1['bus_name'] = temp_bn
    # T2 TO T1-------------------------------------------------------------
    temp_bn = []
    for i in range(0, len(r2_timetable.index)):
        if r2_timetable.loc[i, 'Dep/Arrival T2'] == 'Departure':
            temp_bn.append(r2_timetable.loc[i, 'bus_name2'])
    r2_veh_sch2['bus_name'] = temp_bn


    depott = depot_tt[['bus_name', 'departure_to_depo', 'terminal_arrival']].copy()
    depott['remarks'] = 'shift'
    depott.columns = ['bus_name', 'start', 'end', 'remarks']
    veh_sch = pd.concat([r1_veh_sch1, r1_veh_sch2,r2_veh_sch1, r2_veh_sch2, depott, laydf1], axis=0, ignore_index=True)
    veh_sch = veh_sch.sort_values(by=['start']).reset_index(drop=True)
    bus_name = veh_sch.bus_name.unique()
    d = {}

    # start of a trip = arrival of the bus at origin terminal
    veh_schedule = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'No:', 'start', 'end', 'remarks', 'bus_@'])
    b_lst = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'No: of trips', 'Ideal time'])
    for i in range(0, len(bus_name)):
        no_trips = 0
        df3 = veh_sch[veh_sch['bus_name'] == bus_name[i]].copy()
        df3.reset_index(drop=True, inplace=True)
        for j in range(0, len(df3.index)):
            if df3.iloc[j, 3] == A1 + '_to_' + B1 or df3.iloc[j, 3] == B1 + '_to_' + A1 or A2 + '_to_' + B2 or df3.iloc[j, 3] == B2 + '_to_' + A2:
                no_trips = no_trips + 1
                nn = no_trips
            else:
                nn = '_____'
            if df3.iloc[j, 3] == A1 + '_to_' + B1:
                dist = dead_todepot_r1t1
            elif df3.iloc[j, 3] == B1 + '_to_' + A1:
                dist = dead_todepot_r1t2
            elif df3.iloc[j, 3] == A2 + '_to_' + B2:
                dist = dead_todepot_r2t1
            elif df3.iloc[j, 3] == B2 + '_to_' + A2:
                dist = dead_todepot_r2t2
            else:
                pass
            if df3.loc[j, 'remarks'] == 'layover T2' or df3.loc[j, 'remarks'] == 'layover T1':
                pass
            else:
                if j == 0:
                    if df3.loc[j, 'start'] < start_ser:

                        tp_start = df3.loc[j, 'start'] - dist
                        tp_end = df3.loc[j, 'start']
                        remark = 'shift'
                        veh_schedule.loc[len(veh_schedule)] = [bus_name[i], '_____', tp_start, tp_end, remark, '---']

                    else:
                        tp_start = df3.loc[j, 'start'] - dist
                        tp_end = df3.loc[j, 'start']
                        tpremark = 'shift'
                        Idl_start = start_ser
                        Idl_end = tp_start
                        remark = 'ideal'
                        veh_schedule.loc[len(veh_schedule)] = [bus_name[i], '_____', Idl_start, Idl_end, remark, 'Depo']
                        veh_schedule.loc[len(veh_schedule)] = [bus_name[i], '_____', tp_start, tp_end, tpremark, '---']
                else:
                    Idl_start = df3.loc[j - 1, 'end']
                    Idl_end = df3.loc[j, 'start']
                    remark = 'ideal'
                    if df3.loc[j - 1, 'remarks'] == 'layover T1':
                        x3 = 'T1'
                    elif df3.loc[j - 1, 'remarks'] == 'layover T2':
                        x3 = 'T2'
                    elif df3.loc[j, 'remarks'] == A1 + '_to_' + B1:
                        x3 = 'T1'
                    elif df3.loc[j, 'remarks'] == A2 + '_to_' + B2:
                        x3 = 'T1'
                    elif df3.loc[j, 'remarks'] == B1 + '_to_' + A1:
                        x3 = 'T2'
                    elif df3.loc[j, 'remarks'] == B2 + '_to_' + A2:
                        x3 = 'T2'
                    else:
                        pass
                    veh_schedule.loc[len(veh_schedule)] = [bus_name[i], '_____', Idl_start, Idl_end, remark, x3]
            veh_schedule.loc[len(veh_schedule)] = [df3.iloc[j, 0], nn, df3.iloc[j, 1], df3.iloc[j, 2],
                                                   df3.iloc[j, 3], '---']

        if df3.loc[len(df3.index) - 1, 'end'] >= end_ser:
            pass
        else:
            Idl_start = df3.loc[j - 1, 'end']
            Idl_end = end_ser
            remark = 'ideal'
            if df3.loc[j - 1, 'remarks'] == 'layover T1':
                x3 = 'T1'
            elif df3.loc[j - 1, 'remarks'] == 'layover T2':
                x3 = 'T2'
            elif df3.loc[j, 'remarks'] == A1 + '_to_' + B1:
                x3 = 'T1'
            elif df3.loc[j, 'remarks'] == A2 + '_to_' + B2:
                x3 = 'T1'
            elif df3.loc[j, 'remarks'] == B1 + '_to_' + A1:
                x3 = 'T2'
            elif df3.loc[j, 'remarks'] == B2 + '_to_' + A2:
                x3 = 'T2'
            else:
                pass
            veh_schedule.loc[len(veh_schedule)] = [bus_name[i], '----', Idl_start, Idl_end, remark, x3]

    veh_schedule.sort_values(by=['bus_name','start'], inplace=True, key=natsort_keygen())
    veh_schedule.reset_index(drop=True, inplace=True)
    visual_sched = veh_schedule[['bus_name', 'start', 'end', 'remarks']].copy()
    visual_sched = visual_sched[(visual_sched['remarks'] != 'ideal')]
    visual_sched.loc[visual_sched['remarks'] == 'layover T2', 'remarks'] = 'layover'
    visual_sched.loc[visual_sched['remarks'] == 'layover T1', 'remarks'] = 'layover'

    b_lst = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'No: of trips', 'Ideal time'])
    bus_name = veh_schedule.bus_name.unique()
    for i in range(0, len(bus_name)):
        df3 = veh_schedule[(veh_schedule['bus_name'] == bus_name[i])].copy()
        df4 = df3[df3['remarks'] == 'ideal'].copy()
        df4['dur'] = df4.end - df4.start
        ideal_time = df4['dur'].sum()
        df2 = df3[(df3['remarks'] == A1 + '_to_' + B1) | (df3['remarks'] == A2 + '_to_' + B2) | (
                    df3['remarks'] == B1 + '_to_' + A1) | (df3['remarks'] == B2 + '_to_' + A2)]
        no_trips = len(df2.index)
        b_lst.loc[len(b_lst)] = [bus_name[i], no_trips, ideal_time]

    # Ideal time calculations
    ideal = veh_schedule[(veh_schedule['remarks'] == 'ideal')].copy()
    ideal['Idl_Duration'] = ideal.end - ideal.start
    r_bus = ideal[ideal['Idl_Duration'] > max_ideal]
    r_bus.reset_index(drop=True, inplace=True)

    # Visualisation of bus schedule
    visual_resuse = r_bus[['bus_name', 'start', 'end']].copy()
    visual_resuse['remarks'] = 'Ideal<'+str(max_ideal)+'hrs'
    visual_resuse.columns = ['bus_name', 'start', 'end', 'legend']
    visual_sched.columns = ['bus_name', 'start', 'end', 'legend']
    visual_sched = pd.concat([visual_sched, visual_resuse], axis=0, ignore_index=True)
    visual_sched['Duration'] = visual_sched.end - visual_sched.start

    def color(row):


        c_dict = {A2 + '_to_' + B2: '#ccccff', B2 + '_to_' + A2: '#cc99ff', 'Ideal<'+str(max_ideal)+'hrs': '#309c00',
                      'layover': '#ada55c',
                      'shift': '#00f7ff', A1 + '_to_' + B1: '#E64646', B1 + '_to_' + A1: '#ffb957'}
        return c_dict[row['legend']]

    visual_sched['color'] = visual_sched.apply(color, axis=1)

    fig, ax = plt.subplots(1, figsize=(16, 10))
    plt.xlim(5, 24)

    ax.barh(visual_sched.bus_name, visual_sched.Duration, left=visual_sched.start, color=visual_sched.color,
            height=0.2)
    # Legend

    c_dict = {A2 + '_to_' + B2: '#ccccff', B2 + '_to_' + A2: '#cc99ff', 'Ideal<'+str(max_ideal)+'hrs': '#309c00', 'layover': '#ada55c',
                  'shift': '#00f7ff', A1 + '_to_' + B1: '#E64646', B1 + '_to_' + A1: '#ffb957'}
    legend_elements = [Patch(facecolor=c_dict[i], label=i) for i in c_dict]
    plt.legend(handles=legend_elements)

    # TEXT
    for idx, row in visual_sched.iterrows():
        ax.text(row.end + 0.01, row.bus_name, row.end, va='center', alpha=0.8, fontsize=3)
        ax.text(row.start - 0.01, row.bus_name, row.start, va='center', ha='right', alpha=0.8, fontsize=3)

    #plt.grid()
    plt.tight_layout()

    return (r1_timetable,r2_timetable,crew,b_lst,r_bus,veh_schedule,fig,fleet)

def tt_det(timetable):
    # veh_schedule.set_index(['bus_name', 'No:'], drop=True, inplace=True)

    for i in range(0, len(timetable.index)):
        if timetable.loc[i, 'Dep/Arrival T1'] == 'Arrival':
            timetable.loc[i, 'Dep T1'] = "------"
        if timetable.loc[i, 'Dep/Arrival T2'] == 'Arrival':
            timetable.loc[i, 'Dep T2'] = "------"
    timetable['Departure_from_T1'].fillna('----', inplace=True)
    timetable['Departure_from_T2'].fillna('----', inplace=True)

    # converting time  in hrs to clock time

    # timetable['Departure_from_T1'] = np.floor(timetable['Departure_from_T1']) + (
    # timetable['Departure_from_T1'] - (np.floor(timetable['Departure_from_T1']))) / 100 * 60
    timetable['Time of Arr T1'] = np.floor(timetable['Time of Arr T1']) + (
            timetable['Time of Arr T1'] - (np.floor(timetable['Time of Arr T1']))) / 100 * 60
    # timetable['Departure_from_T2'] = np.floor(timetable['Departure_from_T2']) + (
    # timetable['Departure_from_T2'] - (np.floor(timetable['Departure_from_T2']))) / 100 * 60
    timetable['Time of Arr T2'] = np.floor(timetable['Time of Arr T2']) + (
            timetable['Time of Arr T2'] - (np.floor(timetable['Time of Arr T2']))) / 100 * 60
    timetable.drop(['Departure_from_T1', 'Departure_from_T2'], axis=1, inplace=True)

    return(timetable)

def main_schedule(r1_ttDN, r1_ttUP, r1_dtimeDN, r1_dtimeUP, r1_tarrivalDN,r1_tarrivalUP,r2_ttDN, r2_ttUP, r2_dtimeDN, r2_dtimeUP, r2_tarrivalDN,r2_tarrivalUP,data):

    globals().update(data)

    r1_terminal1, r1_terminal2, r1_veh_sch1, r1_veh_sch2 = tt1(r1_ttDN, r1_ttUP, r1_dtimeDN, r1_dtimeUP, r1_tarrivalDN,r1_tarrivalUP, A1, B1)

    r2_terminal1, r2_terminal2, r2_veh_sch1, r2_veh_sch2 = tt1(r2_ttDN, r2_ttUP, r2_dtimeDN, r2_dtimeUP, r2_tarrivalDN,r2_tarrivalUP, A2, B2)

    (r1_timetable, r2_timetable, crew, b_lst, r_bus, veh_schedule, fig,fleet) = schedule(r1_terminal1, r1_terminal2,
                                                                                        r1_veh_sch1, r1_veh_sch2,
                                                                                        r2_terminal1,
                                                                                        r2_terminal2, r2_veh_sch1,
                                                                                        r2_veh_sch2, data,r1_ttDN, r1_ttUP,r2_ttDN, r2_ttUP)
    r1_timetable = tt_det(r1_timetable)
    r2_timetable = tt_det(r2_timetable)
    
    return r1_timetable, r2_timetable, crew, b_lst, r_bus, veh_schedule, fig,fleet

def main():
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.precision', 2)

    with open('parameters.yml') as f:
        data = yaml.load(f, Loader=SafeLoader)

    # ROUTE 1
    r1_ttDN = pd.read_csv(r'timetable\timetable1\Input_files_holding\travel_time_totDN.csv')
    r1_ttUP = pd.read_csv(r'timetable\timetable1\Input_files_holding\travel_time_totUP.csv')
    r1_dtimeDN = pd.read_csv(r'timetable\timetable1\Input_files_holding\departuretimeDN.csv')
    r1_dtimeUP = pd.read_csv(r'timetable\timetable1\Input_files_holding\departuretimeUP.csv')
    r1_tarrivalDN = pd.read_csv(r'timetable\timetable1\Input_files_holding\stoparrivalDN.csv')
    r1_tarrivalDN = r1_tarrivalDN.iloc[:, 0]
    r1_tarrivalUP = pd.read_csv(r'timetable\timetable1\Input_files_holding\stoparrivalUP.csv')
    r1_tarrivalUP = r1_tarrivalUP.iloc[:, 0]

    # ROUTE 2
    r2_ttDN = pd.read_csv(r'timetable\timetable2\Input_files_holding\travel_time_totDN.csv')
    r2_ttUP = pd.read_csv(r'timetable\timetable2\Input_files_holding\travel_time_totUP.csv')
    r2_dtimeUP = pd.read_csv(r'timetable\timetable2\Input_files_holding\departuretimeUP.csv')
    r2_dtimeDN = pd.read_csv(r'timetable\timetable2\Input_files_holding\departuretimeDN.csv')
    r2_tarrivalDN = pd.read_csv(r'timetable\timetable2\Input_files_holding\stoparrivalDN.csv')
    r2_tarrivalDN = r2_tarrivalDN.iloc[:, 0]
    r2_tarrivalUP = pd.read_csv(r'timetable\timetable2\Input_files_holding\stoparrivalUP.csv')
    r2_tarrivalUP = r2_tarrivalUP.iloc[:, 0]

    details_tt=pd.DataFrame(index=np.arange(0), columns=['Iteration no:', 'Ideal time'])
    no=10 #number of timetables to be generated for optimisation

    for i in range(0,no):
        print(i)

        r1_terminal1, r1_terminal2, r1_veh_sch1, r1_veh_sch2 = tt1(r1_ttDN, r1_ttUP, r1_dtimeDN, r1_dtimeUP, r1_tarrivalDN,
                                                                r1_tarrivalUP, A1, B1)

        r2_terminal1, r2_terminal2, r2_veh_sch1, r2_veh_sch2 = tt1(r2_ttDN, r2_ttUP, r2_dtimeDN, r2_dtimeUP, r2_tarrivalDN,
                                                                r2_tarrivalUP, A2, B2)

        (r1_timetable, r2_timetable, crew, b_lst, r_bus, veh_schedule, fig,fleet) = schedule(r1_terminal1, r1_terminal2,
                                                                                            r1_veh_sch1, r1_veh_sch2,
                                                                                            r2_terminal1,
                                                                                            r2_terminal2, r2_veh_sch1,
                                                                                            r2_veh_sch2, data,r1_ttDN, r1_ttUP,r2_ttDN, r2_ttUP)

        # tot_ideal_time = b_lst['Ideal time'].sum() - r_bus['Idl_Duration'].sum() Use this if ideal time > max ideal needs to be subtracted
        tot_ideal_time = b_lst['Ideal time'].sum()
        r1_timetable = tt_det(r1_timetable)
        r2_timetable = tt_det(r2_timetable)
        # FILE EXPORT
        name = "Time_Table " + str(i)
        path = r'timetable\multiline_meth2\Random{}'.format(name)
        isExist = os.path.exists(path)

        if not isExist:
            # Create a new directory because it does not exist
            os.makedirs(path)

        r1_timetable.to_csv(r'timetable\multiline_meth2\Random{}\R1_tt.csv'.format(name))
        r2_timetable.to_csv(r'timetable\multiline_meth2\Random{}\R2_tt.csv'.format(name))
        details_tt.loc[len(details_tt)] = [i, tot_ideal_time.round(0)]
        
        if i ==0:
            min_ideal= tot_ideal_time
            path =r'timetable\multiline_meth2\Results\vehicleschedule'
            isExist = os.path.exists(path)
            if not isExist:
                # Create a new directory because it does not exist
                os.makedirs(path)
            r1_timetable.to_csv(r'timetable\multiline_meth2\Results\Time_Table.csv', index=False)
            r2_timetable.to_csv(r'timetable\multiline_meth2\Results\Time_Table.csv', index=False)
            veh_schedule.to_csv(r'timetable\multiline_meth2\Results\vehicle_schedule.csv', index=False)
            crew.to_csv(r'timetable\multiline_meth2\Results\crew_scheduling.csv', index=False)
            b_lst.to_csv(r'timetable\multiline_meth2\Results\Bus_utility_details.csv', index=False)
            fig.savefig(r'timetable\multiline_meth2\Results\vehicle_schedule_visual.pdf', dpi=300)
            r_bus.to_csv(r'timetable\multiline_meth2\Results\Reuse.csv', index=False)
            fleet.to_csv(r'timetable\multiline_meth2\Results\fleet_shift_details.csv', index=False)
            for i in range(0, len(b_lst.index)):
                df3 = veh_schedule[(veh_schedule['bus_name'] == b_lst.iloc[i, 0])].copy()
                df3.reset_index(drop=True, inplace=True)
                name = b_lst.iloc[i, 0]
                df3.to_csv(r'timetable\multiline_meth2\Results\vehicleschedule\{}.csv'.format(name))
            busreq_at_r1t1 = r1_timetable['Fleet T1'].sum()
            busreq_at_r1t2 = r1_timetable['Fleet T2'].sum()
            busreq_at_r2t1 = r2_timetable['Fleet T1'].sum()
            busreq_at_r2t2 = r2_timetable['Fleet T2'].sum()

            print('fleet size:', busreq_at_r1t1+busreq_at_r1t2+busreq_at_r2t1+busreq_at_r2t2)
            print('\n Total ideal time in hours:', tot_ideal_time.round(0))
        else:
            if min_ideal> tot_ideal_time:
                min_ideal = tot_ideal_time
                r1_timetable.to_csv(r'timetable\multiline_meth2\Results\Time_Table.csv', index=False)
                r2_timetable.to_csv(r'timetable\multiline_meth2\Results\Time_Table.csv', index=False)
                veh_schedule.to_csv(r'timetable\multiline_meth2\Results\vehicle_schedule.csv',
                                    index=False)
                crew.to_csv(r'timetable\multiline_meth2\Results\crew_scheduling.csv', index=False)
                b_lst.to_csv(r'timetable\multiline_meth2\Results\Bus_utility_details.csv',
                                index=False)
                fig.savefig(r'timetable\multiline_meth2\Results\vehicle_schedule_visual.pdf', dpi=300)
                r_bus.to_csv(r'timetable\multiline_meth2\Results\Reuse.csv', index=False)
                fleet.to_csv(r'timetable\multiline_meth2\Results\fleet_shift_details.csv', index=False)
                for i in range(0, len(b_lst.index)):
                    df3 = veh_schedule[(veh_schedule['bus_name'] == b_lst.iloc[i, 0])].copy()
                    df3.reset_index(drop=True, inplace=True)
                    name = b_lst.iloc[i, 0]
                    df3.to_csv(r'timetable\multiline_meth2\Results\vehicleschedule\{}.csv'.format(name))

                busreq_at_r1t1 = r1_timetable['Fleet T1'].sum()
                busreq_at_r1t2 = r1_timetable['Fleet T2'].sum()
                busreq_at_r2t1 = r2_timetable['Fleet T1'].sum()
                busreq_at_r2t2 = r2_timetable['Fleet T2'].sum()
                tot_ideal_time = b_lst['Ideal time'].sum() - r_bus['Idl_Duration'].sum()
                print('fleet size:', busreq_at_r1t1 + busreq_at_r1t2 + busreq_at_r2t1 + busreq_at_r2t2)
                print('\n Total ideal time in hours:', tot_ideal_time.round(0))

            else:
                pass

    details_tt.to_csv(r'timetable\multiline_meth2\AA_details_tt.csv')
    details_tt.sort_values(by=['Ideal time'], ascending=True, inplace=True)
    details_tt.reset_index(drop=True, inplace=True)
    min_idealtt=details_tt.loc[0,'Ideal time']
    print(min_idealtt)
    print('end')

if __name__ == '__main__':
    main()

