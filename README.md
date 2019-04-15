# Slackbot
AWS Lambda Slackbot for displaying AWS info

Building a Slackbot to display AWS Cloudwatch metrics in Slack Channel

-	Requirements:
o	AWS console access
o	AWS IAM user with Cloudwatch read access
o	AWS IAM user with read/write to S3, Lambda, API Gateway
o	Admin access to Slack workspace

Basic steps:
-	Create Lambda to pull metric images from Cloudwatch using Flask backend to handle Slack POST requests
  - Uses Boto3 to get info and Slackclient to return responses
-	Deploy Lambda using Zappa to automate create of API Gateway
-	Hook API Gateway into Slack slash command

AWS/Boto3:
This slackbot pulls metric info as a picture from AWS through Boto3, the python specific SDK for connecting to AWS (https://boto3.amazonaws.com/v1/documentation/api/latest/index.html). 
 
To get the metric to graph, go to the Cloudwatch service in your AWS console, go to Metrics, select the metric would like to graph and then go to Source and select the view as Image API.
 
Copy that json into your script as the metric to pull data from.
Ex: Autoscaling Group CPU usage metric:
- cpu_metric = '{"metrics":[["AWS/EC2","CPUUtilization","AutoScalingGroupName",' \
             '"NAME_OF_AUTOSCALING_GROUP_HERE"]],"view":"timeSeries","stacked":false,' \
             '"period":300,"yAxis":{"left":{"min":0}},"title": "Autoscaling CPU Utilization", "start":"-PT1H",' \
             '"end":"P0D", "timezone":"-0800"} '

From there you want to use boto3 to set up a client connection to cloudwatch (refer to documentation for instructions for that: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html). This is where you will need to make sure that you have at least a read-only IAM user set up to pull the data. I believe there are other ways to set up a connection, but I found this to be the easiest way. 

Flask/Slackclient:
That actual processing of the POST request from Slack (more info later) is done by a simple Flask backend. Basically, if it gets a valid response, it lets the user know that it has received it, and then passes the request to a handler to pull the appropriate info. That info is passed back to the slack channel through slackclient (https://github.com/slackapi/python-slackclient) a python dev kit for Slack. Once the metric info is pulled through Boto3, it is passed back to the channel which the request was made, and the image is shown there. Most of the Flask responses are done at same time by using Flask tasks, which makes the whole process pretty quick.  

Slack:
The basic structure of a Slack slash command (https://api.slack.com/slash-commands) works by having Slack send out a POST request with various pieces of information to a specified URL and is easy to set up and understand. Once you deploy the lambda, simply take the URL for the api_gateway it gives you and place it in the response URL for the slack slash command you have created.

Zappa:
And to deploy this lambda I used Zappa (https://github.com/Miserlou/flask-zappa) to deploy. Zappa took a little while to figure out, and may be a point of contention for some people, as it requires a IAM user with deployment and execution rights to Lambda, API Gateway,  and S3 at minimum.  The actual deployment of zappa is very easy, please refer to documentation. I have included my zappa_settings.json with some personal info redacted.

There are several other tutorial for deploying python in zappa, such as: https://medium.com/velotio-perspectives/deploy-serverless-event-driven-python-applications-using-zappa-8e215e7f2c5f.

Security and Future improvements:
Of course, an important piece to consider is security. On whatever machine Zappa deploys, it would need to have access to a set of AWS credentials to an IAM user with read/write to part of your environment. This does pose some risk but can be mitigated by placing your Zappa deployment script on a locked deployment machine, with the keys saved privately on that machine. If you are wizard with AWS, you could most likely build the lambda yourself and create the API Gateway connection manually, which would mitigate the majority of the risk. 

The slack connection uses a unique Slack Bot Token to post to your team’s app and checks both the Verification Token and Slack Team Id in every request to verify if it is a valid request. There also is an option to set up an oauth structure for added security. Lastly, I passed most of the security values through environmental variables, which is not super secure. A future upgrade I have planned is to migrate the keys into something like AWS Secret Manager, since my Slackbot already exists as a Lambda. 

There are a lot of potential angles to build up from here, from things like connecting to an RDS database for direct queries, to automated email reports generated at simple slack request. The more you connect something like AWS to an external source like Slack, the more avenues for attack you leave. I would like to implement a slash command that allows for querying the read-only RDS db from Slack, to which my current thought process is to have access to the db gated by the user submitting the request, as well as a secondary password that would have to be included in the slash command.

Ex:
/info query “PASSWORD” Query, where the Flask backend checks the user that submitted against a list of authorized users and the password provided.


