import csv
import pandas as pd
import numpy as np

df = pd.read_csv('train.csv').drop('No.', axis=1)
df['Info'] = df['Info'].astype('category')
startConnection = df.index[df['Info'] == 'Rcvd Connect Complete'].tolist()

for i in range(0,len(startConnection)-1):
    if i > 0:
        df_test = df[startConnection[i]:startConnection[i+1]]
    else:
        df_test = df[0:startConnection[i]]

    if ('Rcvd Authentication Complete' in set(df_test['Info']) and 'Sent Authentication Requested' in set(df_test['Info']) and 'Rcvd Encryption Change' in set(df_test['Info']) and 'Sent Set Connection Encryption' in set(df_test['Info']) and 'Sent [I] End SDU' in set(df_test['Info'])):
        authTime = df_test['Time'][df_test.index[df_test['Info'] == 'Rcvd Authentication Complete'][0]] - df_test['Time'][df_test.index[df_test['Info'] == 'Sent Authentication Requested'][0]]
        encryptTime = df_test['Time'][df_test.index[df_test['Info'] == 'Rcvd Encryption Change'][0]] - df_test['Time'][df_test.index[df_test['Info'] == 'Sent Set Connection Encryption'][0]]
        authEncryptBoolean = df_test['Time'][df_test.index[df_test['Info'] == 'Rcvd Authentication Complete'][0]] < df_test['Time'][df_test.index[df_test['Info'] == 'Sent Set Connection Encryption'][0]]

        packetTime = []
        numPackets = len(df_test.index[df_test['Info'] == 'Sent [I] End SDU'])

        for i in range(0,numPackets):
            packetTime.append(df_test['Time'][df_test.index[df_test['Info'] == 'Sent [I] End SDU'][i]] - df_test['Time'][df_test.index[df_test['Info'] == 'Sent [I] Start SDU'][i]])

        print(authTime, encryptTime, authEncryptBoolean, np.mean(packetTime))

    else:
        print("Not a valid test set")
