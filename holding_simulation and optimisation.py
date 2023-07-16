import pandas as pd
import numpy as np
import yaml
from yaml.loader import SafeLoader
import os
from overallcost import overallcost

from cost_fn_holding  import cost_holding
from ga_holding import cal_pop_fitness,select_mating_pool,crossover,mutation
from space_time import st_chart
import gc


pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.precision', 2)

with open('parameters.yml') as f:
    data = yaml.load(f, Loader=SafeLoader)

globals().update(data)

dob= seatcap*min_c_lvl
cob= int (seatcap*max_c_lvl)






#1. INTRODUCTION OF DELAY
#--------------------------------------------
#Input Parameters
delay=10
trip_no=10
stop_no=6
drctn= 'DN'                      #direction 'DN'/'UP'

control_pnts='immediate upstream stops'
#control_pnts='inputs'        #specific control points
#ctrlpnts_input= control_pnts

#optimisation inputs
sol_per_pop = 20
num_generations = 5
# ACTUAL ARRIVAL TIME = EXPECTED ARRIVAL + DELAY
#---------------------------------------
#INPUT FILES
veh_sch=pd.read_csv(r'Function files\Input_files_holding\vehicle_schedule.csv')
holding=pd.read_csv(r'Function files\Input_files_holding\holding_process.csv ')
veh_sch.drop(0, inplace= True)
if drctn== 'DN':
    dep_t1 = pd.read_csv(r"Function files\Input_files_holding\Timetable_T1.csv")
    dep_t2 = pd.read_csv(r'Function files\Input_files_holding\Timetable_T2.csv')
    despatch = pd.read_csv(r'Function files\Input_files_holding\despatchDN.csv ')
    despatch_idl = pd.read_csv(r'Function files\Input_files_holding\despatchDN.csv ')
    headway = pd.read_csv(r'Function files\Input_files_holding\headwayDN.csv')
    stoparrival=pd.read_csv(r'Function files\Input_files_holding\stoparrivalDN.csv')
    stoparrival_idl= pd.read_csv(r'Function files\Input_files_holding\stoparrivalDN.csv')
    distance = pd.read_csv(r'Function files\Input files\distanceDN.csv').set_index('Distance')
else:
    dep_t1 = pd.read_csv(r'Function files\Input_files_holding\Timetable_T2.csv')
    dep_t2 = pd.read_csv(r'Function files\Input_files_holding\Timetable_T1.csv')
    despatch = pd.read_csv(r'Function files\Input_files_holding\despatchUP.csv ')
    headway = pd.read_csv(r'Function files\Input_files_holding\headwayUP.csv')
    stoparrival_idl=pd.read_csv(r'Function files\Input_files_holding\stoparrivalUP.csv')
    distance = pd.read_csv(r'Function files\Input files\distanceUP.csv').set_index('Distance')

files = [stoparrival,headway,despatch]



stops= stoparrival.columns

stoparrival.iloc[trip_no, stop_no]= stoparrival.iloc[trip_no, stop_no] + delay/60

# 3.  Simulation of bus line and immediate upstreams stops----------------------------------------------------------------------
# --------------------------------------------------------------------------


bus_line = pd.DataFrame(index=np.arange(0), columns=['trip_no', 'ctrl_stops'])

for i in range(0, len(stoparrival.index)):
    if i < trip_no:
        for j in range(0, len(stoparrival.columns) - 1):
            if stoparrival.iloc[i, j] >= (stoparrival.iloc[trip_no, stop_no]):
                bus_line.loc[len(bus_line.index)] = [i, j]
                break
            else:
                pass
    elif i == trip_no:
        pass
    elif i > trip_no and stoparrival.iloc[i, 0] <= (stoparrival.iloc[trip_no, stop_no]):
        for j in range(0, len(stoparrival.columns)):
            if stoparrival.iloc[i, j] > (stoparrival.iloc[trip_no, stop_no]):
                bus_line.loc[len(bus_line.index)] = [i, j]
                break
            else:
                pass
    else:
        break

print('number of buses on route:', len(bus_line.index))
bus_line['bus_name'] = ""

for i in range(0, (len(bus_line.index))):
    bus_line.loc[i, 'bus_name'] = dep_t1.loc[bus_line.loc[i, 'trip_no'], 'bus_name']

delayed_bus = [trip_no, stop_no, dep_t1.loc[trip_no, 'bus_name'], stoparrival.iloc[trip_no, stop_no]]

#---------------------------------------------------------------------------------------------
# With delay No HOLDING
#---------------------------------------------------------------------------------------------

delay_bus_cp = delayed_bus.copy()
h_bus_cp = bus_line.copy()
hold = [0]*len(h_bus_cp.index)
h_bus_cp['holding'] = hold
purpose='No holding'
despatch, stoparrival,cost = cost_holding(h_bus_cp, drctn, delayed_bus, purpose)
h_bus_cp.loc[len(h_bus_cp.index)] = delayed_bus
h_bus_cp = h_bus_cp.sort_values(by=['trip_no']).reset_index(drop=True)
h_bus_cp.drop(['holding'], axis=1, inplace=True)
print('Buses on route and immediate upstream stops: \n',h_bus_cp.rename({'ctrl_stops':'Immediate upstream stops'}, axis=1))

print('Cost of operations if no holding for ',drctn,'direction:\t',cost)


st_trip= h_bus_cp.loc[0,'trip_no']
end_trip = h_bus_cp.loc[len(h_bus_cp.index)-1, 'trip_no']+1

#plotting space time chart for no delay no0 holding(ideal) condition
#-----------------------------------------------------------------------------
stoparrival_idl = stoparrival_idl.iloc[st_trip:end_trip, :]
despatch_idl= despatch_idl.iloc[st_trip:end_trip, :]
fig1 = st_chart(stoparrival_idl, despatch_idl, distance)
fig1.legend(fontsize=20)
path = r'Function files\Output holding optimisation'
isExist = os.path.exists(path)
if not isExist:
    # Create a new directory because it does not exist
    os.makedirs(path)

fig1.savefig(r'Function files\Output holding optimisation\ideal_scenario.pdf', dpi=300)
#-----------------------------------------------------------------------------
#plotting space time chart for no holding condition
#-----------------------------------------------------------------------------
stoparrival_prnt = stoparrival.iloc[st_trip:end_trip, :]
despatch_prnt = despatch.iloc[st_trip:end_trip, :]
fig2 = st_chart(stoparrival_prnt, despatch_prnt, distance)
fig2.legend(fontsize=20)
fig2.savefig(r'Function files\Output holding optimisation\with_delay_no_holding.pdf', dpi=300)


#-----------------------------------------------------------------------------
#2. CHECK DELAY
#-----------------------------------------------------------------------------

#check the  headway for the next bus is within the threshold
headway_test= (stoparrival.iloc[trip_no+1, stop_no] - stoparrival.iloc[trip_no, stop_no])*60


if headway_test >= (headway.iloc[trip_no+1,0]/4):
    print('\n no holding required')
else:
    print('Headway deviation is beyond the threshold')
    print('\n Holding action initiated')

    #1. Control points

    if control_pnts=='immediate upstream stops':
        h_bus=bus_line

    else:
        # control points are as inputs
        h_bus_ctrlinput = pd.DataFrame(index=np.arange(0), columns=['trip_no', 'ctrl_stops'])

        for i in range(0, len(stoparrival.index)):
            if i < trip_no:
                for j in range(0, len(stoparrival.columns) - 1):
                    if stoparrival.iloc[i, j] >= (stoparrival.iloc[trip_no, stop_no]):
                        for m in range(0, len(control_pnts)):
                            if j <= control_pnts[m]:
                                k = control_pnts[m]
                                break
                            else:
                                pass
                        h_bus_ctrlinput.loc[len(h_bus_ctrlinput.index)] = [i, k]
                        break
                    else:
                        pass
            elif i == trip_no:
                pass
            elif i > trip_no and stoparrival.iloc[i, 0] <= (stoparrival.iloc[trip_no, stop_no]):
                for j in range(0, len(stoparrival.columns)):
                    if stoparrival.iloc[i, j] > (stoparrival.iloc[trip_no, stop_no]):
                        for m in range(0, len(control_pnts)):
                            if j <= control_pnts[m]:
                                k = control_pnts[m]
                                break
                            else:
                                pass

                        h_bus_ctrlinput.loc[len(h_bus_ctrlinput.index)] = [i, k]
                        break
                    else:
                        pass
            else:
                break
        h_bus_ctrlinput['bus_name'] = ""
        for i in range(0, (len(h_bus_ctrlinput.index))):
            h_bus_ctrlinput.loc[i, 'bus_name'] = dep_t1.loc[h_bus_ctrlinput.loc[i, 'trip_no'], 'bus_name']

        h_bus= h_bus_ctrlinput



    # 2. CALCULATION OF HOLDING RANGE-----------------------------------------------------------------------------------


    print ('Buses to be holded and control points: \n ',h_bus)

    range_h=pd.DataFrame()

    range_h['bus_name']= h_bus['bus_name']
    range_h['arrival_dest']=""
    range_h['next_dispatch'] = ""
    range_h['min holding']=0
    range_h['Max holding']=""

    #.1 = departure time @terminal 1
    #.2 = destination terminal
    #.3 = arrival time @ destination terminal


    for i in range(0,len(range_h.index)):
        for j in range (0,len(dep_t1.index)):
            arrivalDest= dep_t1.loc[h_bus.loc[i,'trip_no'],'Arrival_Time']

            for k in range(0,len(dep_t2.index)):
                if dep_t2.loc[k,'bus_name']== dep_t1.loc[h_bus.loc[i,'trip_no'],'bus_name'] and dep_t2.loc[k,'Departure_time']>arrivalDest:
                    nextdep= dep_t2.loc[k,'Departure_time']
                    break
                else:
                    pass
            range_h.loc[i,'arrival_dest']=arrivalDest
            range_h.loc[i,'next_dispatch']=nextdep
            range_h.loc[i,'Max holding']=((nextdep- arrivalDest)*60-lay_overtime).round(2)
    range_h.drop(['arrival_dest','next_dispatch'], axis=1, inplace=True)
    delayed_bus = [trip_no, stop_no, dep_t1.loc[trip_no, 'bus_name'], stoparrival.iloc[trip_no, stop_no]]
    print('Holding range for optimisation: \n',range_h )
    #hold=[0,0,0,0,0,0,0,0]
    #h_bus['holding'] = hold
    #cost= cost_holding(h_bus,drctn,delayed_bus)
    #print(cost)




    # 5. OPTIMISATION = genetic algorithm------------------------------------------------------------------------


    num_weights = len(range_h.index)

    num_parents_mating = int(sol_per_pop / 2)
    pop_size = (sol_per_pop, num_weights)
    new_populationDN = np.random.randint(low=range_h.iloc[:, 1], high=range_h.iloc[:, 2] + 1, size=pop_size)
    print("\nInitial population  : ", new_populationDN)
    # Measuring the fitness of each chromosome in the population.
    # pass h_bus in fitness fn if the control points are immediate upstream stop.
    # pass h_bus_ctrlinput fitness fn if the control points are specific input points.

    fitness = cal_pop_fitness(new_populationDN, delayed_bus, h_bus, drctn, sol_per_pop)
    print('cost for initial pop', fitness)

    for generation in range(num_generations):
        print("\nGeneration : ", generation)
        # Selecting the best parents in the population for mating.
        parents = select_mating_pool(new_populationDN, fitness, num_parents_mating)

        # Generating next generation using crossover.
        offspring_crossover = crossover(parents, offspring_size=(pop_size[0] - parents.shape[0], num_weights))

        # Adding some variations to the offspring using mutation.
        offspring_mutation = mutation(offspring_crossover, range_h)

        # Creating the new population based on the parents and offspring.
        new_populationDN[0:parents.shape[0], :] = parents
        new_populationDN[parents.shape[0]:, :] = offspring_mutation
        # The best result in the current iteration.
        fitness = cal_pop_fitness(new_populationDN, delayed_bus, h_bus, drctn, sol_per_pop)

        print('Cost of new population:', generation, 'Generation', fitness)

    print('Final frequency population :', new_populationDN)
    print('Fitness of population', fitness)

    final_pop = pd.DataFrame(new_populationDN)
    final_pop['Overallcost'] = fitness

    min_cost_idx = final_pop[['Overallcost']].idxmin()
    min_cost_idx = min_cost_idx.iloc[0]

    final_pop.drop('Overallcost', axis=1, inplace=True)
    hold = final_pop.iloc[min_cost_idx, :]

    h_bus['holding'] = hold.values

    path = r'Function files\Output holding optimisation'
    isExist = os.path.exists(path)
    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(path)


    purpose = 'Optimised holding'
    despatch, stoparrival,cost = cost_holding(h_bus, drctn, delayed_bus, purpose)

    holding.loc[len(holding.index), 0] = holding.iloc[len(holding.index) - 1, 0] + 1
    print(holding)
    holding.to_csv(r'Function files\Input_files_holding\holding_process.csv ', index=False)
    k = holding.iloc[len(holding.index) - 1, 0]
    name = 'optimised holding' + str(k)
    h_bus.to_csv(r'Function files\Output holding optimisation\{}.csv '.format(name), index=False)


    # plotting space time chart for no holding condition

    stoparrival_prnt=stoparrival.iloc[st_trip:end_trip, :]
    despatch_prnt= despatch.iloc[st_trip:end_trip, :]
    fig3 = st_chart(stoparrival_prnt, despatch_prnt, distance)
    fig3.legend(fontsize=20)
    fig3.savefig(r'Function files\Output holding optimisation\with_optimised_holding.pdf', dpi=300)

    stoparrivalclock = stoparrival.copy()
    despatchclock=despatch.copy()
    for ind in range(0, len(stoparrival.index)):
        for j in range(0, len(stoparrival.columns)):
            stoparrivalclock.iloc[ind, j] = np.floor(stoparrival.iloc[ind, j]) + (
                        (stoparrival.iloc[ind, j] - (np.floor(stoparrival.iloc[ind, j]))) / 100 * 60).round(2)
            despatchclock.iloc[ind, j] = np.floor(despatchclock.iloc[ind, j]) + (
                    (despatchclock.iloc[ind, j] - (np.floor(despatchclock.iloc[ind, j]))) / 100 * 60).round(2)




    for i in range(0,len(h_bus.index)):
        ctrl_stop=h_bus.loc[i,'ctrl_stops']
        trp_no= h_bus.loc[i,'trip_no']
        h_bus.loc[i,'ctrl_stops']= stops[ctrl_stop]
        print('Hold the bus:', h_bus.loc[i, 'bus_name'], '\t at control point:', h_bus.loc[i, 'ctrl_stops'], '\t for', h_bus.loc[i, 'holding'], 'Minutes','\t The new despatch time:', despatch.iloc[trp_no,ctrl_stop])

    print(h_bus)
    print('New despatch time and arrival time are updated')



print('End of the holding process')




