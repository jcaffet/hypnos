import json
import boto3
import boto3.ec2
import os

def lambda_handler(event, context):

    print("Received event : " + json.dumps(event, indent=2))
    action=event['action']
    role_arn=event['role_arn']
    print("Action : %s" % (action))
    print("Role Arn : %s" % (role_arn))

    if action not in ["stop", "start", "list"]:
        raise Exception('No action defined !')

    session = get_session(role_arn=role_arn, session_name='hypnos_lambda')

    asgNameList = retreiveAsgList(session)
    instancesTaggedForNbhStop = retrieveInstancesTaggedToStopList(session)

    returnCode=True

    if action == "start":
        print("Number of autoscalings concerned by instance termination : %s" % (len(asgNameList)))
        print("AutoScalingGroups concerned by instance termination  : %s" % (asgNameList))
        returnCode = resumeAsgList(session, asgNameList)
        if len(instancesTaggedForNbhStop) > 0:
            print("Starting %s instances" % (len(instancesTaggedForNbhStop)))
            print("EC2 instances list to start : %s" % (instancesTaggedForNbhStop))
            if not startInstances(session, instancesTaggedForNbhStop):
                returnCode=False
            else:
                print("No EC2 instance to start.")

    elif action == "stop":
        returnCode=suspendAsgList(session, asgNameList)
        instancesToTerminate = retreiveInstancesToTerminateList(session, asgNameList)
        # terminate instances linked to a concerned autoscaling group
        if len(instancesToTerminate) > 0:
            print("Terminating %s instances" % (len(instancesToTerminate)))
            print("EC2 instances list to terminate : %s" % (instancesToTerminate))
            if not terminateInstances(session, instancesToTerminate):
                returnCode=False
        else:
            print("No EC2 instance to terminate.")
        # stop concerned single instances
        if len(instancesTaggedForNbhStop) > 0:
            print("Number of EC2 instances to stop: %s " % (len(instancesTaggedForNbhStop)))
            print("EC2 instances list to stop : %s" % (instancesTaggedForNbhStop))
            if not stopInstances(session, instancesTaggedForNbhStop):
                returnCode=False
        else:
            print("No EC2 instance to stop.")
    elif action == "list":
        # dryrun only
        instancesToTerminate = retreiveInstancesToTerminateList(session, asgNameList)
        print("Number of autoscalings concerned by instance termination : %s" % (len(asgNameList)))
        print("AutoScalingGroups concerned by instance termination  : %s" % (asgNameList))
        print("Number of EC2 instances that are concerned for terminate: %s " % (len(instancesToTerminate)))
        print("EC2 instances list that are concerned for terminate: %s" % (instancesToTerminate))
        print("Number of EC2 instances that are concerned for stop: %s " % (len(instancesTaggedForNbhStop)))
        print("EC2 instances list that are concerned for stop: %s" % (instancesTaggedForNbhStop))

    return {
        'Return status' : returnCode
    }

def get_session(role_arn=None, session_name='my_session'):

    # If the role_arn is given : assumes a role and returns boto3 session
    # otherwise : returns a regular session with the current IAM user/role
    if role_arn:
        client = boto3.client('sts')
        response = client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)
        session = boto3.Session(
            aws_access_key_id=response['Credentials']['AccessKeyId'],
            aws_secret_access_key=response['Credentials']['SecretAccessKey'],
            aws_session_token=response['Credentials']['SessionToken'])
        return session
    else:
        return boto3.Session()

def suspendAsgList(session, asgNameList):

    processesList=['Launch']
    asgclient = session.client('autoscaling')
    returnValue=True

    for asgName in asgNameList:
        if isExistsAsg(session, asgName):
            print("Suspending %s processes of %s" % (processesList, asgName))
            suspendResponse = asgclient.suspend_processes(AutoScalingGroupName=asgName, ScalingProcesses=processesList)
            if not suspendResponse:
                returnValue=False
        else:
            print("AutoScalingGroup %s does not exist !" % (asgName))
            returnValue=False

    return returnValue


def resumeAsgList(session, asgNameList):

    processesList=['Launch']
    asgclient = session.client('autoscaling')
    returnValue=True

    for asgName in asgNameList:
        if isExistsAsg(session, asgName):
            print("Resuming %s processes of %s" % (processesList, asgName))
            resumeResponse = asgclient.resume_processes(AutoScalingGroupName=asgName, ScalingProcesses=processesList)
            if not resumeResponse:
                returnValue=False
        else:
            print("AutoScalingGroup %s does not exist !" % (asgName))
            returnValue=False

    return returnValue

def retreiveAsgList(session):

    tag_key = 'NonBusinessHoursState'
    tag_value = 'terminated'

    client = session.client('autoscaling')
    paginator = client.get_paginator('describe_auto_scaling_groups')
    page_iterator = paginator.paginate(PaginationConfig={'PageSize': 100})

    asgNameList=[]
    filtered_asgs = page_iterator.search('AutoScalingGroups[] | [?contains(Tags[?Key==`{}`].Value, `{}`)]'.format(tag_key,tag_value))
    for asg in filtered_asgs:
      asgNameList.append(asg['AutoScalingGroupName'])

    return asgNameList

def retreiveInstancesToTerminateList(session, asgNameList):

    instance_ids=[]
    asgclient = session.client('autoscaling')

    for asgName in asgNameList:
        response = asgclient.describe_auto_scaling_groups(AutoScalingGroupNames=[asgName])
        instance_ids += [i['InstanceId'] for asg in response['AutoScalingGroups'] for i in asg['Instances']]

    return instance_ids

def retrieveInstancesTaggedToStopList(session):

    # Retrieve Instance by Tag
    tag_key = 'NonBusinessHoursState'
    tag_value = 'stopped'

    ec2resource = session.resource('ec2')

    # instantiate empty array
    StoppedTaggedInstances = []

    filters = [{'Name': 'tag:NonBusinessHoursState', 'Values': ['stopped']}]
    for instance in ec2resource.instances.filter(Filters=filters):
        StoppedTaggedInstances.append(instance.id)

    return StoppedTaggedInstances

def stopInstances(session, ec2instanceIds):

    # Pay attention here because using filter with empty list will return all the instances !!!
    if ec2instanceIds:
        ec2 = session.resource('ec2')
        print("Request to stop following instance Ids : %s" %(ec2instanceIds))
        filtered_instances=ec2.instances.filter(InstanceIds=ec2instanceIds)
        filtered_instances.stop()
    else:
        print("No instance to stop")

def startInstances(session, ec2instanceIds):

    # Pay attention here because using filter with empty list will return all the instances !!!
    if ec2instanceIds:
        ec2 = session.resource('ec2')
        print("Request to start following instance Ids : %s" %(ec2instanceIds))
        filtered_instances=ec2.instances.filter(InstanceIds=ec2instanceIds)
        filtered_instances.start()
    else:
        print("No instance to stop")

def terminateInstances(session, ec2instanceIds):

    # Pay attention here because using filter with empty list will return all the instances !!!
    if ec2instanceIds:
        ec2 = session.resource('ec2')
        print("Request to terminate following instance Ids : %s" %(ec2instanceIds))
        filtered_instances=ec2.instances.filter(InstanceIds=ec2instanceIds)
        filtered_instances.terminate()
    else:
        print("No instance to terminate")

def isExistsAsg(session, asgName):

    asgclient = session.client('autoscaling')
    asgList = asgclient.describe_auto_scaling_groups(AutoScalingGroupNames=[asgName])
    if not asgList.get('AutoScalingGroups'):
        return False
    else:
        return True
