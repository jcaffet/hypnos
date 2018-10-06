import json
import boto3
import boto3.ec2
import os

# Code is now ugly as we are between two phases :
# - phase1 : retrieve ASG list by S3 config file
# - phase2 : retrieve ASG list by ASG tag
# In the future : code will Suspend all concerned ASG and Terminate (in one action) all tagged 'terminated' instances

def lambda_handler(event, context):

    #print("Received event : " + json.dumps(event, indent=2))
    action=event['action']

    if action not in ["stop", "start", "list"]:
        raise Exception('No action defined !')

    asgNameList = retreiveAsgList()
    print("Managing a list of %s autoscaling groups." % (len(asgNameList)))
    print("AutoScalingGroup list : %s" % (asgNameList))

    returnCode=True
    if action == "start":
        returnCode = resumeAsgList(asgNameList)
    elif action == "stop":
        returnCode=suspendAsgList(asgNameList)
        instancesToTerminate = retreiveInstancesToTerminateList(asgNameList)
        if len(instancesToTerminate) > 0:
            print("Terminating %s instances" % (len(instancesToTerminate)))
            print("EC2 instances list to terminate : %s" % (instancesToTerminate))
            if not terminateInstances(instancesToTerminate):
                returnCode=False
        else:
            print("No EC2 instance to terminate.")
    elif action == "list":
        # dryrun only
        instancesToTerminate = retreiveInstancesToTerminateList(asgNameList)
        print("Number of EC2 instances that are concerned : %s " % (len(instancesToTerminate)))
        print("EC2 instances list that are concerned : %s" % (instancesToTerminate))


    return { 
        'Return status' : returnCode
    }

def retreiveAsgList():

    asgNameList=[]
    tag_key = 'NonBusinessHoursState'
    tag_value = 'terminated'

    client = boto3.client('autoscaling')
    paginator = client.get_paginator('describe_auto_scaling_groups')
    page_iterator = paginator.paginate(PaginationConfig={'PageSize': 100})

    filtered_asgs = page_iterator.search('AutoScalingGroups[] | [?contains(Tags[?Key==`{}`].Value, `{}`)]'.format(tag_key,tag_value))
    for asg in filtered_asgs:
      asgNameList.append(asg['AutoScalingGroupName'])

    return asgNameList

def retreiveInstancesToTerminateList(asgNameList):

    instance_ids=[]
    asgclient = boto3.client('autoscaling')

    for asgName in asgNameList:
        response = asgclient.describe_auto_scaling_groups(AutoScalingGroupNames=[asgName])
        instance_ids += [i['InstanceId'] for asg in response['AutoScalingGroups'] for i in asg['Instances']]

    return instance_ids


def suspendAsgList(asgNameList):

    processesList=['Launch']
    asgclient = boto3.client('autoscaling')
    returnValue=True

    for asgName in asgNameList:
        if isExistsAsg(asgName):
            print("Suspending %s processes of %s" % (processesList, asgName))
            suspendResponse = asgclient.suspend_processes(AutoScalingGroupName=asgName, ScalingProcesses=processesList)
            if not suspendResponse:
                returnValue=False
        else:
            print("AutoScalingGroup %s does not exist !" % (asgName))
            returnValue=False

    return returnValue


def resumeAsgList(asgNameList):

    processesList=['Launch']
    asgclient = boto3.client('autoscaling')
    returnValue=True

    for asgName in asgNameList:
        if isExistsAsg(asgName):
            print("Resuming %s processes of %s" % (processesList, asgName))
            resumeResponse = asgclient.resume_processes(AutoScalingGroupName=asgName, ScalingProcesses=processesList)
            if not resumeResponse:
                returnValue=False
        else:
            print("AutoScalingGroup %s does not exist !" % (asgName))
            returnValue=False

    return returnValue

def terminateInstances(ec2instanceIds):

    # Pay attention here because using filter with empty list will return all the instances !!!
    if ec2instanceIds:
        ec2 = boto3.resource('ec2')
        print("Request to terminate following instance Ids : %s" %(ec2instanceIds))
        filtered_instances=ec2.instances.filter(InstanceIds=ec2instanceIds)
        filtered_instances.terminate()
    else:
        print("No instance to terminate")

def isExistsAsg(asgName):

    asgclient = boto3.client('autoscaling')
    asgList = asgclient.describe_auto_scaling_groups(AutoScalingGroupNames=[asgName])
    if not asgList.get('AutoScalingGroups'):
        return False
    else:
        return True

