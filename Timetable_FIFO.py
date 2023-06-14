import pandas as pd
import numpy as np
import gc
import yaml
from yaml.loader import SafeLoader
import os
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from natsort import natsort_keygen

def schedule(traveltimeDN, departuretimeDN, departuretimeUP, traveltimeUP, terminalarrivalDN,
             terminalarrivalUP, data):
    
    globals().update(data)
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

    # tt_terminal1 = timetable for terminal 1
    # tt_terminal2 = timetable for terminal 2
    # creating folders for exporting results
    # defining path
    # path = r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\FIFO\vehicleschedule'
    vehicleschedule = []
    # isExist = os.path.exists(path)
    # # checking path exists or not , if not creates the path
    # if not isExist:
    #     # Create a new directory because it does not exist
    #     os.makedirs(path)

    num_bus_T = 1
    # Dataframe to store data of  depot pool
    depot_pool = pd.DataFrame(index=np.arange(0),
                              columns=['bus_name', 'departure_to_depo', 'from_terminal', 'TT_depot', 'layover',
                                       'TT_terminal1', 'TT_terminal2', 'nxt_shift'])
    # Dataframe to store data of  depot pool
    depot_tt = pd.DataFrame(index=np.arange(0),
                            columns=['bus_name', 'departure_to_depo', 'departure_from_depo', 'terminal_arrival',
                                     'terminal'])
    # Dataframe to store layover details
    laydf1 = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'start', 'end', 'remarks'])
    # Dataframe to store fleet details
    fleet = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'shift_no', 'start_shift1', 'end_shift', 'crew'])
    fleet_1 = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'shift_no', 'start_shift1', 'end_shift', 'crew'])
    fleet_2 = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'shift_no', 'start_shift1', 'end_shift', 'crew'])
    # Dataframe to store terminal pool details
    pool_t1 = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'Ready_to_depart'])
    pool_t2 = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'Ready_to_depart'])
    # VEHICLE ASSIGNMENT
    for i in range(0, len(tt_terminal1.index)):
        for j in range(0, 2):  # j==1 for terminal1 and j==2 for terminal2
            bus_name = 'RI00'  # bus name code
            if j == 0:
                or_terminal = tt_terminal1
                des_terminal = tt_terminal2
                pool = pool_t1
                traveltime = traveltimeDN
            else:

                or_terminal = tt_terminal2
                des_terminal = tt_terminal1
                pool = pool_t2
                traveltime = traveltimeUP

            if or_terminal.loc[i, 'Dep/Arrival'] == 'Departure':
                # CHECK FOR BUSES TO RETURN TO DEPOT AFTER A SHIFT
                # checking buses that are ready for next departure at time =or_terminal.loc[i, 'Time of Arrival']
                temp_pool = pool[pool['Ready_to_depart'] <= or_terminal.loc[i, 'Time of Arrival']]
                # the minimum time required by all buses in the temp_pool to complete the next trip
                max = or_terminal.loc[i, 'Departure_time'] + traveltime.iloc[or_terminal.loc[i, 'Dep'] - 1, 0]
                if len(temp_pool.index) > 0 and max >= fleet.loc[0, 'end_shift']:
                    pl_dropidx = [] #list stores the index of buses that will go back to the depot after a shift
                    #check for buses that will go to the depot for crew change and next shift
                    for ind in range(0, len(temp_pool.index)):
                        k = temp_pool.index[ind]
                        y1 = fleet[fleet['bus_name'] == temp_pool.loc[k, 'bus_name']].copy()
                        y1.sort_values(by=['shift_no'], ascending=False, inplace=True)
                        y1.reset_index(drop=True, inplace=True)
                        #y1 stores the shift details of the temp_pool.loc[k, 'bus_name'] bus
                        if len(y1.index) > 0:
                            y1 = y1[:1] #accessing the latest shift details

                            x1 = or_terminal.loc[i, 'Departure_time'] + traveltime.iloc[
                                or_terminal.loc[i, 'Dep'] - 1, 0] #minimum time required to complete next trip

                            if x1 >= y1.loc[0, 'end_shift']: #bus will depart to the depot if x1 >= y1.loc[0, 'end_shift']
                                #updating the depot pool
                                bus_name_d = temp_pool.loc[k, 'bus_name']
                                departure_to_depo = or_terminal.loc[i, 'Departure_time']

                                if j == 0:
                                    arrival_depot = dead_todepot_t1 + departure_to_depo
                                    from_terminal = 'T1'
                                else:
                                    arrival_depot = dead_todepot_t2 + departure_to_depo
                                    from_terminal = 'T2'

                                depo_layover = layover_depot / 60
                                departure_from_depo = arrival_depot + depo_layover
                                TTdepo_ter1 = arrival_depot + depo_layover + dead_todepot_t1
                                TTdepo_ter2 = arrival_depot + depo_layover + dead_todepot_t2
                                shift_nxt = y1.loc[0, 'shift_no'] + 1
                                depot_pool.loc[len(depot_pool.index)] = [bus_name_d, departure_to_depo,
                                                                         from_terminal,
                                                                         arrival_depot, depo_layover, TTdepo_ter1,
                                                                         TTdepo_ter2, shift_nxt]
                                depot_tt.loc[len(depot_tt.index)] = [bus_name_d, departure_to_depo, departure_from_depo,
                                                                     22, 0]
                                pl_dropidx.append(k)

                            else:
                                pass
                    #removing the buses left for depot for crew change/next shift from terminal pool
                    pool.drop(index=pl_dropidx, inplace=True)
                    pool.reset_index(drop=True, inplace=True)
                # ------------------------------------------------------------------------------------------

                # CHECK for buses in the terminal pool for next departure
                temp_pool = pool[pool['Ready_to_depart'] <= or_terminal.loc[i, 'Time of Arrival']]
                temp_pool.reset_index(drop=True, inplace=True)
                if len(temp_pool.index) == 0:  # if no buses in terminal pool for next departure then check for buses in the depotpool
                    if j == 0: #for terminal 1
                        #creating a pool of buses by checking the expected arrival of buses at terminal 1 from depot
                        temp_depool = depot_pool[
                            depot_pool['TT_terminal1'] < tt_terminal1.loc[i, 'Time of Arrival']].copy()
                        temp_depool.sort_values(by=['TT_terminal1'], ascending=True, inplace=True)
                        temp_depool.reset_index(drop=True, inplace=True)
                    else: #for terminal 2
                        temp_depool = depot_pool[
                            depot_pool['TT_terminal2'] < tt_terminal2.loc[i, 'Time of Arrival']].copy()
                        temp_depool.sort_values(by=['TT_terminal2'], ascending=True, inplace=True)
                        temp_depool.reset_index(drop=True, inplace=True)

                    if len(temp_depool.index) == 0: # if no buses in temp_depot pool for next departure then addition of a bus to the fleet
                        #adding new bus to the terminal
                        or_terminal.loc[i, 'bus_name'] = bus_name + str(num_bus_T)
                        num_bus_T = num_bus_T + 1
                        or_terminal.loc[i, 'Fleet'] = 1
                        #start of shift
                        shift_str = np.floor(or_terminal.loc[i, 'Time of Arrival'])
                        # end of shift
                        shift_end = np.floor(shift + tt_terminal1.loc[i, 'Time of Arrival'])
                        if shift_end > end_ser:
                            shift_end = end_ser + 2
                        else:
                            pass
                        shift_no = 1
                        or_terminal.loc[i, 'Pool'] = len(temp_pool.index)
                    else:
                        #adding buses for temp_depo pool
                        or_terminal.loc[i, 'bus_name'] = temp_depool.loc[0, 'bus_name']
                        or_terminal.loc[i, 'Fleet'] = 0

                        if j == 0: #terminal 1
                            shift_str = np.floor(temp_depool.loc[0, 'TT_terminal1'])
                            depot_tt.loc[(depot_tt['bus_name'] == temp_depool.loc[0, 'bus_name']) & (
                                    depot_tt['departure_to_depo'] == temp_depool.loc[
                                0, 'departure_to_depo']), 'terminal_arrival'] = temp_depool.loc[
                                0, 'TT_terminal1']

                            depot_tt.loc[(depot_tt['bus_name'] == temp_depool.loc[0, 'bus_name']) & (
                                    depot_tt['departure_to_depo'] == temp_depool.loc[
                                0, 'departure_to_depo']), 'terminal'] = 'T1'

                        else: #terminal 2
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
                        #removing the added bus from pool
                        depot_pool.drop(depot_pool[depot_pool['bus_name'] == temp_depool.loc[0, 'bus_name']].index,
                                        inplace=True)

                        depot_pool.reset_index(drop=True, inplace=True)
                        or_terminal.loc[i, 'Pool'] = len(temp_pool.index)

                    fleet.loc[len(fleet.index)] = [or_terminal.loc[i, 'bus_name'], shift_no,
                                                   shift_str, shift_end, crewperbus]


                else:
                    #Adding bus from the terminal pool
                    or_terminal.loc[i, 'bus_name'] = temp_pool.loc[0, 'bus_name']
                    pool.drop(index=0, inplace=True)
                    pool.reset_index(drop=True, inplace=True)
                    or_terminal.loc[i, 'Pool'] = len(temp_pool.index)

            else:
                #updating the arrival information of the bus at the terminal
                df2 = des_terminal[des_terminal['Dep'] == or_terminal.loc[i, 'Dep']]
                df2 = df2[df2['Dep/Arrival'] == 'Departure'].copy()
                df2.reset_index(drop=True, inplace=True)
                or_terminal.loc[i, 'bus_name'] = df2.loc[0, 'bus_name']
                #calculating layover time and when would be the minimum time for next departure
                ready_for_depart = or_terminal.loc[i, 'Time of Arrival'] + (lay_overtime + slack) / 60
                if j==0:
                    x2='layover T1'
                else:
                    x2='layover T2'
                laydf1.loc[len(laydf1.index)] = [or_terminal.loc[i, 'bus_name'],
                                                 or_terminal.loc[i, 'Time of Arrival'], ready_for_depart, x2]
                #adding arrived vehicle to the terminal pool
                pool.loc[len(pool.index)] = [or_terminal.loc[i, 'bus_name'], ready_for_depart]
                #sorting pool based on the minimum time for next departure IN ASCENTING ORDER
                pool.sort_values(by=['Ready_to_depart'], ascending=True, inplace=True)
                pool.reset_index(drop=True, inplace=True)
                temp_pool = pool[pool['Ready_to_depart'] <= or_terminal.loc[i, 'Time of Arrival']]
                or_terminal.loc[i, 'Pool'] = len(temp_pool.index)

    #Timetable for the route
    timetable = pd.concat([tt_terminal1, tt_terminal2], axis=1, ignore_index=True)
    timetable.columns = ['Dep T1', 'Pool T1', 'Dep/Arrival T1', 'bus_name1', 'Departure_from_T1', 'Time of Arr T1',
                         'Fleet T1', 'Dep T2', 'Pool T2', 'Dep/Arrival T2', 'bus_name2', 'Departure_from_T2',
                         'Time of Arr T2', 'Fleet T2']

    # CREW SCHEDULING---------------------
    total_crew = fleet['crew'].sum()

    # Dataframe to store crew and vehicle despatch details from depo
    crew = pd.DataFrame(index=np.arange(0), columns=['Time', 'Crew', 'buses to be dispatched '])
    time_period = start_ser - 1
    for i in range(start_ser - 1, end_ser):
        df5 = fleet[fleet['start_shift1'] == i]
        bus = df5.loc[:, 'bus_name'].tolist()
        crew_hr = df5['crew'].sum()
        time = str(i + .00) + '-' + str(i + .59)
        crew.loc[len(crew.index)] = [time, crew_hr, bus]

    # VEHICLE SCHEDULING
    # T1 TO T2--------------------------------------------------------------------------------------------------------------
    # veh_sch1= departure data from terminal 1
    veh_sch1 = pd.DataFrame(index=departuretimeDN.index,
                            columns=['bus_name', 'start', 'end', 'remarks'])
    veh_sch1['start'] = departuretimeDN['Arrival_T1']  # time at which bus arrives at origin for a trip
    veh_sch1['end'] = departuretimeDN['Arr_time T2']  # time at which bus arrives at destination end of the trip
    veh_sch1['remarks'] = A + '_to_' + B
    temp_bn = []
    for i in range(0, len(timetable.index)):
        if timetable.loc[i, 'Dep/Arrival T1'] == 'Departure':
            temp_bn.append(timetable.loc[i, 'bus_name1'])

    veh_sch1['bus_name'] = temp_bn

    # T2 TO T1-------------------------------------------------------------
    # veh_sch2= departure data from terminal 2
    veh_sch2 = pd.DataFrame(index=departuretimeUP.index,
                            columns=['bus_name', 'start', 'end', 'remarks'])
    veh_sch2['remarks'] = B + '_to_' + A
    veh_sch2['start'] = departuretimeUP['Arrival_T2']
    veh_sch2['end'] = departuretimeUP['Arr_time T1']
    temp_bn = []
    for i in range(0, len(timetable.index)):
        if timetable.loc[i, 'Dep/Arrival T2'] == 'Departure':
            temp_bn.append(timetable.loc[i, 'bus_name2'])
    veh_sch2['bus_name'] = temp_bn

    depott = depot_tt[['bus_name', 'departure_to_depo', 'terminal_arrival']].copy()
    depott['remarks'] = 'shift'
    depott.columns = ['bus_name', 'start', 'end', 'remarks']
    veh_sch = pd.concat([veh_sch1, veh_sch2, depott, laydf1], axis=0, ignore_index=True)
    veh_sch = veh_sch.sort_values(by=['start']).reset_index(drop=True)
    bus_name = veh_sch.bus_name.unique()
    d = {}

    # start of a trip = arrival of the bus at origin terminal
    veh_schedule = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'No:', 'start', 'end', 'remarks', 'bus_@'])
    bus_details = pd.DataFrame(index=np.arange(0), columns=['bus_name', 'No: of trips', 'Ideal time'])
    for i in range(0, len(bus_name)):
        no_trips = 0
        df3 = veh_sch[veh_sch['bus_name'] == bus_name[
            i]].copy()  # df3 store data of bus_name[i] which includes trip data, layover details, shift details
        df3.reset_index(drop=True, inplace=True)
        for j in range(0, len(df3.index)):
            # Calculation of ideal time
            if df3.iloc[j, 3] == A + '_to_' + B or df3.iloc[j, 3] == B + '_to_' + A:
                no_trips = no_trips + 1
                nn = no_trips
            else:
                nn = '_____'
            if df3.iloc[j, 3] == A + '_to_' + B:
                dist = dead_todepot_t1
            elif df3.iloc[j, 3] == B + '_to_' + A:
                dist = dead_todepot_t2
            else:
                pass
            if df3.loc[j, 'remarks'] == 'layover T2' or df3.loc[j, 'remarks'] == 'layover T1':
                pass
            else:
                if j == 0: #first trip
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
                    elif df3.loc[j, 'remarks'] == A + '_to_' + B:
                        x3 = 'T1'
                    else:
                        x3 = 'T1'
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
            elif df3.loc[j, 'remarks'] == A + '_to_' + B:
                x3 = 'T1'
            else:
                x3 = 'T2'
            veh_schedule.loc[len(veh_schedule)] = [bus_name[i], '----', Idl_start, Idl_end, remark, x3]
        df4 = veh_schedule[(veh_schedule['bus_name'] == bus_name[i]) & (veh_schedule['remarks'] == 'ideal')].copy()
        df4['dur'] = df4.end - df4.start
        ideal_time = df4['dur'].sum()
        df3 = veh_schedule[(veh_schedule['bus_name'] == bus_name[i])].copy()
        df3.reset_index(drop=True, inplace=True)
        name = bus_name[i]
        
        # df3.to_csv(r'\FIFO\vehicleschedule\{}.csv'.format(name))
        df3.title = name
        vehicleschedule.append(df3)     # saving to list in order to return as output instead of saving csv

        bus_details.loc[len(bus_details)] = [bus_name[i], no_trips, ideal_time]

    veh_schedule.sort_values(by='bus_name', inplace=True, key=natsort_keygen())
    veh_schedule.reset_index(drop=True, inplace=True)

    # Ideal time calculations
    ideal = veh_schedule[(veh_schedule['remarks'] == 'ideal')].copy()
    ideal['Idl_Duration'] = ideal.end - ideal.start
    reuse_buses = ideal[ideal['Idl_Duration'] > max_ideal]
    reuse_buses.reset_index(drop=True, inplace=True)

    # Visualisation of bus schedule
    #  Visual_sched= Dataframe used to generate the visuals
    visual_sched = veh_schedule[['bus_name', 'start', 'end', 'remarks']].copy()
    visual_sched = visual_sched[(visual_sched['remarks'] != 'ideal')]
    visual_sched.loc[visual_sched['remarks'] == 'layover T2', 'remarks'] = 'layover'
    visual_sched.loc[visual_sched['remarks'] == 'layover T1', 'remarks'] = 'layover'
    visual_resuse = reuse_buses[['bus_name', 'start', 'end']].copy()
    visual_resuse['remarks'] = 'Ideal<'+str(max_ideal)+'hrs'
    visual_resuse.columns = ['bus_name', 'start', 'end', 'legend']
    visual_sched.columns = ['bus_name', 'start', 'end', 'legend']
    visual_sched = pd.concat([visual_sched, visual_resuse], axis=0, ignore_index=True)
    visual_sched['Duration'] = visual_sched.end - visual_sched.start

    # Legend
    def color(row):
        c_dict = {A + '_to_' + B: '#E64646', B + '_to_' + A: '#ffb957', 'Ideal<'+str(max_ideal)+'hrs': '#309c00', 'layover': '#ada55c',
                  'shift': '#00f7ff'}
        return c_dict[row['legend']]

    visual_sched['color'] = visual_sched.apply(color, axis=1)

    fig, ax = plt.subplots(1, figsize=(16, 10))
    plt.xlim(5, 24)

    ax.barh(visual_sched.bus_name, visual_sched.Duration, left=visual_sched.start, color=visual_sched.color,
            height=0.2)
    # Legend
    c_dict = {A + '_to_' + B: '#E64646', B + '_to_' + A: '#ffb957', 'Ideal<'+str(max_ideal)+'hrs': '#309c00', 'layover': '#ada55c',
              'shift': '#00f7ff'}
    legend_elements = [Patch(facecolor=c_dict[i], label=i) for i in c_dict]
    plt.legend(handles=legend_elements)

    # TEXT
    for idx, row in visual_sched.iterrows():
        ax.text(row.end + 0.01, row.bus_name, row.end, va='center', alpha=0.8, fontsize=3)
        ax.text(row.start - 0.01, row.bus_name, row.start, va='center', ha='right', alpha=0.8, fontsize=3)

    plt.grid()
    plt.tight_layout()

    veh_schedule.set_index(['bus_name', 'No:'], drop=True, inplace=True)

    for i in range(0, len(tt_terminal1.index)):
        if timetable.loc[i, 'Dep/Arrival T1'] == 'Arrival':
            timetable.loc[i, 'Dep T1'] = "------"
        if timetable.loc[i, 'Dep/Arrival T2'] == 'Arrival':
            timetable.loc[i, 'Dep T2'] = "------"
    timetable['Departure_from_T1'].fillna('----',inplace=True)
    timetable['Departure_from_T2'].fillna('----', inplace=True)
    #fleet size calculation
    busreq_at_Terminal1 = timetable['Fleet T1'].sum()
    busreq_at_Terminal2 = timetable['Fleet T2'].sum()
    poolsize_at_Terminal1 = len(departuretimeDN.index) - busreq_at_Terminal1
    poolsize_at_Terminal2 = len(departuretimeUP.index) - busreq_at_Terminal2
    # converting time  in hrs to clock time

    #timetable['Departure_from_T1'] = np.floor(timetable['Departure_from_T1']) + (
                #timetable['Departure_from_T1'] - (np.floor(timetable['Departure_from_T1']))) / 100 * 60
    timetable['Time of Arr T1'] = np.floor(timetable['Time of Arr T1']) + ( timetable['Time of Arr T1'] - (np.floor(timetable['Time of Arr T1']))) / 100 * 60
    #timetable['Departure_from_T2'] = np.floor(timetable['Departure_from_T2']) + (
            #timetable['Departure_from_T2'] - (np.floor(timetable['Departure_from_T2']))) / 100 * 60
    timetable['Time of Arr T2'] = np.floor(timetable['Time of Arr T2']) + (timetable['Time of Arr T2'] - (np.floor(timetable['Time of Arr T2']))) / 100 * 60
    timetable. drop(['Departure_from_T1','Departure_from_T2'], axis=1,inplace=True)
    tot_ideal_time = bus_details['Ideal time'].sum() - reuse_buses['Idl_Duration'].sum()

    del tt_terminal2
    del tt_terminal1

    del arrivalUP
    del departuretimeUP1
    del arrivalDN
    del departuretimeDN
    del departuretimeUP

    gc.collect()


    return (
            fleet,depot_tt,crew,timetable, busreq_at_Terminal1, busreq_at_Terminal2, poolsize_at_Terminal1, poolsize_at_Terminal2, veh_sch1,
            veh_sch2, veh_schedule, bus_details, fig, reuse_buses, tot_ideal_time,vehicleschedule)

def main():
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.precision', 2)

    with open('parameters.yml') as f:
        data = yaml.load(f, Loader=SafeLoader)

    #importing files
    travel_time_totDN = pd.read_csv(r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\Input_files_holding\travel_time_totDN.csv')
    travel_time_totUP = pd.read_csv(r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\Input_files_holding\travel_time_totUP.csv')
    departuretimeUP = pd.read_csv(r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\Input_files_holding\departuretimeUP.csv')
    departuretimeDN = pd.read_csv(r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\Input_files_holding\departuretimeDN.csv')
    terminalarrivalDN = pd.read_csv(r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\Input_files_holding\stoparrivalDN.csv')
    terminalarrivalDN = terminalarrivalDN.iloc[:, 0]
    terminalarrivalUP = pd.read_csv(r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\Input_files_holding\stoparrivalUP.csv')
    terminalarrivalUP = terminalarrivalUP.iloc[:, 0]


    fleet,depot_tt,crew,timetable, busreq_at_Terminal1, busreq_at_Terminal2, poolsize_at_Terminal1, poolsize_at_Terminal2, veh_sch1, veh_sch2, veh_schedule, bus_details, fig, reuse_buses, tot_ideal_time, vehicleschedule = schedule(
        travel_time_totDN, departuretimeDN, departuretimeUP, travel_time_totUP, terminalarrivalDN, terminalarrivalUP, data)
    
    #PRINT RESULTS
    print(timetable.to_string())
    print(f'\nNo. of Bus required at Terminal1 Depot :', busreq_at_Terminal1,
        '\nNo. of Bus required at Terminal2 Depot:', busreq_at_Terminal2,
        '\n\nNo. of Bus reutilized from Pool at Terminal1 :', poolsize_at_Terminal1,
        "\nNo. of Bus reutilized from Pool at Terminal2 :", poolsize_at_Terminal2)
    print('\n Total ideal time in hours:', tot_ideal_time.round(0))
    print('Crew Requirement hourly: \n', crew)
    total_crew=crew ['Crew'].sum()
    print('\n Total crew required:', total_crew)


    print(veh_schedule.head(5))

    #Exporting files
    timetable.to_csv(r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\FIFO\Time_Table_FIFO.csv', index=False)
    veh_schedule.to_csv(r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\FIFO\vehicle_schedule_FIFO.csv')
    crew.to_csv(r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\FIFO\crew_scheduling_FIFO.csv', index=False)
    bus_details.to_csv(r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\FIFO\Bus_utility_details_FIFO.csv', index=False)
    fig.savefig(r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\FIFO\vehicle_schedule_visual_FIFO.pdf', dpi=300)
    reuse_buses.to_csv(r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\FIFO\Reuse_FIFO.csv', index=False)
    fleet.to_csv(r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\FIFO\fleet_shift_details_FIFO.csv', index=False)
    depot_tt.to_csv(r'C:\Users\abhis\OneDrive\Desktop\Scripts\busproject\Function files 10122022\FIFO\depot_shift_details_FIFO.csv', index=False)
    print('end')

if __name__ == '__main__':
    main()