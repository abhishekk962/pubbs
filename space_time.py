import matplotlib.pyplot as plt
import numpy as np
import pandas as pd




def st_chart(stoparrival,despatch,distance ):
    distance_origin = distance.copy()
    for i in range(0, len(distance.columns)):
        x = distance.iloc[[0], 0:i].sum(axis=1, skipna=True).values
        x = x[0]
        distance_origin.iloc[0, i] = x + distance.iloc[0, i]

    trip_st = 6
    trip_end = 11


    fig = plt.figure(figsize=(29, 21), dpi=300)
    axes = fig.add_axes([0.05, 0.05, .95, .95])
    axes.set_xlabel('Time',fontsize=20)

    axes.set_ylabel('Distance from terminal 1',fontsize=20)
    axes.set_title('Space Time diagram',fontsize=25)
    timedata_arrival = pd.DataFrame(columns=['Time', 'distance', 'trip_no'])
    for i in range(0, len(stoparrival.index)):
        timedata_arrival = pd.DataFrame(columns=['Time', 'distance', 'trip_no'])
        for j in range(0, len(stoparrival.columns)):
            list_1 = [stoparrival.iloc[i, j], distance_origin.iloc[0, j], i]
            timedata_arrival.loc[len(timedata_arrival.index)] = list_1
            list_2 = [despatch.iloc[i, j], distance_origin.iloc[0, j], i]
            timedata_arrival.loc[len(timedata_arrival.index)] = list_2
        x = timedata_arrival['Time']
        y = timedata_arrival['distance']
        name = str(stoparrival.index[i])
        axes.plot(x, y, label=name)


    return(fig)

