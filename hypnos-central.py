import json
import boto3
import boto3.ec2
import os

def lambda_handler(event, context):

    print("Received event : " + json.dumps(event, indent=2))
    
    role=event['role']
    account=event['account']
    region=event['region']
    print("Role to assume : %s" % (role))
    print("Account to use : %s" % (account))
    print("Region : %s" % (region))
    
    action=event['action']
    if action in ["stop", "start", "list"]:
        print("Action : %s" % (action))
    else:
        raise Exception('No valid action value defined !')

    session = get_session(role=role, account=account, region=region, session_name='hypnos_lambda')

    returnCode=True
    if action == "start":
        # resumes tagged ASG activity which will start their linked instances
        asgNameListToStart = retreiveTaggedAsgList(session, tag_key = 'WorkingHoursState', tag_value = 'running')
        print("Number of autoscalings concerned by instance termination : %s" % (len(asgNameListToStart)))
        print("AutoScalingGroups concerned by instance termination  : %s" % (asgNameListToStart))
        returnCode = resumeAsgList(session, asgNameListToStart)

        # start all single instances tagged to running
        instanceIdListToStart = retrieveTaggedInstancesList(session, tag_key = 'WorkingHoursState', tag_value = 'running')
        if len(instanceIdListToStart) > 0:
            print("Starting %s instances" % (len(instanceIdListToStart)))
            print("EC2 instances list to start : %s" % (instanceIdListToStart))
            if not startInstances(session, instanceIdListToStart):
                returnCode=False
            else:
                print("No EC2 instance to start.")

        # start all RDS clusters tagged to started
        rdsClusterListToStart = listTaggedRdsClusters(session, tag_key = 'WorkingHoursState', tag_value = 'running')
        startRdsClusters(session, rdsClusterListToStart)
    elif action == "stop":
        # suspends tagged ASG activity and terminates their linked instances
        asgNameListToStop = retreiveTaggedAsgList(session, tag_key = 'WorkingHoursState', tag_value = 'stopped')
        returnCode=suspendAsgList(session, asgNameListToStop)
        instancesToTerminate = retreiveInstancesToTerminateList(session, asgNameListToStop)
        # terminate instances linked to a concerned autoscaling group
        if len(instancesToTerminate) > 0:
            print("Terminating %s instances" % (len(instancesToTerminate)))
            print("EC2 instances list to terminate : %s" % (instancesToTerminate))
            if not terminateInstances(session, instancesToTerminate):
                returnCode=False
        else:
            print("No EC2 instance to terminate.")

        # stop all single EC2 instances tagged to stopped
        instanceIdListToStop = retrieveTaggedInstancesList(session, tag_key = 'NonWorkingHoursState', tag_value = 'stopped')
        if len(instanceIdListToStop) > 0:
            print("Number of EC2 instances to stop: %s " % (len(instanceIdListToStop)))
            print("EC2 instances list to stop : %s" % (instanceIdListToStop))
            if not stopInstances(session, instanceIdListToStop):
                returnCode=False
        else:
            print("No EC2 instance to stop.")

        # stop all RDS clusters tagged to stopped
        rdsClusterListToStop = listTaggedRdsClusters(session, tag_key = 'NonWorkingHoursState', tag_value = 'stopped')
        stopRdsClusters(session, rdsClusterListToStop)
    elif action == "list":
        # dryrun only
        asgNameListToStart = retreiveTaggedAsgList(session, tag_key = 'WorkingHoursState', tag_value = 'running')
        asgNameListToStop = retreiveTaggedAsgList(session, tag_key = 'NonWorkingHoursState', tag_value = 'stopped')
        print("%s autoscaling groups concerned by NonWorkingHours stop : %s" % (len(asgNameListToStop), asgNameListToStop))
        print("%s autoscaling groups concerned by WorkingHours start : %s" % (len(asgNameListToStart), asgNameListToStart))

        instanceIdListToStart = retrieveTaggedInstancesList(session, tag_key = 'WorkingHoursState', tag_value = 'running')
        instanceIdListToStop = retrieveTaggedInstancesList(session, tag_key = 'NonWorkingHoursState', tag_value = 'stopped')
        print("%s EC2 instances concerned for NonWorkingHours stop : %s" % (len(instanceIdListToStop), instanceIdListToStop))
        print("%s EC2 instances concerned for WorkingHours start : %s" % (len(instanceIdListToStart), instanceIdListToStart))

        rdsClusterListToStart = listTaggedRdsClusters(session, tag_key = 'WorkingHoursState', tag_value = 'running')
        rdsClusterListToStop = listTaggedRdsClusters(session, tag_key = 'NonWorkingHoursState', tag_value = 'stopped')
        print("%s RDS clusters concerned for NonWorkingHours stop : %s" % (len(rdsClusterListToStop), extractIdentifiersFromRdsClusterList(rdsClusterListToStop)))
        print("%s RDS clusters concerned for WorkingHours start : %s" % (len(rdsClusterListToStart), extractIdentifiersFromRdsClusterList(rdsClusterListToStart)))
    return {
        'Return status' : returnCode
    }

def get_session(role=None, account=None, region=None, session_name='my_session'):

    # If the role is given : assumes a role and returns boto3 session
    # otherwise : returns a regular session with the current IAM user/role
    if role:
        client = boto3.client('sts')
        role_arn = 'arn:aws:iam::' + account + ':role/' + role
        response = client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)
        session = boto3.Session(
            aws_access_key_id=response['Credentials']['AccessKeyId'],
            aws_secret_access_key=response['Credentials']['SecretAccessKey'],
            aws_session_token=response['Credentials']['SessionToken'],
            region_name=region)
        return session
    else:
        return boto3.Session()

def suspendAsgList(session, asgNameList):

    processesList=['Launch']
    returnValue=True
    asgclient = session.client('autoscaling')

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
    returnValue=True
    asgclient = session.client('autoscaling')

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

def retreiveTaggedAsgList(session, tag_key = 'none', tag_value = 'none'):

    client = session.client('autoscaling')
    paginator = client.get_paginator('describe_auto_scaling_groups')
    page_iterator = paginator.paginate()

    asgNameList=[]
    filtered_asgs = page_iterator.search('AutoScalingGroups[] | [?contains(Tags[?Key==`{}`].Value, `{}`)]'.format(tag_key,tag_value))
    for asg in filtered_asgs:
      asgNameList.append(asg['AutoScalingGroupName'])
    return asgNameList

def retreiveAllAsgList(session):

    client = session.client('autoscaling')
    paginator = client.get_paginator('describe_auto_scaling_groups')
    asg_iterator = paginator.paginate()

    asgNameList=[]
    for asg in asg_iterator:
        asgNameList.append(asg.get('AutoScalingGroupName'))
    return asgNameList

def retreiveInstancesToTerminateList(session, asgNameList):

    instance_ids=[]
    asgclient = session.client('autoscaling')

    for asgName in asgNameList:
        response = asgclient.describe_auto_scaling_groups(AutoScalingGroupNames=[asgName])
        instance_ids += [i['InstanceId'] for asg in response['AutoScalingGroups'] for i in asg['Instances']]

    return instance_ids

def retrieveTaggedInstancesList(session, tag_key = 'none', tag_value = 'none'):

    ec2resource = session.resource('ec2')
    instanceIds = []
    filters = [{'Name': 'tag:'+tag_key, 'Values': [tag_value]}]
    for instance in ec2resource.instances.filter(Filters=filters):
        instanceIds.append(instance.id)
    return instanceIds

def retrieveAllStandaloneInstances(session):

    ec2resource = session.resource('ec2')
    
    # get a list of all instances
    all_running_instances = [i for i in ec2resource.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])]

    # get instances which belong to an ASG
    asg_instances = [i for i in ec2resource.instances.filter(Filters=[{'Name': 'tag-key', 'Values': ['aws:autoscaling:groupName']}])]

    # filter from all instances_asg the instances that are not in the filtered list
    instances_id_to_stop = [running.id for running in all_running_instances if running.id not in [i.id for i in asg_instances]]
        
    return instances_id_to_stop

def stopInstances(session, ec2instanceIds):

    # Pay attention here because using filter with empty list will return all the instances !!!
    if ec2instanceIds:
        ec2 = session.resource('ec2')
        print("Request to stop the following instances : %s" %(ec2instanceIds))
        runningInstances = ec2.instances.filter(InstanceIds=ec2instanceIds, Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        runningInstances.stop()
    else:
        print("No instance to stop")

def startInstances(session, ec2instanceIds):

    # Pay attention here because using filter with empty list will return all the instances !!!
    if ec2instanceIds:
        ec2 = session.resource('ec2')
        print("Request to start the following instances : %s" %(ec2instanceIds))
        stoppedInstances=ec2.instances.filter(InstanceIds=ec2instanceIds, Filters=[{'Name': 'instance-state-name', 'Values': ['stopped']}])
        stoppedInstances.start()
    else:
        print("No instance to start")

def terminateInstances(session, ec2instanceIds):

    # Pay attention here because using filter with empty list will return all the instances !!!
    if ec2instanceIds:
        ec2 = session.resource('ec2')
        print("Request to terminate the following instance Ids : %s" %(ec2instanceIds))
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

def stopRdsClusters(session, rdsClusters):
    client = session.client('rds')
    for rdsCluster in rdsClusters:
        # it is not accepted to stop a cluster in a Status not Available
        if rdsCluster['Status'] == "available":
            print("Stopping %s RDS cluster" % (rdsCluster['DBClusterIdentifier']))
            response = client.stop_db_cluster(DBClusterIdentifier=rdsCluster['DBClusterIdentifier'])
        else:
            print("%s RDS cluster is in %s status => no stop action" % (rdsCluster['DBClusterIdentifier'], rdsCluster['Status']))

def startRdsClusters(session, rdsClusters):
    client = session.client('rds')
    for rdsCluster in rdsClusters:
        # it is not accepted to start a cluster in a Status not Stopped
        if rdsCluster['Status'] == "stopped":
            print("Starting %s RDS cluster" % (rdsCluster['DBClusterIdentifier']))
            response = client.start_db_cluster(DBClusterIdentifier=rdsCluster['DBClusterIdentifier'])
        else:
            print("%s RDS cluster is in %s status => no start action" % (rdsCluster['DBClusterIdentifier'], rdsCluster['Status']))

def filterRdsClustersByStatus(rdsClusters, Status="none"):
    filteredRdsCluster=[]
    for rdsCluster in rdsClusters:
        if rdsCluster['Status'] == Status:
            filteredRdsClusterList.append(rdsCluster)
    return filteredRdsClusterList

def listTaggedRdsClusters(session, tag_key = 'none', tag_value = 'none'):

    client = session.client('rds')
    dbs = client.describe_db_clusters()

    rdsIdentifierList=[]
    for db in dbs['DBClusters']:
        tagresponse = client.list_tags_for_resource(ResourceName=db['DBClusterArn'])
        taglist = tagresponse['TagList']
        for tag in taglist:
            if tag['Key'] == tag_key and tag['Value'] == tag_value:
                rdsIdentifierList.append(db)
    return rdsIdentifierList

def extractIdentifiersFromRdsClusterList(rdsClusters):
    return [ rdsCluster['DBClusterIdentifier'] for rdsCluster in rdsClusters ]
