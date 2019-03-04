import boto3
import json
import os

def lambda_handler(event, context):

    print("Received event : " + json.dumps(event, indent=2))
    action=event['action']
    print("Action : %s" % (action))

    ROLE = os.environ['ROLE_TO_ASSUME']
    LAMBDA_TO_CALL = os.environ['LAMBDA_TO_CALL']

    if action not in ["stop", "start", "list"]:
        raise Exception('No valid action defined !')

    accountList=getAccountsList()
    if type(accountList) != list:
        raise Exception('No valid list of accounts !')

    regions = getAllAwsRegionsNames()
    print("Available regions : %s" % (regions))
    
    client = boto3.client('lambda')
    for account in accountList:
        for region in regions:
            print ("Launching action %s on %s account for %s with role %s" % (action, account, region, ROLE))
            response = client.invoke(
                FunctionName=LAMBDA_TO_CALL,
                InvocationType='Event',
                Payload=json.dumps({'action': action,
                                    'account': account,
                                    'region': region,
                                    'role': ROLE,
                                    'mode': 'tagged'})
            )

def getAllAwsRegionsNames():

    client = boto3.client('ec2')
    regionNames = [region['RegionName'] for region in client.describe_regions()['Regions']]
    return regionNames


def getAccountsList():

    CONFIGFILE_BUCKET = os.environ['CONFIGFILE_BUCKET']
    CONFIGFILE_NAME = os.environ['CONFIGFILE_NAME']
    tempFile = '/tmp/accounts.list'
    accountList=[]
    print(CONFIGFILE_BUCKET)
    print(CONFIGFILE_NAME)
    s3client = boto3.client('s3')
    s3client.download_file(CONFIGFILE_BUCKET, CONFIGFILE_NAME, tempFile)
    #print(open(tempFile).read())
    for line in open(tempFile):
      li=line.strip()
      if not li.startswith("#"):
        accountList.append(line.rstrip())
    return accountList


