#!/bin/bash

usage(){
    echo "Usage: $0 <env>" 
    echo "env : env to deploy" 
}

if [ $# -eq 1 ]; then
   env=$1
else
   usage;
   exit 1;
fi

case $env in
  corp)
    echo "Zipping source"
    zip hypnos-terminate.py.zip hypnos-terminate.py
    echo "Copying source"
    HYPNOS_BUCKET=operations-services-corp
    aws s3 cp hypnos-terminate.py.zip s3://${HYPNOS_BUCKET}/hypnos/
    echo "Creating stack"
    aws cloudformation create-stack \
        --stack-name operations-hypnos-central-${env} \
        --capabilities CAPABILITY_NAMED_IAM \
        --template-body file://cf-hypnos-central.yml \
        --parameters ParameterKey=Account,ParameterValue=${env}
    ;;
  dev|recprod)
    echo "Creating stacks"
    aws --profile=${env} cloudformation create-stack \
        --stack-name operations-hypnos-role-${env} \
        --capabilities CAPABILITY_NAMED_IAM \
        --template-body file://cf-hypnos-role.yml
    ;;
  *)
    echo "Unknown environment"
    exit 1
    ;;
esac

