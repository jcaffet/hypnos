# AWS Hypnos

## Description

AWS Hypnos is capable to stop AWS resources during non-business hours for costs and security optimizations

## Content

There is :
- one stack for the admin account (usually the sharedservices account within a multi-account context)
- one stack to deploy per spoke account with one IAM role

## Design

![Hypnos Diagram](images/hypnos-diagram.png)

There is one Lambda in one admin account triggered by Cloudwatch Event rules.

The Lambda needs two parameters :
- action : start, stop or list
- role_arn : the role to assume

At the end of business hours, the Cloudwatch Rule invokes Hypnos Lambda which :
- looks for tagged autoscaling groups, suspends them and terminates all the attached instances
- looks for tagged EC2 instances and stops them

At the beginning of business hours, the Cloudwatch Rule invokes Hypnos Lambda which :
- looks for concerned autoscaling groups and resumes them. Then, the ASG is launching instances corresponding to the Desired capacity setting
- looks for tagged EC2 instances and starts them

## Limitations

The actual implementation only takes into account the same region.

