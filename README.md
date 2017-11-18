# AWS
Scripts and snippets to help with AWS work

# AutoUpdate_SGs_AWS_Public_Endpoints:
  This script runs in Lambda and autoupdates security groups (SG) to allow for egress to Amazon end point services. 
  Just subscribe to the SNS topic for AWS IP range changes and have it trigger this code.
  Since Amazon doesn't have SG's for all its end points you have to maintain egress filtering to allow instances to 
  communicate to them without having a 0.0.0.0/0 rule for egress. I grabbed some code from the AWS website, but it 
  was built for ingress only and it didn't actually work since it created more than 50 rules in the SG. 
  I added a region filter and adjusted the code to allow for egress. 
  
  Adjust the header section to fit your needs and pre-stage the SG's with the appropriate tagging. See below:
  # Header
  # Name of the service, as seen in the ip-groups.json file, to extract information for
  SERVICE = "AMAZON"

  # Name of the region, as seen in the ip-groups.json file, to extract information for
  REGION = "us-west-2"

  # Ports your application uses that need inbound permissions from the service for
  EGRESS_PORTS = { 'Http' : 80, 'Https': 443 }

  # Tags which identify the security groups you want to update
  SECURITY_GROUP_TAG_FOR_HTTP = { 'Named-Service': 'AMAZON', 'AutoUpdate': 'True', 'Protocol': 'http' }
  SECURITY_GROUP_TAG_FOR_HTTPS = { 'Named-Service': 'AMAZON', 'AutoUpdate': 'True', 'Protocol': 'https' }


# AWS IAM resources with an explicit deny:
  This snippet shows a simple deny IAM roles policy. The example shows how to give a * rule to a group of commands and 
  deny a single command out of the bundle. 
