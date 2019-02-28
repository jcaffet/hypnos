# AWS Hypnos

Hypnos takes care of your security and costs by turning down AWS ressources during non-business hours.

## Description

AWS Hypnos is capable to stop AWS resources during non-business hours for costs and security optimizations.

More precisely, at evening :
- suspends auto-scaling groups activity and terminates the instances
- stops standalone EC2 instances

In the morning of business day :
- resumes the auto-scaling groups activity, which triggers the new instances creation
- starts standalone EC2 instances 

Hypnos works for multiple accounts : just add them in the file stored in S3

It is also capable of two modes :
- all : handles of ressources of the account
- taggued : only looks for tagged ressources and avoid the other ones 

## Content

There is :
- one stack for the central account (usually the sharedservices account within a multi-account context)
- one stack to deploy per spoke account with one IAM role

## Design

### Diagram
![Hypnos Diagram](images/hypnos-diagram.png)

### Cloudwatch Rules

The two Cloudwatch rules trigger the wrapper lambda depending on the configured settings in the Cloudformation :
- at the end of business hours,
- at the beginning of business hours

### Wrapper Lambda

There is one wrapper Lambda in the central account triggered by Cloudwatch Event rules. It collects from an S3 bucket the accounts list to perform and asynchronously invokes lambda for each target account.

The wrapper lambda needs one parameters :
- action : start, stop or list

### Central Lambda

The business lambda assumes a role on the external child account and performs the stop activity.

The Lambda needs three parameters :
- action : start, stop or list
- account : AWS account to work with
- mode : use "all" to handle all the autoscaling groups and EC2 instances. Or use "tagged" to only work with tagged instances.

For a stop action, Hypnos Lambda :
- looks for tagged autoscaling groups, suspends them and terminates all the attached instances
- looks for tagged EC2 instances and stops them

For a start action, Hypnos Lambda :
- looks for concerned autoscaling groups and resumes them. Then, the ASG is launching instances corresponding to the Desired capacity setting
- looks for tagged EC2 instances and starts them

For a list action, Hypnos Lambda :
- only displays concerned ressources without any action (dry run)

## How to use Hypnos as a child account user

In the child account point of view, there is no business logic to develop. The only thing to do is to add the appropriate tag to the concerned ressouces : NonBusinessHoursState 

The NonBusinessHoursState tag values could be :
- terminated : for auto-scaling groups, terminates the attached instances
- running : keep instances running during non-business hours
- stopped : for standalone instances, stop them during non-business hours

It is a good pratice to define different behaviours depending on the environment. With Cloudformation, use mappings :

```
Mappings:
  EnvironmentMap:
    dev:
      TagNonBusinessHoursState: 'terminated'
    uat:
      TagNonBusinessHoursState: 'terminated'
    prod:
      TagNonBusinessHoursState: 'running'
```

And retreive the value later for the tag value :

```
- Key: NonBusinessHoursState
  Value: !FindInMap [EnvironmentMap, !Ref Environment, TagNonBusinessHoursState]
  PropagateAtLaunch: 'true'
```

## Limitations

- only supports up to 100 autoscaling groups per account
- only takes into account the same AWS region

