import argparse
import base64
import os
import time
import csv
import pandas as pd
import numpy as np
import h2o
import requests

from flask import Flask, redirect, render_template, request
from google.cloud import storage

app = Flask(__name__)


@app.route('/')
def homepage():
    # Redirect to the home page.
    return render_template('homepage.html')

@app.route('/upload_csv', methods=['GET', 'POST'])
def upload_csv():
    # Create a Cloud Storage client.
    storage_client = storage.Client()

    # Get the Cloud Storage bucket that the file will be uploaded to.
    bucket = storage_client.get_bucket(os.environ.get('CLOUD_STORAGE_BUCKET'))

    # Create a new blob and upload the file's content to Cloud Storage.
    csv = request.files['file']
    blob = bucket.blob(csv.filename)
    blob.upload_from_string(csv.read())

    # Make the blob publicly viewable.
    #blob.make_public()
    #csv_public_url = blob.public_url


    h2o.init()

    # read in csv as pandas dataframe, and drop index
    df = pd.read_csv(csv)
    print('hello1')
    df.columns = ['Time','Info']
    df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m-%d %H:%M:%S.%f').astype(np.int64)
    print('hello2')
    createConnection = pd.DataFrame(df.index[df['Info'].str.contains('HCI Command: Create Connection|HCI Command: Accept Connection Request')].tolist())
    completeConnection = pd.DataFrame(df.index[df['Info'].str.contains('HCI Event: Connect Complete')].tolist())
    connections = pd.concat([createConnection,completeConnection],axis=1)
    connections.columns = ['create','connect']

    i = len(connections)-1
    print('hello3')
    mlpredictors = []

    df_test = df[connections.create[i]:connections.create[i+1]]
    authTime = df['Time'][connections.connect[i]] - df['Time'][connections.create[i]]
    totalTime = df['Time'][connections.connect[i+1]] - df['Time'][connections.connect[i]]
    packetRate = (len(df_test[df_test['Info'].str.contains('HCI Event: Number of Completed Packets')]))/(1.0*totalTime)
    eventRate = (len(df_test[df_test['Info'].str.contains('HCI Event:')]))/(1.0*totalTime)
    commandRate = (len(df_test[df_test['Info'].str.contains('HCI Command:')]))/(1.0*totalTime)
    encryptRate = (len(df_test[df_test['Info'].str.contains('HCI Event: Encrypt Change')]))/(1.0*totalTime)
    mlpredictors.append([authTime, packetRate, eventRate, commandRate, encryptRate])

    mlpredictors = pd.DataFrame(mlpredictors)
    mlpredictors.columns=['Auth Time','Packet Rate','Event Rate','Command Rate','Encrypt Rate']

    print('end of file')
    print(mlpredictors)

    #if kmeans_classifier(authTime, packetRate, eventRate, commandRate, encryptRate):
        #r = requests.post("http://succ.pxtst.com:6069/res", data={'user': '23po48ufwer', 'error': 'true'})
        #shit's going down

    # Redirect to the home page.
    return render_template('homepage.html')

@app.errorhandler(500)
def server_error(e):
    return """
    An internal error occurred: <pre>{}</pre>
    See csvs for full stacktrace.
    """.format(e), 500
