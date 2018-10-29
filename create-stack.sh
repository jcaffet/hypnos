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
  dev|recprod)
    echo "Zipping source"
    zip hypnos-terminate.py.zip hypnos-terminate.py
    echo "Copying source"
    if [ $env == "recprod" ];then
      HYPNOS_BUCKET=applications.rec
    else
      HYPNOS_BUCKET=applications.${env}
    fi
    aws --profile=${env} s3 cp hypnos-terminate.py.zip s3://${HYPNOS_BUCKET}/hypnos/
    echo "Creating stack"
    aws --profile=${env} cloudformation create-stack \
        --stack-name operations-hypnos-${env} \
        --capabilities CAPABILITY_NAMED_IAM \
        --template-body file://cf-hypnos.yml \
        --parameters ParameterKey=Account,ParameterValue=${env}
    ;;
  *)
    echo "Unknown environment"
    exit 1
    ;;
esac

