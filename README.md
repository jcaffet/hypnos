# AWS Hypnos

Hypnos takes care of your security and costs by turning down AWS resources during non-business hours and start them at the beginning of working hours.

## Description

AWS Hypnos is capable to stop AWS resources during non-business hours for costs and security optimizations.

More precisely, at evening :
- suspends auto-scaling groups activity and terminates the instances
- stops standalone EC2 instances
- stops Aurora RDS clusters

In the morning of business day :
- resumes the auto-scaling groups activity, which triggers the new instances creation
- starts standalone EC2 instances
- starts Aurora RDS clusters

Hypnos works for a list of AWS accounts and will handle all the regions of the account.

## Content

There is :
- one stack for the central account (usually the sharedservices account within a multi-account context)
- one stack to deploy per spoke account with one IAM role

## Design

### Diagram
![Hypnos Diagram](images/hypnos-diagram.png)

### Cloudwatch Rule

The CloudWatch rule periodically triggers the launcher lambda depending on the configuration in the CloudFormation :
- at the end of business hours,
- at the beginning of business hours

### Launcher Lambda

There is one launcher Lambda in the central account triggered by CloudWatch Event rules. It collects accounts information in a Dynamo table to perform and asynchronously invokes lambda for each target account and each regions.

The information per item in the DynamoDB table must be :
- accountId (S)
- activeBeginWorkingHours (BOOL)
- activeEndWorkingHours (BOOL)
- beginWorkingHoursUtc (S)
- endWorkingHoursUtc (S)

The Lambda needs one parameter :
- mode : use "run" to perform actions or "dryrun" to just list actions and concerned resources.

### Central Lambda

The business lambda assumes a role on the external child account and performs the stop activity.

The Lambda needs three parameters :
- action : start, stop or list
- account : AWS account to work with
- region : AWS region to work with

For a stop action, Hypnos Lambda :
- looks for tagged autoscaling groups, suspends them and terminates all the attached instances
- looks for tagged EC2 instances in "running" status and stops them
- looks for tagged Aurora RDS clusters in "Available" status and them

For a start action, Hypnos Lambda :
- looks for concerned autoscaling groups and resumes them. Then, the ASG is launching instances corresponding to the Desired capacity setting
- looks for tagged EC2 instances in "stopped" status and starts them
- looks for tagged Aurora RDS clusters in "stopped" status and them

For a list action, Hypnos Lambda :
- only displays concerned resources without any action (dryrun mode)

## How to use Hypnos for child account users

In the child account point of view, there is no business logic to develop. The only thing to do is to
- add the appropriate tags to the concerned resources : WorkingHoursState and NonWorkingHoursState
- deploy the child role stack (if not already deployed as a StackSet)
- specify the account in the DynamoDB table with begin and end hours and if action should happen at that times.

The NonWorkingHoursState tag values could be :
- running : keep instances running during non-business hours
- stopped : for auto-scaling groups, terminates the attached instances, for standalone instances or Aurora clusters, stop them during non-business hours

The WorkingHoursState tag values could be :
- running : start instances at the beginning of business hours
- stopped : for auto-scaling groups, standalone instances and Aurora clusters keep them stopped at the beginning of business hours

It is a good practice to define different behaviors depending on the environment. With CloudFormation, use mappings :

```
Mappings:
  EnvironmentMap:
    dev:
      TagNonWorkingHoursState: 'stopped'
    uat:
      TagNonWorkingHoursState: 'stopped'
    prod:
      TagNonWorkingHoursState: 'running'
```

And retrieve the value later for the tag value :

```
- Key: NonWorkingHoursState
  Value: !FindInMap [EnvironmentMap, !Ref Environment, TagNonWorkingHoursState]
  PropagateAtLaunch: 'true'
```
