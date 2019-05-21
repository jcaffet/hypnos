import boto3
import json
import os
from datetime import datetime, date, time, timedelta

def lambda_handler(event, context):

    print("Event received : " + json.dumps(event, indent=2))

    if event['mode']:
        mode = event['mode']
        if mode in ["dryrun"]:
            print("Mode : %s" % (mode))
    else:
        print("No mode detected")

    LAMBDA_TO_CALL = os.environ['LAMBDA_TO_CALL']
    if LAMBDA_TO_CALL:
        print("LAMBDA_TO_CALL : %s" % (LAMBDA_TO_CALL))
    else:
        raise Exception('LAMBDA_TO_CALL not found !')

    ACCOUNTSCONFIG_TABLE = os.environ['ACCOUNTSCONFIG_TABLE']
    if ACCOUNTSCONFIG_TABLE:
        print("ACCOUNTSCONFIG_TABLE : %s" % (ACCOUNTSCONFIG_TABLE))
    else:
        raise Exception('ACCOUNTSCONFIG_TABLE not found !')

    accountList = getAccountsList(ACCOUNTSCONFIG_TABLE)
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
        accountId = account["accountId"]
        beginWorkingHoursUtc = account["beginWorkingHoursUtc"]
        activeBeginWorkingHours = account["activeBeginWorkingHours"]
        endWorkingHoursUtc = account["endWorkingHoursUtc"]
        activeEndWorkingHours = account["activeEndWorkingHours"]

        begin=datetime.strptime(beginWorkingHoursUtc,'%H:%M')
        end=datetime.strptime(endWorkingHoursUtc,'%H:%M')
        now_string=datetime.now().strftime('%H:%M')
        now=datetime.strptime(now_string,'%H:%M')
        delta=timedelta(minutes=15)

        # determine the action to have depending on the incoming parameters
        print("Determining action for accountId %s for now at %s with begin %s and end %s (UTC hours)" % (accountId, now.strftime('%H:%M'), begin.strftime('%H:%M'), end.strftime('%H:%M')))
        action="none"
        if begin<end:
            print("UTC Begin hour is before the End hour.")
            if now>=begin and now<end:
                print("Working hours.")
                if isInLaunchingPeriod(begin, now, delta):
                    if activeBeginWorkingHours:
                        print("Start on working-hours enabled => launch start action")
                        action="start"
                    else:
                        print("Start on working-hours disabled => no start action")
                        action="none"
            else:
                print("Non Working hours.")
                if isInLaunchingPeriod(end, now, delta):
                    if activeEndWorkingHours:
                        print("Stop on Working-hours enabled => launch stop action")
                        action="stop"
                    else:
                        print("Stop on working-hours disabled => no stop action")
                        action="none"
        else:
            print("UTC Begin hour is after the End hour.")
            if now>end and now<begin:
                print("Non Working hours.")
                if isInLaunchingPeriod(end, now, delta):
                    if activeEndWorkingHours:
                        print("Stop on working-hours enabled => launch stop action")
                        action="stop"
                    else:
                        print("Stop on working-hours disabled => no stop action")
                        action="none"
            else:
                print("Working hours.")
                if isInLaunchingPeriod(begin, now, delta):
                    if activeBeginWorkingHours:
                        print("Start on working-hours enabled => launch start action")
                        action="start"
                    else:
                        print("Start on working-hours disabled => no start action")
                        action="none"

        if mode != "dryrun":
            if action != "none":
                launchLambdaForAllRegions(client, LAMBDA_TO_CALL, accountId, regions, action)
            else:
                print("No action decided for %s" % (accountId))
        else:
            launchLambdaForAllRegions(client, LAMBDA_TO_CALL, accountId, regions, "list")

    return {
        'accountList': accountList,
    }

def launchLambdaForAllRegions(client, lambdaName, account, regions, action = "none"):
    for region in regions:
        print ("Launching action %s on %s account for %s region." % (action, account, region))
        launchLambda(client, lambdaName, account, region, action)

def launchLambda(client, lambdaName, account, region, action = "none"):
    if action != "none":
        response = client.invoke(
            FunctionName=lambdaName,
            InvocationType='Event',
            Payload=json.dumps({'action': action,
                                'account': account,
                                'region': region
                                })
            )
    else:
        print("No action defined")

def isInLaunchingPeriod(period_begin, now, delta):
  if now>=period_begin and now<period_begin+delta:
      print("Launching period detected.")
      return True
  else:
      print("Out of launching period.")
      return False

def getAllAwsRegionsNames():

    client = boto3.client('ec2')
    regionNames = [region['RegionName'] for region in client.describe_regions()['Regions']]
    return regionNames

def getAccountsList(AccountsConfigTable):

    client = boto3.resource('dynamodb')
    table = client.Table(AccountsConfigTable)
    response = table.scan()
    accounts = response['Items']

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        accounts.extend(response['Items'])

    return accounts
