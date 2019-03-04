import boto3
import json
import os

def lambda_handler(event, context):

    print("Event received : " + json.dumps(event, indent=2))
    
    action=event['action']
    print("Action : %s" % (action))
    if action not in ["stop", "start", "list"]:
        raise Exception('No valid action defined !')

    ROLE = os.environ['ROLE_TO_ASSUME']
    print("ROLE : %s" % (ROLE))
    
    LAMBDA_TO_CALL = os.environ['LAMBDA_TO_CALL']
    print("LAMBDA_TO_CALL : %s" % (LAMBDA_TO_CALL))
    
    CONFIGFILE_BUCKET = os.environ['CONFIGFILE_BUCKET']
    print("CONFIGFILE_BUCKET : %s" % (CONFIGFILE_BUCKET))
    
    CONFIGFILE_NAME = os.environ['CONFIGFILE_NAME']
    print("CONFIGFILE_NAME : %s" % (CONFIGFILE_NAME))

    accountList = getAccountsList(CONFIGFILE_BUCKET, CONFIGFILE_NAME)
    if type(accountList) == list:
        print("Accounts list : %s" % (accountList))
    else:
        raise Exception('No valid list of accounts !')

    regions = getAllAwsRegionsNames()
    if type(regions) == list:
        print("Regions list : %s" % (regions))
    else:
        raise Exception('No valid list of accounts !')

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

def getAccountsList(configFileBucket, configFileName):

    tempFile = '/tmp/accounts.list'
    accountList=[]

    s3client = boto3.client('s3')
    s3client.download_file(configFileBucket, configFileName, tempFile)
    #print(open(tempFile).read())
    
    # extract account from the file and avoid comments
    for line in open(tempFile):
      li=line.strip()
      if not li.startswith("#"):
        accountList.append(line.rstrip())
    return accountList

