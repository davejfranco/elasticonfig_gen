## Cluster Init on AWS

This script is meant to create a cluster between Ec2 instances on AWS.

## How it works?

The script should run on every Ec2 instance that will join into de Elasticsearch Cluster. Every instance will look for its own tags to identify which "Environment", "Cluster" name and its own "Role" belongs to. Then will use the same info to discover all the nodes under those tags; this will allow the script to create a config file based on a template to join the cluster. Awesome right?

## How to deploy

Currently the script is stored on an s3 bucket called needish-ops and is there because during the elasticsearch AMI creation is pulled from that s3 bucket to be run later on when the instance is created using terraform.

## Who is the wonderful mind that came with this fantastic idea.

Dave Franco!

![](http://www.famousbirthdays.com/headshots/dave-franco-3.jpg)

sorry not that guy, this one 

![](https://media.licdn.com/mpr/mpr/shrinknp_200_200/p/7/005/084/05e/2c54faf.jpg)

