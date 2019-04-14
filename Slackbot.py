import os
from slackclient import SlackClient
import boto3
from flask import abort, Flask, jsonify, request
from zappa.async import task
import json

app = Flask(__name__)

# instantiate Slack client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

# Set up cloudwatch client to pull metrics
cw = boto3.client('cloudwatch',
                  aws_access_key_id=os.environ.get('EXTERNAL_ACCESS_KEY_ID'),
                  aws_secret_access_key=os.environ.get('EXTERNAL_SECRET_ACCESS_KEY'),
                  region_name="us-east-1")

# specific metrics to pull, may move into external file to call from 
cpu_metric = '{"metrics":[["AWS/EC2","CPUUtilization","AutoScalingGroupName",' \
             '"AUTOSCALE GROUP NAME"]],"view":"timeSeries","stacked":false,' \
             '"period":300,"yAxis":{"left":{"min":0}},"title": "Autoscaling CPU Utilization", "start":"-PT1H",' \
             '"end":"P0D", "timezone":"-0800"} '
instance_metric = '{"metrics":[["AWS/AutoScaling","GroupTotalInstances","AutoScalingGroupName",' \
                  '"AUTOSCALE GROUP NAME",{"period":60}]],"view":"timeSeries","stacked":false,' \
                  '"period":300,"yAxis":{"left":{"min":0}}, "title": "Total Instances", "start":"-PT1H","end":"P0D",' \
                  '"timezone":"-0800"} '

'-----------------------------------------------------------------------------------------------------'


# checks if the request came from our slack and has the correct token. 
def is_request_valid(info):
    is_token_valid = info.form['token'] == os.environ['SLACK_VERIFICATION_TOKEN']
    is_team_id_valid = info.form['team_id'] == os.environ['SLACK_TEAM_ID']
    return is_token_valid and is_team_id_valid

# Used to find the writer database in a reader/writer RDS combo, to pull info on the writer one
def find_rds():
    db_metric_1 = '{"metrics":[["AWS/RDS","CPUUtilization","DBInstanceIdentifier",' \
                '"DATABASE 1 NAME"]],"view":"timeSeries","stacked":false,' \
                '"period":300,"yAxis":{"left":{"min":0}},"title": "DB CPU Utilization", "start":"-PT1H","end":"P0D",' \
                '"timezone":"-0800"} '
    db_metric_2 = '{"metrics":[["AWS/RDS","CPUUtilization","DBInstanceIdentifier",' \
                '"DATABASE 2 NAME"]],"view":"timeSeries","stacked":false,' \
                '"period":300,"yAxis":{"left":{"min":0}},"title": "DB CPU Utilization", "start":"-PT1H","end":"P0D",' \
                '"timezone":"-0800"} '
    rds = boto3.client('rds',aws_access_key_id=os.environ.get('EXTERNAL_ACCESS_KEY_ID'),
                  aws_secret_access_key=os.environ.get('EXTERNAL_SECRET_ACCESS_KEY'),
                  region_name="us-east-1")
    for member in rds.describe_db_clusters()['DBClusters'][0]['DBClusterMembers']:
        if member['IsClusterWriter']:
            server = member['DBInstanceIdentifier']
    if server == "SERVER NAME 1":
        return db_metric_1
    elif server == "SERVER NAME 2":
        return db_metric_2
'--------------------------------------------------------------------------------------------------------------'


# zappa async task to pull metric images as same time as normal response
@task
def pull_metric(metric, channel, comment):
    metrics = {
        'server': [cpu_metric, "Autoscaling CPU Usage for past Hour"],
        'db': [find_rds(), "Database CPU Usage for past Hour"],
        'instances': [instance_metric, "Total Autoscaling Instances"]
    }
    slack_client.api_call(
        "files.upload",
        initial_comment=comment,
        channels=channel,
        file=cw.get_metric_widget_image(MetricWidget=metrics[metric][0])['MetricWidgetImage'],
        title=metrics[metric][1]
    )
    return



# Default response if there is a command it doesn't understand
@task
def default_response(user, channel):
    slack_client.api_call(
        "chat.postEphemeral",
        user=user,
        channel=channel,
        text='Not a valid command. Please call /info help for a list of commands'
    )
    return


# zappa task for /help to return values
@task
def info_help(user, channel):
    message = json.dumps([{"text": "• `/info server` - Displays server CPU for past hour \n "
                                   "• `/info db` - Displays database CPU for past hour \n "
                                   "• `/info instances` - Shows total instances running\n ",
                           "color": "#3AA3E3", "mrkdwn_in": ['text']
                           }])
    slack_client.api_call(
        "chat.postEphemeral",
        user=user,
        channel=channel,
        attachments=message,
        mrkdwn=True
    )
    return


# parses arguments passed to bot
@task
def event_handler(info):
    command = info['text']
    comment = "Command: `/info {}` \nUser: <@{}>".format(command, info['user_id'])
    commands = {
        'server': lambda: pull_metric('server', info['channel_id'], comment),
        'db': lambda: pull_metric('db', info['channel_id'], comment),
        'instances': lambda: pull_metric('instances', info['channel_id'], comment),
        'help': lambda: info_help(info['user_id'], info['channel_id'])
    }
    commands.get(command, lambda: default_response(info['user_id'], info['channel_id']))()
    return


'---------------------------------------------------------------------------------------------------------------'


# main function, checks request and passes to event_handler, responds immediately
@app.route('/', methods=['POST'])
def main():
    if not is_request_valid(request):
        abort(400)

    event_handler(request.form)
    return jsonify(text='Got it! Please wait!')


if __name__ == '__main__':
    app.run()
