import argparse
import base64
import os
import time
import csv
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
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

    df = pd.read_csv(csv)
    userID = df.iloc[0,0]
    df = df.iloc[1:]
    df.columns = ['Time','Info']
    df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m-%d %H:%M:%S.%f').astype(np.int64)
    createConnection = pd.DataFrame(df.index[df['Info'].str.contains('HCI Command: Create Connection|HCI Command: Accept Connection Request')].tolist())
    completeConnection = pd.DataFrame(df.index[df['Info'].str.contains('HCI Event: Connect Complete')].tolist())
    connections = pd.concat([createConnection,completeConnection],axis=1)
    connections.columns = ['create','connect']
    print(connections)

    i = len(connections)-2
    mlpredictors = []

    df_test = df.iloc[connections.create[i]:connections.create[i+1]]
    authTime = df['Time'][connections.connect[i]] - df['Time'][connections.create[i]]
    totalTime = df['Time'][connections.connect[i+1]] - df['Time'][connections.connect[i]]
    packetRate = (len(df_test[df_test['Info'].str.contains('HCI Event: Number of Completed Packets')]))/(1.0*totalTime)
    eventRate = (len(df_test[df_test['Info'].str.contains('HCI Event:')]))/(1.0*totalTime)
    commandRate = (len(df_test[df_test['Info'].str.contains('HCI Command:')]))/(1.0*totalTime)
    encryptRate = (len(df_test[df_test['Info'].str.contains('HCI Event: Encrypt Change')]))/(1.0*totalTime)
    mlpredictors.append([authTime, packetRate, eventRate, commandRate, encryptRate])

    mlpredictors = pd.DataFrame(mlpredictors)
    mlpredictors.columns=['Auth Time','Packet Rate','Event Rate','Command Rate','Encrypt Rate']

    classifiers = pd.read_csv('machine-learning/mlpredictors.csv')
    classifiers.columns=['ID','Auth Time','Packet Rate','Event Rate','Command Rate','Encrypt Rate','isFalse']

    total_vector = classifiers.append(mlpredictors)

    np_vector = total_vector[['Auth Time','Packet Rate','Event Rate','Command Rate','Encrypt Rate']].as_matrix()

    kmeans = KMeans(n_clusters=2, random_state=0).fit(np_vector)

    newPredict = kmeans.predict(mlpredictors[['Auth Time','Packet Rate','Event Rate','Command Rate','Encrypt Rate']].as_matrix())[0]

    oldPredict = kmeans.predict(classifiers[['Auth Time','Packet Rate','Event Rate','Command Rate','Encrypt Rate']].as_matrix())[0]

    oldStatus = classifiers['isFalse'][0]

    if (newPredict == oldPredict):
        if (oldStatus):
            requests.post("http://succ.pxtst.com:6069/res", data={userID: '23po48ufwer', 'error': 'true'})
    else:
        if (!(oldStatus)):
            requests.post("http://succ.pxtst.com:6069/res", data={userID: '23po48ufwer', 'error': 'true'})

    # Redirect to the home page.
    return render_template('homepage.html')

@app.errorhandler(500)
def server_error(e):
    return """
    An internal error occurred: <pre>{}</pre>
    See csvs for full stacktrace.
    """.format(e), 500

if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)    
