import boto3

def lambda_handler(event, context):
    aws_region = 'us-east-1'
    
    # Create AWS clients
    ec2 = boto3.client('ec2', region_name=aws_region)
    rds = boto3.client('rds', region_name=aws_region)
    autoscaling = boto3.client('autoscaling', region_name=aws_region)

    # Start all RDS instances
    started_rds_instances = start_rds_instances(rds)

    # Start EC2 instances not in an Auto Scaling Group
    started_ec2_instances = start_non_asg_instances(ec2)
    
    # Scale up Auto Scaling Groups
    scaled_asgs = scale_up_asgs(autoscaling)
    
    return {
        'statusCode': 200,
        'body': {
            'StartedEC2Instances': started_ec2_instances,
            'StartedRDSInstances': started_rds_instances,
            'ScaledUpASGs': scaled_asgs
        }
    }

def start_non_asg_instances(ec2):
    try:
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['stopped']},
                {'Name': 'auto-scaling-group-name', 'Values': ['*'], 'Exclude': True}
            ]
        )
        
        instances_to_start = [
            instance['InstanceId']
            for reservation in response['Reservations']
            for instance in reservation['Instances']
        ]
        
        if instances_to_start:
            ec2.start_instances(InstanceIds=instances_to_start)
            print('Starting EC2 instances:', instances_to_start)
        
        return instances_to_start
    except Exception as e:
        print('Error starting EC2 instances:', e)
        return []

def start_rds_instances(rds):
    try:
        response = rds.describe_db_instances()
        
        dbs_to_start = [db['DBInstanceIdentifier'] for db in response['DBInstances'] if db['DBInstanceStatus'] == 'stopped']
        
        for db_identifier in dbs_to_start:
            rds.start_db_instance(DBInstanceIdentifier=db_identifier)
            print('Starting RDS instance:', db_identifier)
        
        return dbs_to_start
    except Exception as e:
        print('Error starting RDS instances:', e)
        return []

def scale_up_asgs(autoscaling):
    try:
        response = autoscaling.describe_auto_scaling_groups()
        scaled_asgs = []
        
        for asg in response['AutoScalingGroups']:
            asg_name = asg['AutoScalingGroupName']
            desired_capacity = 0
            
            # Retrieve the previous desired capacity from tags
            tags = {tag['Key']: tag['Value'] for tag in asg.get('Tags', [])}
            if 'PreviousDesiredCapacity' in tags:
                desired_capacity = int(tags['PreviousDesiredCapacity'])
                
                # Restore the desired capacity
                autoscaling.update_auto_scaling_group(
                    AutoScalingGroupName=asg_name,
                    DesiredCapacity=desired_capacity
                )
                
                print(f'Scaled up ASG {asg_name} to {desired_capacity}')
                scaled_asgs.append(asg_name)
        
        return scaled_asgs
    except Exception as e:
        print('Error scaling up ASGs:', e)
        return []
