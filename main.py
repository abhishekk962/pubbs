import csv
import pandas as pd
import numpy as np
from flask import Flask, render_template, make_response,request, Response, session, redirect
import os
import re
import datetime
import io
from io import BytesIO
import pymysql
import yaml
from flask import send_file  
from flask_session import Session
 
app = Flask(__name__)
# app.config["SESSION_PERMANENT"] = False
# app.config["SESSION_TYPE"] = "filesystem"
# Session(app)

app.secret_key = os.urandom(24)


# Connect to phpMyAdmin Database
conn = pymysql.connect(host="103.21.58.10",
                       user="pubbsm8z",
                       password="Matrix__111",
                       database="pubbsm8z_uba",
                       port = 3306
                       )

# Create a User Login and Register Page

def query_db(query):
    c = conn.cursor()
    c.execute(query)
    data = c.fetchall()
    return data

@app.route('/')
@app.route('/login', methods =['GET', 'POST'])
def login():
    message = ''
    if 'email' in session:
        return render_template('index.html')
    else:
        return render_template('login1.html', message = message)
    

@app.route('/logout')
def logout():
    # session.pop('loggedin', None)
    session.pop('email', None)
    session.pop('password', None)
    return redirect('/home')

@app.route('/register', methods =['GET', 'POST'])
def register():
    message = ''
    if 'email' in session:
        return render_template('index.html')
    else:
        return render_template('register1.html', message = message)

@app.route('/loggedin', methods = ['GET', 'POST'])
def loggedin():
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        c = conn.cursor()
        c.execute('SELECT * FROM user WHERE email = % s AND password = % s', (email, password, ))
        user = c.fetchone()
        if user:
            # session['loggedin'] = True
            # session['userid'] = user['userid']
            session['email'] = user[1]
            session['password'] = user[2]
            # session['loggedin'] = True
            message = 'Logged in successfully !'
            return redirect('/home')
            # return render_template('index.html', message = message)
        else:
            message = 'Please enter correct email / password !'
        return render_template('login1.html', message = message)



@app.route('/registered', methods =['GET', 'POST'])
def registered():
    message = ''
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        email = request.form['email']
        c = conn.cursor()
        c.execute('SELECT * FROM user WHERE email = % s', (email, ))
        account = c.fetchone()
        if account:
            message = 'Account already exists !'
            return render_template('register1.html', message = message)
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            message = 'Invalid email address !'
            return render_template('register1.html', message = message)
        elif not name or not password or not email:
            message = 'Please fill out the form !'
            return render_template('register1.html', message = message)
        else:
            c.execute('INSERT INTO user (name, email, password) VALUES (% s, % s, % s)', (name, email, password, ))
            conn.commit()
            message = 'You have successfully registered ! Please Login'
            return render_template('register1.html', message = message)


@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'email' in session:
        return render_template('index.html')
    else:
        return redirect('/login')

# new
@app.route('/input-stops', methods=['GET', 'POST'])
def input_stops():
    session['periods'] = int(request.form['Number_of_service_periods'])
    session['project'] = request.form['Bus_route_name']
    return render_template('coord.html', periods=session['periods'])

# new
@app.route('/save-stops', methods=['GET', 'POST'])
def save_stops():
    stops = request.form.to_dict()
    stops_list = [stops[n] for n in stops if '_Name' in n]
    session['stops_list'] = stops_list
    up_distances = [stops[n] for n in stops if '_UP' in n]
    dn_distances = [stops[n] for n in stops if '_DN' in n]
    latitudes = [stops[n] for n in stops if '_lat' in n]
    longitudes = [stops[n] for n in stops if '_lng' in n]
    is_dummy = [True if f"{n}_Dummy" in stops else False for n in stops_list]
    is_intersection = [True if f"{n}_Cong" in stops else False for n in stops_list]

    # Upload to Database
    c = conn.cursor()
    query = f"CREATE TABLE IF NOT EXISTS T_STOPS_INFO (User TEXT,Project TEXT,Stop_Num INT,Stop_Name TEXT,Stop_Lat FLOAT,Stop_Long FLOAT, UP_Dist FLOAT, DN_Dist FLOAT, Dummy BOOLEAN, Cong_Int BOOLEAN);"
    c.execute(query)
    conn.commit()

    # c = conn.cursor()
    # c.execute(f"DELETE FROM T_STOPS_INFO WHERE Project = '{session['project']}' and User = '{session['email']}';")
    # conn.commit()

    c = conn.cursor()
    for n in range(len(stops_list)):
        c.execute(f"INSERT INTO T_STOPS_INFO (User,Project,Stop_Num,Stop_Name,Stop_Lat,Stop_Long,UP_Dist,DN_Dist,Dummy,Cong_Int) VALUES ('{session['email']}','{session['project']}','{n+1}','{stops_list[n]}','{latitudes[n]}','{longitudes[n]}','{up_distances[n]}','{dn_distances[n]}',{is_dummy[n]},{is_intersection[n]});")
        conn.commit()
    
    # c.execute(f"DROP TABLE IF EXISTS T_DistanceUP;")
    # query = f"CREATE TABLE T_DistanceUP ({','.join([f'`{n}` FLOAT' for n in session['stops_list']])});"
    # c.execute(query)
    # query = f"INSERT INTO T_DistanceUP (`{'`, `'.join(session['stops_list'])}`) VALUES ({', '.join(['%s' for n in range(len(session['stops_list']))])})"
    # c.execute(query, tuple(up_distances))
    # conn.commit()

    # c = conn.cursor()
    # c.execute(f"DROP TABLE IF EXISTS T_DistanceDN;")
    # query = f"CREATE TABLE T_DistanceDN ({','.join([f'`{n}` FLOAT' for n in session['stops_list']])});"
    # c.execute(query)
    # query = f"INSERT INTO T_DistanceDN (`{'`, `'.join(session['stops_list'])}`) VALUES ({', '.join(['%s' for n in range(len(session['stops_list']))])})"
    # c.execute(query, tuple(dn_distances))
    # conn.commit()
    # return stops
    return render_template('newtable.html', stops_list=session['stops_list'], periods=session['periods'])

# new
@app.route('/table-filled', methods=['GET', 'POST'])
def table_filled():
    # Get filled data
    data = request.form.to_dict()
    c = conn.cursor()
    c.execute(f"SELECT Stop_Name FROM T_STOPS_INFO WHERE User = '{session['email']}' and Project='{session['project']}' ORDER BY Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))
    # print(stops_list)
    # return stops_list
    # Upload to Database
    c = conn.cursor()
    db_table = request.form['db_table']
    # c.execute(f"DROP TABLE IF EXISTS {db_table};")
    query = f"CREATE TABLE IF NOT EXISTS {db_table} (User TEXT,Project TEXT,Period INT,{','.join([f'`Stop {n+1}` FLOAT' for n in range(30)])});"
    c.execute(query)
    c.execute(f"DELETE FROM {db_table} WHERE Project = '{session['project']}';")
    for p in range(session['periods']):
        query = f"INSERT INTO {db_table} (User,Project,Period,{','.join([f'`Stop {n+1}`' for n in range(len(stops_list))])}) VALUES ('{session['email']}','{session['project']}','{p+1}',{','.join(['%s' for n in range(len(stops_list))])});"
        print(query)
        row = []
        for s in stops_list:
            row.append(float(data[f"{s}_{p+1}"]))
            print(row, f"{s}_{p+1}")
        print(query)
        c.execute(query, tuple(row))
        conn.commit()
        row = []

    # return data
    return render_template('newtable.html', stops_list=stops_list, periods=session['periods'])
    # return render_template('test.html',stops_list=stops_list)

# new
@app.route('/clear-table', methods=['GET', 'POST'])
def clear_table():
    c = conn.cursor()
    c.execute(f"SELECT Stop_Name FROM T_STOPS_INFO WHERE User = '{session['email']}' and Project='{session['project']}' ORDER BY Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))
    return render_template('newtable.html', stops_list=stops_list, periods=session['periods'])

# new
@app.route('/retrieve-data', methods=['GET', 'POST'])
def retrieve_data():
    # Retrieve from Database
    db_table = request.form['db_table']
    c = conn.cursor()
    c.execute(f"SELECT Stop_Name FROM T_STOPS_INFO WHERE User = '{session['email']}' and Project='{session['project']}' ORDER BY Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))
    c.execute(f"SELECT {','.join([f'`Stop {n+1}`' for n in range(len(stops_list))])} FROM {db_table} WHERE User = '{session['email']}' and Project='{session['project']}' ORDER BY Period")
    db_data= c.fetchall()
    if len(db_data) != session['periods']:
        return "The specified number of periods don't match the data from the database. Please check and try again."
    if len(db_data[0]) != len(stops_list):
        return "The specified number of stops don't match the data from the database. Please check and try again."
    return render_template('newtable.html', stops_list=stops_list, periods=session['periods'], db_data=db_data)
    # return render_template('test.html',stops_list=stops_list)

# new
@app.route('/upload-csv-data', methods=['GET', 'POST'])
def upload_csv_data():
    # Get stops list
    c = conn.cursor()
    c.execute(f"SELECT Stop_Name FROM T_STOPS_INFO WHERE User = '{session['email']}' and Project='{session['project']}' ORDER BY Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))

    csvdata = request.files['csvfile'].read()
    csvdata = pd.read_csv(BytesIO(csvdata))
    csvdata = list(csvdata.itertuples(index=False, name=None))
    if len(csvdata) != session['periods']:
        return "The specified number of periods don't match the csv data uploaded. Please check and try again."
    if len(csvdata[0]) != len(stops_list):
        return "The specified number of stops don't match the csv data uploaded. Please check and try again."
    return render_template('newtable.html', stops_list=stops_list, periods=session['periods'], db_data=csvdata)

# new
@app.route('/download-csv-data', methods=['GET', 'POST'])
def download_csv_data():
    # Retrieve from Database
    data = request.form.to_dict()

    # Get stops list
    c = conn.cursor()
    c.execute(f"SELECT Stop_Name FROM T_STOPS_INFO WHERE User = '{session['email']}' and Project='{session['project']}' ORDER BY Stop_Num")
    stops_list= c.fetchall()
    stops_list = tuple(sum(stops_list, ()))

    # Write csv
    csv = ""
    csv += ','.join(stops_list) + '\n'
    for p in range(session['periods']):
        row = []
        for s in stops_list:
            row.append(float(data[f"{s}_{p+1}"]))
        row = ','.join([str(n) for n in row])
        csv += row + '\n'

    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=myplot.csv"})
    # return render_template('newtable.html', stops_list=stops_list, periods=periods, db_data=db_data)
    # return render_template('test.html',stops_list=stops_list)

# old
@app.route('/table')
def table():
    return render_template('table.html')

# old
@app.route('/upload_file')
def file_upload():
    return render_template('file_upload.html')

# old
@app.route('/insert-data', methods=['GET', 'POST'])
def insert_data():
    try:
        Bus_route_name = request.form['Bus_route_name']
        Terminal_1_origin = request.form['Terminal_1_origin']
        Terminal_2_destination = request.form['Terminal_2_destination']
        Bus_service_timings_From = request.form['Bus_service_timings_From']
        Bus_service_timings_To = request.form['Bus_service_timings_To']
        Number_of_service_periods = request.form['Number_of_service_periods']
        

        c = conn.cursor()

        query = "insert into route_info (Bus_route_name, Terminal_1_origin, Terminal_2_destination, Bus_service_timings_From, Bus_service_timings_To , Number_of_service_periods ) VALUES (%s,%s,%s,%s,%s,%s)"

        c.execute(query, (Bus_route_name, Terminal_1_origin, Terminal_2_destination, Bus_service_timings_From, Bus_service_timings_To , Number_of_service_periods))
        conn.commit()

        with open('distanceUP.csv', 'r') as file:
            reader = zip(*csv.reader(file))
            # Create an empty list to hold the rows of data
            rows1 = []
            # Loop through each row in the reader object and append it to the list
            for row in reader:
                rows1.append(row)


        with open('distanceDN.csv', 'r') as file:
            reader = zip(*csv.reader(file))
            # Create an empty list to hold the rows of data
            rows2 = []
            # Loop through each row in the reader object and append it to the list
            for row in reader:
                rows2.append(row)

        # timeperiod DOWN
        c.execute("SELECT * FROM timeperiodDN")
        time1 = c.fetchall()

        # timeperiod UP
        c.execute("SELECT * FROM timeperiodUP")
        time2 = c.fetchall()

        # Define the header row for the CSV file
        header = ['Bus_route_name', 'Terminal_1_origin', 'Terminal_2_destination', 'Bus_service_timings_From', 'Bus_service_timings_To', 'Number_of_service_periods']

        # Define the row of data to be written to the CSV file
        data = [Bus_route_name, Terminal_1_origin, Terminal_2_destination, Bus_service_timings_From, Bus_service_timings_To, Number_of_service_periods]
        
        # Open the CSV file in 'write' mode and write the data to it
        with open('route_info.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            
            # Write the header row
            writer.writerow(header)
            
            # Write the data row
            writer.writerow(data)
        conn.close()

        return render_template('index.html',rows1=rows1, rows2 = rows2, time1 = time1 , time2 = time2)
    except Exception as e:
        print(e)
        return "An error occurred"

    
# old
@app.route('/submit', methods=['POST'])
def submit():
    # Get data from form
    A = request.form['A']
    B = request.form['B']
    frequencydefault = request.form['frequencydefault']
    seatcap = request.form['seatcap']
    min_c_lvl = request.form['min_c_lvl']
    max_c_lvl = request.form['max_c_lvl']
    max_wait = request.form['max_wait']
    bus_left = request.form['bus_left']
    min_dwell = request.form['min_dwell']
    slack = request.form['slack']
    lay_overtime = request.form['lay_overtime']
    buscost = request.form['buscost']
    buslifecycle = request.form['buslifecycle']
    crewperbus = request.form['crewperbus']
    crewincome = request.form['crewincome']
    cr_trip = request.form['cr_trip']
    cr_day = request.form['cr_day']
    busmaintenance = request.form['busmaintenance']
    fuelprice = request.form['fuelprice']
    kmperliter = request.form['kmperliter']
    kmperliter2 = request.form['kmperliter2']
    c_cantboard = request.form['c_cantboard']
    c_waittime = request.form['c_waittime']
    c_invehtime = request.form['c_invehtime']
    penalty = request.form['penalty']
    hrinperiod = request.form['hrinperiod']
    ser_period = request.form['ser_period']

    # Vehicle and crew scheduling

    dead_todepot_t1 = request.form['dead_todepot_t1']
    dead_todepot_t2 = request.form['dead_todepot_t2']
    layover_depot = request.form['layover_depot']
    start_ser = request.form['start_ser']
    end_ser = request.form['end_ser']
    shift = request.form['shift']
    max_ideal = request.form['max_ideal']

    # Genetic algorith parameters

    sol_per_pop = request.form['sol_per_pop']
    num_generations = request.form['num_generations']

    # CONSTRAINTS FULL DAY SERVICES

    max_oppp = request.form['max_oppp']
    min_ppvk = request.form['min_ppvk']
    min_ppt = request.form['min_ppt']
    max_ocpp = request.form['max_ocpp']
    max_fleet = request.form['max_fleet']
    max_ppl = request.form['max_ppl']
    min_crr = request.form['min_crr']

    # CONSTRAINTS TRIP WISE

    min_ppp = request.form['min_ppp']
    max_pplpt = request.form['max_pplpt']
    min_rvpt = request.form['min_rvpt']
    max_opc = request.form['max_opc']

    # Write data to MYSQL
    cursor = conn.cursor()

    query = """Insert into data_scheduling(A, B, frequencydefault, seatcap, min_c_lvl, max_c_lvl, max_wait, bus_left, min_dwell, slack, lay_overtime ,
    buscost,buslifecycle , crewperbus,crewincome, cr_trip , cr_day, busmaintenance , fuelprice, kmperliter, kmperliter2, c_cantboard ,c_waittime,
    c_invehtime, penalty, hrinperiod, ser_period, dead_todepot_t1, dead_todepot_t2, layover_depot, start_ser, end_ser, shift, max_ideal, sol_per_pop,
    num_generations, max_oppp, min_ppvk, min_ppt,max_ocpp, max_fleet, max_ppl, min_crr, min_ppp, max_pplpt, min_rvpt, max_opc) VALUES (%s,%s,%s,%s,%s,
    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
   
    # collection.insert_one(data)
    cursor.execute(query,(A, B, frequencydefault, seatcap, min_c_lvl, max_c_lvl, max_wait, bus_left, min_dwell, slack, lay_overtime, buscost, buslifecycle,
                     crewperbus, crewincome, cr_trip, cr_day, busmaintenance, fuelprice, kmperliter, kmperliter2, c_cantboard, c_waittime, c_invehtime, penalty, hrinperiod,
                     ser_period, dead_todepot_t1, dead_todepot_t2, layover_depot, start_ser, end_ser, shift, max_ideal, sol_per_pop, num_generations, max_oppp, min_ppvk, min_ppt,
                     max_ocpp, max_fleet, max_ppl, min_crr, min_ppp, max_pplpt, min_rvpt, max_opc))
    conn.commit()

     # Write data to CSV
    with open('parameters.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['A', 'B', 'frequencydefault', 'seatcap', 'min_c_lvl', 'max_c_lv', 'max_wait', 'bus_left', 'min_dwell', 'slack', 'lay_overtime', 'buscost', 'buslifecycle',
                     'crewperbus', 'crewincome', 'cr_trip', 'cr_day', 'busmaintenance', 'fuelprice', 'kmperliter', 'kmperliter2', 'c_cantboard', 'c_waittime', 'c_invehtime', 'penalty', 'hrinperiod',
                     'ser_period', 'dead_todepot_t1', 'dead_todepot_t2', 'layover_depot', 'start_ser', 'end_ser', 'shift', 'max_ideal', 'sol_per_pop', 'num_generations', 'max_oppp', 'min_ppvk', 'min_ppt',
                     'max_ocpp', 'max_fleet', 'max_ppl', 'min_crr', 'min_ppp', 'max_pplpt', 'min_rvpt', 'max_opc'])
        # create a list of the data that you want to write to the CSV file
        data = [A, B, frequencydefault, seatcap, min_c_lvl, max_c_lvl, max_wait, bus_left, min_dwell, slack, lay_overtime, buscost, buslifecycle,
                crewperbus, crewincome, cr_trip, cr_day, busmaintenance, fuelprice, kmperliter, kmperliter2, c_cantboard, c_waittime, c_invehtime, penalty, hrinperiod,
                ser_period, dead_todepot_t1, dead_todepot_t2, layover_depot, start_ser, end_ser, shift, max_ideal, sol_per_pop, num_generations, max_oppp, min_ppvk, min_ppt,
                max_ocpp, max_fleet, max_ppl, min_crr, min_ppp, max_pplpt, min_rvpt, max_opc]
        writer.writerow(data)

    # Open the CSV file
    with open('parameters.csv', newline='') as csvfile:
        # Read the CSV data into a dictionary
        data = csv.DictReader(csvfile)

    # Open the YAML file
    with open('parameters.yml', 'w') as ymlfile:
        # Write the YAML data to the file
        yaml.dump(data, ymlfile)


    # Close the database connection
    cursor.close()
    conn.close()

    return render_template('index.html')

# old
@app.route('/stop_coef',methods=['POST'])
def stop_coef():
    try:
        Attributes = request.form['Attributes']
        Const = request.form['Const']
        No_of_Boarding = request.form['No_of_Boarding']
        No_of_Alighting = request.form['No_of_Alighting']
        Occupancy_Level = request.form['Occupancy_Level']
        Morning_Peak = request.form['Morning_Peak']
        Before_Intersection = request.form['Before_Intersection']
        Far_from_Intersection = request.form['Far_from_Intersection']
        Commercial = request.form['Commercial']
        Transport_hub = request.form['Transport_hub']
        Bus_Bay = request.form['Bus_Bay']
        
        c = conn.cursor()

        query = "insert into stop_OLS_coefficient (Attributes, Const, No_of_Boarding, No_of_Alighting, Occupancy_Level , Morning_Peak , Before_Intersection, Far_from_Intersection, Commercial, Transport_hub ,Bus_Bay) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"

        c.execute(query, (Attributes, Const, No_of_Boarding, No_of_Alighting, Occupancy_Level , Morning_Peak, Before_Intersection, Far_from_Intersection, Commercial, Transport_hub, Bus_Bay))
        conn.commit()
       
        # Define the header row for the CSV file
        header = ['Attributes', 'Const', 'No_of_Boarding', 'No_of_Alighting', 'Occupancy_Level', 'Morning_Peak', 'Before_Intersection', 'Far_from_Intersection', 'Commercial', 'Transport_hub', 'Bus_Bay']

        # Define the row of data to be written to the CSV file
        data = [Attributes, Const, No_of_Boarding, No_of_Alighting, Occupancy_Level, Morning_Peak, Before_Intersection, Far_from_Intersection, Commercial, Transport_hub, Bus_Bay]

        # Open the CSV file in 'write' mode and write the data to it
        with open('stop OLS coefficient.csv', 'w', newline='') as file:
            writer = csv.writer(file)

            # Write the header row
            writer.writerow(header)

            # Write the data row
            writer.writerow(data)

        conn.close()

        return render_template('index.html')
    except Exception as e:
        print(e)
        return "An error occurred"

# old
@app.route('/passenger_arrival_UP', methods=['GET', 'POST'])
def passenger_arrival_UP():
    if request.method == 'POST':
        # Extract form data from request object
        data = request.form.to_dict()
        
        # Connect to MySQL database
        c = conn.cursor()
        
        # Insert each row into the database
        for i in range(1, 17):
            values = (data[f'Passenger{i}'], data[f'Garia{i}'], data[f'Patuli PS{i}'],data[f'Peerless{i}'], data[f'Ajaynagar{i}'], data[f'Kalikapur{i}'],data[f'Ruby hospital{i}'],data[f'VIP Bazaar{i}'], data[f'Science City{i}'], data[f'Metroplitan{i}'],data[f'Beliaghata XING{i}'],data[f'HUDCO{i}'], data[f'Khanna Cinema{i}'], data[f'Shyambazar{i}'], data[f'Bagbazar{i}'])
            # sql_query = "INSERT INTO Passenger_arrival_UP(Passenger, Garia, Patuli PS, Peerless, Ajaynagar, Kalikapur, Ruby hospital, VIP Bazaar, Science City, Metroplitan, Beliaghata XING, HUDCO, Khanna Cinema, Shyambazar, Bagbazar) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            sql_query = "INSERT INTO `Passenger_arrival_UP`(`Passenger`, `Garia`, `Patuli PS`, `Peerless`, `Ajaynagar`, `Kalikapur`, `Ruby hospital`, `VIP Bazaar`, `Science City`, `Metroplitan`, `Beliaghata XING`, `HUDCO`, `Khanna Cinema`, `Shyambazar`, `Bagbazar`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            c.execute(sql_query, values)
        
        # Commist changes to database
        conn.commit()
        
         # Define the header row for the CSV file
        header = ['Passenger', 'Garia', 'Patuli PS', 'Peerless', 'Ajaynagar', 'Kalikapur', 'Ruby hospital', 'VIP Bazaar', 'Science City', 'Metroplitan', 'Beliaghata XING', 'HUDCO', 'Khanna Cinema', 'Shyambazar', 'Bagbazar']
        
        # Define the row of data to be written to the CSV file
        data_row = [data[f'Passenger{i}'] for i in range(1, 17)]
        data_row.extend([data[f'Garia{i}'] for i in range(1, 17)])
        data_row.extend([data[f'Patuli PS{i}'] for i in range(1, 17)])
        data_row.extend([data[f'Peerless{i}'] for i in range(1, 17)])
        data_row.extend([data[f'Ajaynagar{i}'] for i in range(1, 17)])
        data_row.extend([data[f'Kalikapur{i}'] for i in range(1, 17)])
        data_row.extend([data[f'Ruby hospital{i}'] for i in range(1, 17)])
        data_row.extend([data[f'VIP Bazaar{i}'] for i in range(1, 17)])
        data_row.extend([data[f'Science City{i}'] for i in range(1, 17)])
        data_row.extend([data[f'Metroplitan{i}'] for i in range(1, 17)])
        data_row.extend([data[f'Beliaghata XING{i}'] for i in range(1, 17)])
        data_row.extend([data[f'HUDCO{i}'] for i in range(1, 17)])
        data_row.extend([data[f'Khanna Cinema{i}'] for i in range(1, 17)])
        data_row.extend([data[f'Shyambazar{i}'] for i in range(1, 17)])
        data_row.extend([data[f'Bagbazar{i}'] for i in range(1, 17)])
        
        # Open the CSV file in 'write' mode and write the data to it
        with open('Passenger_arrival_UP.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            
            # Write the header row
            writer.writerow(header)
            
            # Write the data row
            writer.writerow(data_row)

        # Close database connection
        conn.close()
        
        return render_template('table.html')

# old 
@app.route('/passenger_arrival_DN', methods=['GET', 'POST'])
def passenger_arrival_DN():
    if request.method == 'POST':
        # Extract form data from request object
        data = request.form.to_dict()
        
        # Connect to MySQL database
        c = conn.cursor()
        
        # Insert each row into the database
        for i in range(1, 16):
            values = (data[f'entry{i}'], data[f'entry{i}'], data[f'entry{i}'],data[f'entry{i}'], data[f'entry{i}'], data[f'entry{i}'],data[f'entry{i}'],data[f'entry{i}'], data[f'entry{i}'], data[f'entry{i}'],data[f'entry{i}'],data[f'entry{i}'], data[f'entry{i}'], data[f'entry{i}'], data[f'entry{i}'])
            # sql_query = "INSERT INTO Passenger_arrival_UP(Passenger, Garia, Patuli PS, Peerless, Ajaynagar, Kalikapur, Ruby hospital, VIP Bazaar, Science City, Metroplitan, Beliaghata XING, HUDCO, Khanna Cinema, Shyambazar, Bagbazar) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            sql_query = "INSERT INTO `Passenger_arrival_DN`(`Passenger`, `Bagbazar`, `Shyambazar`,`Khanna Cinema`, `HUDCO`,  `Beliaghata XING`, `Metroplitan`, `Science City`, `VIP Bazaar`, `Ruby hospital`,`Kalikapur`, `Ajaynagar`, `Peerless`, `Patuli PS`,`Garia`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            c.execute(sql_query, values)
        
        # Commit changes to database
        conn.commit()
        
        # Open CSV file for writing
        with open('Passenger_arrival_DN.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            # Write headers to CSV file
            writer.writerow(['Passenger', 'Bagbazar', 'Shyambazar', 'Khanna Cinema', 'HUDCO', 'Beliaghata XING', 'Metroplitan', 'Science City', 'VIP Bazaar', 'Ruby hospital', 'Kalikapur', 'Ajaynagar', 'Peerless', 'Patuli PS', 'Garia'])

            # Write data rows to CSV file
            for i in range(1, 16):
                row = [data[f'entry{i}'] for i in range(1, 16)]
                writer.writerow(row)

        # Close database connection
        conn.close()
        
        return render_template('table.html')


# old 
@app.route('/fare_UP', methods=['GET', 'POST'])
def fare_UP():
     if request.method == 'POST':
            # Get data from the HTML form
            stops = request.form.getlist('stops[]')
            garia = request.form.getlist('garia[]')
            patuli = request.form.getlist('patuli[]')
            peerless = request.form.getlist('peerless[]')
            ajaynagar = request.form.getlist('ajaynagar[]')
            kalikapur = request.form.getlist('kalikapur[]')
            ruby_hospital = request.form.getlist('ruby_hospital[]')
            vip_bazaar = request.form.getlist('vip_bazaar[]')
            science_city = request.form.getlist('science_city[]')
            metropolitan = request.form.getlist('metropolitan[]')
            beliaghata_xing = request.form.getlist('beliaghata_xing[]')
            hudco = request.form.getlist('hudco[]')
            khanna_cinema = request.form.getlist('khanna_cinema[]')
            shyambazar = request.form.getlist('shyambazar[]')
            bagbazar = request.form.getlist('bagbazar[]')

     
            # Insert data into the MySQL database
            cur = conn.cursor()
            for i in range(len(stops)):
                sql = "INSERT INTO `fare_UP`( `Stops`, `Garia`, `Patuli PS`, `Peerless`, `Ajaynagar`, `Kalikapur`, `Ruby hospital`, `VIP Bazaar`, `Science City`, `Metroplitan`, `Beliaghata XING`, `HUDCO`, `Khanna Cinema`, `Shyambazar`, `Bagbazar`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)"
                val = (stops[i], garia[i], patuli[i], peerless[i], ajaynagar[i], kalikapur[i], ruby_hospital[i], vip_bazaar[i], science_city[i], metropolitan[i], beliaghata_xing[i], hudco[i], khanna_cinema[i], shyambazar[i], bagbazar[i])
                cur.execute(sql, val)
            conn.commit()

            # Write data to CSV file
            with open('fare_UP.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Stops', 'Garia', 'Patuli PS', 'Peerless', 'Ajaynagar', 'Kalikapur', 'Ruby hospital', 'VIP Bazaar', 'Science City', 'Metroplitan', 'Beliaghata XING', 'HUDCO', 'Khanna Cinema', 'Shyambazar', 'Bagbazar'])
                for i in range(len(stops)):
                    writer.writerow([stops[i], garia[i], patuli[i], peerless[i], ajaynagar[i], kalikapur[i], ruby_hospital[i], vip_bazaar[i], science_city[i], metropolitan[i], beliaghata_xing[i], hudco[i], khanna_cinema[i], shyambazar[i], bagbazar[i]])
            
            return render_template('table.html')
  
# old
@app.route('/fare_DN', methods=['GET', 'POST'])
def fare_DN():
     if request.method == 'POST':
            # Get data from the HTML form
            stops = request.form.getlist('stops[]')
            bagbazar = request.form.getlist('bagbazar[]')
            shyambazar = request.form.getlist('shyambazar[]')
            khanna_cinema = request.form.getlist('khanna_cinema[]')
            hudco = request.form.getlist('hudco[]')
            beliaghata_xing = request.form.getlist('beliaghata_xing[]')
            metropolitan = request.form.getlist('metropolitan[]')
            science_city = request.form.getlist('science_city[]')
            vip_bazaar = request.form.getlist('vip_bazaar[]')
            ruby_hospital = request.form.getlist('ruby_hospital[]')
            kalikapur = request.form.getlist('kalikapur[]')
            ajaynagar = request.form.getlist('ajaynagar[]')
            peerless = request.form.getlist('peerless[]')
            patuli = request.form.getlist('patuli[]')
            garia = request.form.getlist('garia[]')
            
            # Insert data into the MySQL database
            cur = conn.cursor()
            for i in range(len(stops)):
                sql = "INSERT INTO `fare_DN`(`Stops`, `Bagbazar`, `Shyambazar`,`Khanna Cinema`, `HUDCO`,  `Beliaghata XING`, `Metroplitan`, `Science City`, `VIP Bazaar`, `Ruby hospital`,`Kalikapur`, `Ajaynagar`, `Peerless`, `Patuli PS`,`Garia`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                val = (stops[i], bagbazar[i], shyambazar[i], khanna_cinema[i], hudco[i], beliaghata_xing[i], metropolitan[i], science_city[i], vip_bazaar[i], ruby_hospital[i], kalikapur[i], ajaynagar[i], peerless[i], patuli[i], garia[i])
                cur.execute(sql, val)
            conn.commit()

            # Write data to CSV file
            with open('fare_DN.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Stops', 'Bagbazar', 'Shyambazar', 'Khanna Cinema', 'HUDCO', 'Beliaghata XING', 'Metroplitan', 'Science City', 'VIP Bazaar', 'Ruby hospital', 'Kalikapur', 'Ajaynagar', 'Peerless', 'Patuli PS', 'Garia'])
                for i in range(len(stops)):
                    writer.writerow([stops[i], bagbazar[i], shyambazar[i], khanna_cinema[i], hudco[i], beliaghata_xing[i], metropolitan[i], science_city[i], vip_bazaar[i], ruby_hospital[i], kalikapur[i], ajaynagar[i], peerless[i], patuli[i], garia[i]])
            
            return render_template('table.html')

# old 
@app.route('/alighting_rate_UP', methods=['GET', 'POST'])
def alighting_rate_UP():
     if request.method == 'POST':
            # Get data from the HTML form
            alighting = request.form.getlist('alighting[]')
            garia = request.form.getlist('garia[]')
            patuli = request.form.getlist('patuli[]')
            peerless = request.form.getlist('peerless[]')
            ajaynagar = request.form.getlist('ajaynagar[]')
            kalikapur = request.form.getlist('kalikapur[]')
            ruby_hospital = request.form.getlist('ruby_hospital[]')
            vip_bazaar = request.form.getlist('vip_bazaar[]')
            science_city = request.form.getlist('science_city[]')
            metropolitan = request.form.getlist('metropolitan[]')
            beliaghata_xing = request.form.getlist('beliaghata_xing[]')
            hudco = request.form.getlist('hudco[]')
            khanna_cinema = request.form.getlist('khanna_cinema[]')
            shyambazar = request.form.getlist('shyambazar[]')
            bagbazar = request.form.getlist('bagbazar[]')

     
            # Insert data into the MySQL database
            cur = conn.cursor()
            for i in range(len(alighting)):
                sql = "INSERT INTO `alighting_rate_UP`( `Alighting`, `Garia`, `Patuli PS`, `Peerless`, `Ajaynagar`, `Kalikapur`, `Ruby hospital`, `VIP Bazaar`, `Science City`, `Metroplitan`, `Beliaghata XING`, `HUDCO`, `Khanna Cinema`, `Shyambazar`, `Bagbazar`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)"
                val = (alighting[i], garia[i], patuli[i], peerless[i], ajaynagar[i], kalikapur[i], ruby_hospital[i], vip_bazaar[i], science_city[i], metropolitan[i], beliaghata_xing[i], hudco[i], khanna_cinema[i], shyambazar[i], bagbazar[i])
                cur.execute(sql, val)
            conn.commit()

            # Write data to CSV file
            with open('alighting_rate_UP.csv', 'w', newline='') as file:
                writer = csv.writer(file)
                # Write header row
                writer.writerow(['Alighting', 'Garia', 'Patuli PS', 'Peerless', 'Ajaynagar', 'Kalikapur', 'Ruby hospital', 'VIP Bazaar', 'Science City', 'Metroplitan', 'Beliaghata XING', 'HUDCO', 'Khanna Cinema', 'Shyambazar', 'Bagbazar'])
                # Write data rows
                for i in range(len(alighting)):
                    writer.writerow([alighting[i], garia[i], patuli[i], peerless[i], ajaynagar[i], kalikapur[i], ruby_hospital[i], vip_bazaar[i], science_city[i], metropolitan[i], beliaghata_xing[i], hudco[i], khanna_cinema[i], shyambazar[i], bagbazar[i]])
            
            return render_template('table.html')

# old   
@app.route('/alighting_rate_DN', methods=['GET', 'POST'])
def alighting_rate_DN():
     if request.method == 'POST':
            # Get data from the HTML form
            alighting = request.form.getlist('alighting[]')
            bagbazar = request.form.getlist('bagbazar[]')
            shyambazar = request.form.getlist('shyambazar[]')
            khanna_cinema = request.form.getlist('khanna_cinema[]')
            hudco = request.form.getlist('hudco[]')
            beliaghata_xing = request.form.getlist('beliaghata_xing[]')
            metropolitan = request.form.getlist('metropolitan[]')
            science_city = request.form.getlist('science_city[]')
            vip_bazaar = request.form.getlist('vip_bazaar[]')
            ruby_hospital = request.form.getlist('ruby_hospital[]')
            kalikapur = request.form.getlist('kalikapur[]')
            ajaynagar = request.form.getlist('ajaynagar[]')
            peerless = request.form.getlist('peerless[]')
            patuli = request.form.getlist('patuli[]')
            garia = request.form.getlist('garia[]')
            
            # Insert data into the MySQL database
            cur = conn.cursor()
            for i in range(len(alighting)):
                sql = "INSERT INTO `alighting_rate_DN`(`Alighting`, `Bagbazar`, `Shyambazar`,`Khanna Cinema`, `HUDCO`,  `Beliaghata XING`, `Metroplitan`, `Science City`, `VIP Bazaar`, `Ruby hospital`,`Kalikapur`, `Ajaynagar`, `Peerless`, `Patuli PS`,`Garia`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                val = (alighting[i], bagbazar[i], shyambazar[i], khanna_cinema[i], hudco[i], beliaghata_xing[i], metropolitan[i], science_city[i], vip_bazaar[i], ruby_hospital[i], kalikapur[i], ajaynagar[i], peerless[i], patuli[i], garia[i])
                cur.execute(sql, val)
            conn.commit()

             # Store data in a CSV file
            with open('alighting_rate_DN.csv', 'w', newline='') as file:
                writer = csv.writer(file)
                headers = ['Alighting', 'Bagbazar', 'Shyambazar', 'Khanna Cinema', 'HUDCO', 'Beliaghata XING', 'Metroplitan', 'Science City', 'VIP Bazaar', 'Ruby hospital', 'Kalikapur', 'Ajaynagar', 'Peerless', 'Patuli PS', 'Garia']
                writer.writerow(headers)
                for i in range(len(alighting)):
                    row = [alighting[i], bagbazar[i], shyambazar[i], khanna_cinema[i], hudco[i], beliaghata_xing[i], metropolitan[i], science_city[i], vip_bazaar[i], ruby_hospital[i], kalikapur[i], ajaynagar[i], peerless[i], patuli[i], garia[i]]
                    writer.writerow(row)

            return render_template('table.html')

# old
@app.route('/TraveTimeUP_ANN', methods=['GET', 'POST'])
def TraveTimeUP_ANN():
     if request.method == 'POST':
            # Get data from the HTML form
            travel_time = request.form.getlist('travel_time[]')
            garia = request.form.getlist('garia[]')
            patuli = request.form.getlist('patuli[]')
            peerless = request.form.getlist('peerless[]')
            ajaynagar = request.form.getlist('ajaynagar[]')
            kalikapur = request.form.getlist('kalikapur[]')
            ruby_hospital = request.form.getlist('ruby_hospital[]')
            vip_bazaar = request.form.getlist('vip_bazaar[]')
            science_city = request.form.getlist('science_city[]')
            metropolitan = request.form.getlist('metropolitan[]')
            beliaghata_xing = request.form.getlist('beliaghata_xing[]')
            hudco = request.form.getlist('hudco[]')
            khanna_cinema = request.form.getlist('khanna_cinema[]')
            shyambazar = request.form.getlist('shyambazar[]')
            bagbazar = request.form.getlist('bagbazar[]')

     
            # Insert data into the MySQL database
            cur = conn.cursor()
            for i in range(len(travel_time)):
                sql = "INSERT INTO `alighting_rate_UP`( `Travel Time`, `Garia`, `Patuli PS`, `Peerless`, `Ajaynagar`, `Kalikapur`, `Ruby hospital`, `VIP Bazaar`, `Science City`, `Metroplitan`, `Beliaghata XING`, `HUDCO`, `Khanna Cinema`, `Shyambazar`, `Bagbazar`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)"
                val = (travel_time[i], garia[i], patuli[i], peerless[i], ajaynagar[i], kalikapur[i], ruby_hospital[i], vip_bazaar[i], science_city[i], metropolitan[i], beliaghata_xing[i], hudco[i], khanna_cinema[i], shyambazar[i], bagbazar[i])
                cur.execute(sql, val)
            conn.commit()

            # Write data to CSV file
            with open('TraveTimeUP_ANN.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                headers = ['Travel Time', 'Garia', 'Patuli PS', 'Peerless', 'Ajaynagar', 'Kalikapur', 'Ruby hospital', 'VIP Bazaar', 'Science City', 'Metroplitan', 'Beliaghata XING', 'HUDCO', 'Khanna Cinema', 'Shyambazar', 'Bagbazar']
                writer.writerow(headers)
                for i in range(len(travel_time)):
                    row = [travel_time[i], garia[i], patuli[i], peerless[i], ajaynagar[i], kalikapur[i], ruby_hospital[i], vip_bazaar[i], science_city[i], metropolitan[i], beliaghata_xing[i], hudco[i], khanna_cinema[i], shyambazar[i], bagbazar[i]]
                    writer.writerow(row)
                    
            return render_template('table.html')

# old 
@app.route('/TravelTimeDN_ann', methods=['GET', 'POST'])
def TravelTimeDN_ann():
     if request.method == 'POST':
            # Get data from the HTML form
            travel_time = request.form.getlist('travel_time[]')
            bagbazar = request.form.getlist('bagbazar[]')
            shyambazar = request.form.getlist('shyambazar[]')
            khanna_cinema = request.form.getlist('khanna_cinema[]')
            hudco = request.form.getlist('hudco[]')
            beliaghata_xing = request.form.getlist('beliaghata_xing[]')
            metropolitan = request.form.getlist('metropolitan[]')
            science_city = request.form.getlist('science_city[]')
            vip_bazaar = request.form.getlist('vip_bazaar[]')
            ruby_hospital = request.form.getlist('ruby_hospital[]')
            kalikapur = request.form.getlist('kalikapur[]')
            ajaynagar = request.form.getlist('ajaynagar[]')
            peerless = request.form.getlist('peerless[]')
            patuli = request.form.getlist('patuli[]')
            garia = request.form.getlist('garia[]')
            
            # Insert data into the MySQL database
            cur = conn.cursor()
            for i in range(len(travel_time)):
                sql = "INSERT INTO `alighting_rate_DN`(`Travel Time`, `Bagbazar`, `Shyambazar`,`Khanna Cinema`, `HUDCO`,  `Beliaghata XING`, `Metroplitan`, `Science City`, `VIP Bazaar`, `Ruby hospital`,`Kalikapur`, `Ajaynagar`, `Peerless`, `Patuli PS`,`Garia`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                val = (travel_time[i], bagbazar[i], shyambazar[i], khanna_cinema[i], hudco[i], beliaghata_xing[i], metropolitan[i], science_city[i], vip_bazaar[i], ruby_hospital[i], kalikapur[i], ajaynagar[i], peerless[i], patuli[i], garia[i])
                cur.execute(sql, val)
            conn.commit()

            # Save data to a CSV file
            with open('TravelTimeDN_ann.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Travel Time', 'Bagbazar', 'Shyambazar', 'Khanna Cinema', 'HUDCO', 'Beliaghata XING', 'Metroplitan', 'Science City', 'VIP Bazaar', 'Ruby hospital', 'Kalikapur', 'Ajaynagar', 'Peerless', 'Patuli PS', 'Garia'])
                for i in range(len(travel_time)):
                    writer.writerow([travel_time[i], bagbazar[i], shyambazar[i], khanna_cinema[i], hudco[i], beliaghata_xing[i], metropolitan[i], science_city[i], vip_bazaar[i], ruby_hospital[i], kalikapur[i], ajaynagar[i], peerless[i], patuli[i], garia[i]])
            
            return render_template('table.html')

# -------------------------------------------SCHEDULING FILE UPLOAD----------------------------------------------------

# old
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    name = file.filename
    type = file.content_type
    size = file.content_length
    data = file.read()

    # Insert file details into the database
    with conn.cursor() as cursor:
        sql = "INSERT INTO input_holding_files (name, type, size, data) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (name, type, size, data))
        conn.commit()

    return 'File uploaded successfully!'

# old
@app.route('/files')
def files():
    # Retrieve all files from the database
    with conn.cursor() as cursor:
        sql = "SELECT * FROM input_holding_files"
        cursor.execute(sql)
        files = cursor.fetchall()
        
    print(files)  # Check the files variable
    return render_template('uploaded.html', files=files)

# old
@app.route('/download/<int:file_id>')
def download(file_id):
    # Retrieve file from the database
    with conn.cursor() as cursor:
        sql = "SELECT * FROM input_holding_files WHERE id = %s"
        cursor.execute(sql, (file_id,))
        file = cursor.fetchone()

    # Return the file as a response
    return send_file(BytesIO(file[3]), attachment_filename=file[1], as_attachment=True)

# new
@app.route('/coord')
def coord():
    return render_template('coord.html')

if __name__ == '__main__':
    app.run(debug=True)
