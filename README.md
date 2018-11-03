# AWS Hypnos

## Description

AWS Hypnos is capable to stop AWS resources during non-business hours for costs optimizations

## Content

There is :
- one stack for the central account
- one stack to deploy per child account with one IAM role
- one simple update script

## Design

There is one Lambda on the central account triggered by Cloudwatch Event rules.

The Lambda needs two parameters :
- action : start, stop or list
- role_arn : the role to assume

When stopping, Hypnos Lambda :
- looks for concerned autoscaling groups, suspend them and terminate all the attached instances

When starting, Hypnos Lambda :
- looks for concerned autoscaling groups, resunme them and then the ASG is launching instances corresponding to the Desired capacity setting

## Limitations

The actual implementation only takes into account the same region.
