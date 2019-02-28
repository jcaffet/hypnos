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

    client = boto3.client('lambda')

    for account in accountList:
        print ("Launching action %s on %s account with role %s" % (action, account,ROLE))
        response = client.invoke(
            FunctionName=LAMBDA_TO_CALL,
            InvocationType='Event',
            Payload=json.dumps({'action': action, 'account': account, 'role': ROLE, 'mode': 'tagged'})
        )

def getAccountsFromOu(OrganizationUnit):
    client = boto3.client('organizations')
    accountsFromOu = client.list_accounts_for_parent(ParentId=OrganizationUnit)
    accounts = [account['Id'] for account in accountsFromOu['Accounts']]
    return accountsIds

def getAccountsList():
    CONFIGFILE_BUCKET = os.environ['CONFIGFILE_BUCKET']
    CONFIGFILE_NAME = os.environ['CONFIGFILE_NAME']
    tempFile = '/tmp/accounts.list'
    accountList=[]

    s3client = boto3.client('s3')
    s3client.download_file(CONFIGFILE_BUCKET, CONFIGFILE_NAME, tempFile)
    for line in open(tempFile):
      li=line.strip()
      if not li.startswith("#"):
        accountList.append(line.rstrip())
    return accountList

