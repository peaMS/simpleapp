import os
import socket
import datetime
import warnings
import requests
from flask import Flask
from flask import request
from flask import jsonify
import pymysql

def init_odbc(cx_string):
    cnxn = pyodbc.connect(cx_string)
    return cnxn

def get_sqlversion(cx):
    cursor = cx.cursor()
    cursor.execute('SELECT @@VERSION')
    return cursor.fetchall()

def get_sqlsrcip(cx):
    cursor = cx.cursor()
    cursor.execute('SELECT CONNECTIONPROPERTY("client_net_address")')
    return cursor.fetchall()

def get_sqlquery(cx, query):
    cursor = cx.cursor()
    cursor.execute(query)
    try:
        rows = cursor.fetchall()
        app.logger.info('Query "' + query + '" has returned ' + str(len(rows)) + ' rows')
        app.logger.info('Variable type for first row: ' + str(type(rows[0])))
        if len(rows) > 0:
            return rows[0][0]
        else:
            return None
    except:
        try:
            cursor.commit()
        except:
            pass
        app.logger.info('Query "' + query + '" has returned no rows')
        return None

def get_variable_value(variable_name):
    variable_value = os.environ.get(variable_name)
    basis_path='/secrets'
    variable_path = os.path.join(basis_path, variable_name)
    if variable_value == None and os.path.isfile(variable_path):
        with open(variable_path, 'r') as file:
            variable_value = file.read().replace('\n', '')
    return variable_value

# Return True if IP address is valid
def is_valid_ipv4_address(address):
    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:  # no inet_pton here, sorry
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3
    except socket.error:  # not a valid address
        return False
    return True

# To add to SQL cx to handle output
def handle_sql_variant_as_string(value):
    # return value.decode('utf-16le')
    return value.decode('utf-8')

# Send SQL query to the database
def send_sql_query(sql_server_fqdn = None, sql_server_db = None, sql_server_username = None, sql_server_password = None, sql_query = None, use_ssl=None):
    # Only set the sql_server_fqdn and db variable if not supplied as argument
    if sql_server_fqdn == None:
        sql_server_fqdn = get_variable_value('SQL_SERVER_FQDN')
    if sql_server_db == None:
        sql_server_db = get_variable_value('SQL_SERVER_DB')
    if sql_server_username == None:
        sql_server_username = get_variable_value('SQL_SERVER_USERNAME')
    if sql_server_password == None:
        sql_server_password = get_variable_value('SQL_SERVER_PASSWORD')
    if use_ssl == None:
        use_ssl = get_variable_value('USE_SSL')
        if use_ssl == None:
            use_ssl = 'yes'
    # Check we have the right variables (note that SQL_SERVER_DB is optional)
    if sql_server_username == None or sql_server_password == None or sql_server_fqdn == None:
        print('DEBUG - Required environment variables not present')
        return 'Required environment variables not present: ' + str(sql_server_fqdn) + ' :' + str(sql_server_username) + '/' + str(sql_server_password)    # Build connection string
    # MySQL query
    else:
        if sql_query == None:
            sql_query = "SELECT VERSION();"
        try:
            # Different connection strings if using a database or not, if using SSL or not
            if use_ssl == 'yes':
                if sql_server_db == None:
                    app.logger.info('Connecting with SSL to mysql server ' + str(sql_server_fqdn) + ', username ' + str(sql_server_username) + ', password ' + str(sql_server_password))
                    db = pymysql.connect(host=sql_server_fqdn, user=sql_server_username, passwd=sql_server_password, ssl={'ssl':{'ca': 'BaltimoreCyberTrustRoot.crt.pem'}})
                else:
                    app.logger.info('Connecting with SSL to mysql server ' + str(sql_server_fqdn) + ', database ' + str(sql_server_db) + ', username ' + str(sql_server_username) + ', password ' + str(sql_server_password))
                    db = pymysql.connect(host=sql_server_fqdn, user=sql_server_username, passwd=sql_server_password, database=sql_server_db, ssl={'ssl':{'ca': 'BaltimoreCyberTrustRoot.crt.pem'}})
            else:
                if sql_server_db == None:
                    app.logger.info('Connecting without SSL to mysql server ' + str(sql_server_fqdn) + ', username ' + str(sql_server_username) + ', password ' + str(sql_server_password))
                    db = pymysql.connect(host=sql_server_fqdn, user=sql_server_username, passwd=sql_server_password)
                else:
                    app.logger.info('Connecting without SSL to mysql server ' + str(sql_server_fqdn) + ', database ' + str(sql_server_db) + ', username ' + str(sql_server_username) + ', password ' + str(sql_server_password))
                    db = pymysql.connect(host=sql_server_fqdn, user=sql_server_username, passwd=sql_server_password, database=sql_server_db)
            # Send query and extract data
            cursor = db.cursor()
            cursor.execute(sql_query)
            # Option 1: first row only
            # data = cursor.fetchone()
            # Option 2: all rows
            rows = cursor.fetchall()
            data = ''
            app.logger.info('Query "' + sql_query + '" has returned ' + str(len(rows)) + ' rows')
            if len(rows) > 0:
                row_headers=[x[0] for x in cursor.description]
                json_data=[]
                for result in rows:
                    json_data.append(dict(zip(row_headers,result)))
                return json_data
            else:
                return None
            # Return value
            db.close()
            return str(data)
        except Exception as e:
            error_msg = "Error, something happened when sending a query to a MySQL server"
            app.logger.info(error_msg)
            app.logger.error(e)
            return str(e)

# Gets the web port out of an environment variable, or defaults to 8080
def get_web_port():
    web_port=os.environ.get('PORT')
    if web_port==None or not web_port.isnumeric():
        print("Using default port 8080")
        web_port=8080
    else:
        print("Port supplied as environment variable:", web_port)
    return web_port


# Start flask app
app = Flask(__name__)


# Print all headers
@app.route("/api/headers", methods=['GET'])
def headers():
    try:
        return jsonify(dict(request.headers))
    except Exception as e:
        return jsonify(str(e))


# Print all cookies
@app.route("/api/cookies", methods=['GET'])
def cookies():
    try:
        return jsonify(dict(request.cookies))
    except Exception as e:
        return jsonify(str(e))


# Flask route for healthchecks
@app.route("/api/healthcheck", methods=['GET'])
def healthcheck():
    if request.method == 'GET':
        try:
            msg = {
                'health': 'OK',
                'version': '1.0'
            }
            environment = get_variable_value('ENVIRONMENT')
            if environment != None:
                msg['environment'] = environment
            return jsonify(msg)
        except Exception as e:
            return jsonify(str(e))

# Flask route to ping the SQL server with a SQL query
@app.route("/api/sql", methods=['GET'])
def sql():
    if request.method == 'GET':
        try:
            sql_server_fqdn = request.args.get('SQL_SERVER_FQDN')   #if key doesn't exist, returns None
            sql_server_db = request.args.get('SQL_SERVER_DB')
            sql_server_username = request.args.get('SQL_SERVER_USERNAME')
            sql_server_password = request.args.get('SQL_SERVER_PASSWORD')
            use_ssl = request.args.get('USE_SSL')
            sql_query = request.args.get('QUERY')
            sql_output = send_sql_query(sql_server_fqdn=sql_server_fqdn, sql_server_db=sql_server_db, sql_server_username=sql_server_username, sql_server_password=sql_server_password, sql_query=sql_query, use_ssl=use_ssl)
            msg = {
                'sql_output': sql_output
            }          
            return jsonify(msg)
        except Exception as e:
          return jsonify(str(e))

# Flask route to ping the SQL server with a basic SQL query
@app.route("/api/sqlversion", methods=['GET'])
def sqlversion():
    if request.method == 'GET':
        sql_query = 'SELECT @@VERSION'
        try:
            sql_server_fqdn = request.args.get('SQL_SERVER_FQDN')
            sql_server_db = request.args.get('SQL_SERVER_DB')
            sql_server_username = request.args.get('SQL_SERVER_USERNAME')
            sql_server_password = request.args.get('SQL_SERVER_PASSWORD')
            app.logger.info('Values retrieved from the query: {0}, db {1}: credentials {2}/{3}'.format(str(sql_server_fqdn), str(sql_server_db), str(sql_server_username), str(sql_server_password)))
            # No need to give the query as parameter, "SELECT @@VERSION" is hte default for the function send_sql_query
            sql_output = send_sql_query(sql_server_fqdn=sql_server_fqdn, sql_server_db=sql_server_db, sql_server_username=sql_server_username, sql_server_password=sql_server_password)
            msg = {
            'sql_output': sql_output
            }          
            return jsonify(msg)
        except Exception as e:
          return jsonify(str(e))

# Return source IP of a SQL query as reported by the database
@app.route("/api/sqlsrcip", methods=['GET'])
def sqlsrcip():
    if request.method == 'GET':
        try:
            sql_server_fqdn = request.args.get('SQL_SERVER_FQDN')
            sql_server_db = request.args.get('SQL_SERVER_DB')
            sql_server_username = request.args.get('SQL_SERVER_USERNAME')
            sql_server_password = request.args.get('SQL_SERVER_PASSWORD')
            use_ssl = request.args.get('USE_SSL')
            sql_query = 'SELECT host FROM information_schema.processlist WHERE ID=connection_id();'
            app.logger.info('Values retrieved from the query: {0}, db {1}: credentials {2}/{3}'.format(str(sql_server_fqdn), str(sql_server_db), str(sql_server_username), str(sql_server_password)))
            sql_output = send_sql_query(sql_server_fqdn=sql_server_fqdn, sql_server_db=sql_server_db, sql_server_username=sql_server_username, sql_server_password=sql_server_password, sql_query=sql_query)
            msg = {
                'sql_output': sql_output
            }          
            return jsonify(msg)
        except Exception as e:
          return jsonify(str(e))

# Creates a table to log in the database connection attemtps
@app.route("/api/srcipinit", methods=['GET'])
def srcipinit():
    if request.method == 'GET':
        try:
            # Get variables from the request
            sql_server_fqdn = request.args.get('SQL_SERVER_FQDN')
            sql_server_db = request.args.get('SQL_SERVER_DB')
            sql_server_username = request.args.get('SQL_SERVER_USERNAME')
            sql_server_password = request.args.get('SQL_SERVER_PASSWORD')
            use_ssl = request.args.get('USE_SSL')
            app.logger.info('Values retrieved from the query: {0}, db {1}: credentials {2}/{3}'.format(str(sql_server_fqdn), str(sql_server_db), str(sql_server_username), str(sql_server_password)))
            # Send query to create the table in MySQL
            sql_query = 'DROP TABLE IF EXISTS srciplog;'
            sql_output = send_sql_query(sql_server_fqdn=sql_server_fqdn, sql_server_db=sql_server_db, sql_server_username=sql_server_username, sql_server_password=sql_server_password, sql_query=sql_query)
            sql_query = 'CREATE TABLE srciplog (ip varchar(15), timestamp varchar(30));'
            sql_output = send_sql_query(sql_server_fqdn=sql_server_fqdn, sql_server_db=sql_server_db, sql_server_username=sql_server_username, sql_server_password=sql_server_password, sql_query=sql_query)
            # Output
            msg = {
                'table_created': 'srciplog',
                'sql_output': sql_output
            }          
            return jsonify(msg)
        except Exception as e:
          return jsonify(str(e))

# Stores the source IP in a table in the database
@app.route("/api/srciplog", methods=['GET'])
def srciplog():
    if request.method == 'GET':
        try:
            # Get variables from the request
            sql_server_fqdn = request.args.get('SQL_SERVER_FQDN')
            sql_server_db = request.args.get('SQL_SERVER_DB')
            sql_server_username = request.args.get('SQL_SERVER_USERNAME')
            sql_server_password = request.args.get('SQL_SERVER_PASSWORD')
            use_ssl = request.args.get('USE_SSL')
            # Get source IP from DB
            # sql_query = 'SELECT host FROM information_schema.processlist WHERE ID=connection_id();'
            # app.logger.info('Values retrieved from the query: {0}, db {1}: credentials {2}/{3}'.format(str(sql_server_fqdn), str(sql_server_db), str(sql_server_username), str(sql_server_password)))
            # src_ip_address = str(send_sql_query(sql_server_fqdn=sql_server_fqdn, sql_server_db=sql_server_db, sql_server_username=sql_server_username, sql_server_password=sql_server_password, sql_query=sql_query))
            src_ip_address = str(request.remote_addr)
            # Send query to record IP in the srciplog table
            timestamp = str(datetime.datetime.utcnow())
            sql_query = "INSERT INTO srciplog (ip, timestamp) VALUES ('{0}', '{1}');".format(src_ip_address, timestamp)
            # Send query to retrieve source IP
            app.logger.info('Values retrieved from the query: {0}, db {1}: credentials {2}/{3}'.format(str(sql_server_fqdn), str(sql_server_db), str(sql_server_username), str(sql_server_password)))
            sql_output = send_sql_query(sql_server_fqdn=sql_server_fqdn, sql_server_db=sql_server_db, sql_server_username=sql_server_username, sql_server_password=sql_server_password, sql_query=sql_query)
            # Output
            msg = {
                'srciplog': {
                    'ip': src_ip_address,
                    'timestamp': timestamp,
                    'sql_output': sql_output
                }
            }          
            return jsonify(msg)
        except Exception as e:
          return jsonify(str(e))

# Stores the source IP in a table in the database
@app.route("/api/srcipget", methods=['GET'])
def srcipget():
    if request.method == 'GET':
        try:
            # Get variables from the request
            sql_server_fqdn = request.args.get('SQL_SERVER_FQDN')
            sql_server_db = request.args.get('SQL_SERVER_DB')
            sql_server_username = request.args.get('SQL_SERVER_USERNAME')
            sql_server_password = request.args.get('SQL_SERVER_PASSWORD')
            use_ssl = request.args.get('USE_SSL')
            # Send query to get srciplog table
            timestamp = str(datetime.datetime.utcnow())
            sql_query = "SELECT * FROM srciplog;"
            # Send query to retrieve source IP
            app.logger.info('Values retrieved from the query: {0}, db {1}: credentials {2}/{3}'.format(str(sql_server_fqdn), str(sql_server_db), str(sql_server_username), str(sql_server_password)))
            sql_output = send_sql_query(sql_server_fqdn=sql_server_fqdn, sql_server_db=sql_server_db, sql_server_username=sql_server_username, sql_server_password=sql_server_password, sql_query=sql_query)
            # Output
            msg = {
            'srciplog': {
                'sql_output': sql_output,
                }
            }          
            return jsonify(msg)
        except Exception as e:
          return jsonify(str(e))


# Flask route to provide Instance MetaData Service data
@app.route("/api/imds", methods=['GET'])
def imds():
    try:
        headers = {'Metadata': 'True'}
        url = 'http://169.254.169.254/metadata/instance?api-version=2017-08-01'
        msg = requests.get(url, headers=headers, timeout=1).json()
        return jsonify(msg)
    except Exception as e:
        return jsonify(str(e))

# Flask route to provide the container's environment variables
@app.route("/api/printenv", methods=['GET'])
def printenv():
    if request.method == 'GET':
        try:
            return jsonify(dict(os.environ))
        except Exception as e:
            return jsonify(str(e))

# Flask route to connect to MySQL
@app.route("/api/mysql", methods=['GET'])
def mysql():
    if request.method == 'GET':
        sql_query = 'SELECT @@VERSION'
        try:
            # Get variables
            mysql_fqdn = request.args.get('SQL_SERVER_FQDN') or get_variable_value('SQL_SERVER_FQDN')
            mysql_user = request.args.get('SQL_SERVER_USERNAME') or get_variable_value('SQL_SERVER)USERNAME')
            mysql_pswd = request.args.get('SQL_SERVER_PASSWORD') or get_variable_value('SQL_SERVER_PASSWORD')
            mysql_db = request.args.get('SQL_SERVER_DB') or get_variable_value('SQL_SERVER_DB')
            app.logger.info('Values to connect to MySQL:')
            app.logger.info(mysql_fqdn)
            app.logger.info(mysql_db)
            app.logger.info(mysql_user)
            app.logger.info(mysql_pswd)
            # The user must be in the format user@server
            mysql_name = mysql_fqdn.split('.')[0]
            if mysql_name:
                mysql_user = mysql_user + '@' + mysql_name
            else:
                return "MySql server name could not be retrieved out of FQDN"
            # Different connection strings if using a database or not
            if mysql_db == None:
                app.logger.info('Connecting to mysql server ' + str(mysql_fqdn) + ', username ' + str(mysql_user) + ', password ' + str(mysql_pswd))
                db = pymysql.connect(mysql_fqdn, mysql_user, mysql_pswd)
            else:
                app.logger.info('Connecting to mysql server ' + str(mysql_fqdn) + ', database ' + str(mysql_db) + ', username ' + str(mysql_user) + ', password ' + str(mysql_pswd))
                db = pymysql.connect(mysql_fqdn, mysql_user, mysql_pswd, mysql_db)
            # Send query and extract data
            cursor = db.cursor()
            cursor.execute("SELECT VERSION()")
            data = cursor.fetchone()
            app.logger.info('Closing SQL connection...') 
            db.close()
            msg = {
                'sql_output': str(data)
            }          
            return jsonify(msg)
        except Exception as e:
            return jsonify(str(e))

# Ignore warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")

# Set web port
web_port=get_web_port()

app.run(host='0.0.0.0', port=web_port, debug=True, use_reloader=False)
