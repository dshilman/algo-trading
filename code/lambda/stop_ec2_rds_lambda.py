import boto3

def lambda_handler(event, context):
    aws_region = 'us-east-1'
    
    # Create AWS clients
    ec2 = boto3.client('ec2', region_name=aws_region)
    rds = boto3.client('rds', region_name=aws_region)
    autoscaling = boto3.client('autoscaling', region_name=aws_region)
    
    # Stop EC2 instances not in an Auto Scaling Group
    stopped_ec2_instances = stop_non_asg_instances(ec2)
    
    # Scale down Auto Scaling Groups
    scaled_asgs = scale_down_asgs(autoscaling)

    # Stop all RDS instances
    stopped_rds_instances = stop_rds_instances(rds)

    return {
        'statusCode': 200,
        'body': {
            'StoppedEC2Instances': stopped_ec2_instances,
            'StoppedRDSInstances': stopped_rds_instances,
            'ScaledDownASGs': scaled_asgs
        }
    }

def stop_non_asg_instances(ec2):
    try:
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['running']},
                {'Name': 'auto-scaling-group-name', 'Values': ['*'], 'Exclude': True}
            ]
        )
        
        instances_to_stop = [
            instance['InstanceId']
            for reservation in response['Reservations']
            for instance in reservation['Instances']
        ]
        
        if instances_to_stop:
            ec2.stop_instances(InstanceIds=instances_to_stop)
            print('Stopping EC2 instances:', instances_to_stop)
        
        return instances_to_stop
    except Exception as e:
        print('Error stopping EC2 instances:', e)
        return []

def stop_rds_instances(rds):
    try:
        response = rds.describe_db_instances()
        
        dbs_to_stop = [db['DBInstanceIdentifier'] for db in response['DBInstances'] if db['DBInstanceStatus'] == 'available']
        
        for db_identifier in dbs_to_stop:
            rds.stop_db_instance(DBInstanceIdentifier=db_identifier)
            print('Stopping RDS instance:', db_identifier)
        
        return dbs_to_stop
    except Exception as e:
        print('Error stopping RDS instances:', e)
        return []

def scale_down_asgs(autoscaling):
    try:
        response = autoscaling.describe_auto_scaling_groups()
        scaled_asgs = []
        
        for asg in response['AutoScalingGroups']:
            asg_name = asg['AutoScalingGroupName']
            desired_capacity = asg['DesiredCapacity']
            
            if desired_capacity > 0:
                # Tag ASG with its current desired capacity
                autoscaling.create_or_update_tags(
                    Tags=[
                        {
                            'ResourceId': asg_name,
                            'ResourceType': 'auto-scaling-group',
                            'Key': 'PreviousDesiredCapacity',
                            'Value': str(desired_capacity),
                            'PropagateAtLaunch': False
                        }
                    ]
                )
                
                # Set the desired capacity to 0
                autoscaling.update_auto_scaling_group(
                    AutoScalingGroupName=asg_name,
                    DesiredCapacity=0
                )
                
                print(f'Scaled down ASG {asg_name} from {desired_capacity} to 0')
                scaled_asgs.append(asg_name)
        
        return scaled_asgs
    except Exception as e:
        print('Error scaling down ASGs:', e)
        return []
