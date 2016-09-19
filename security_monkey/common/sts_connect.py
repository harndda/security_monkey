#     Copyright 2014 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
"""
.. module: security_monkey.common.sts_connect
    :platform: Unix

.. version:: $$VERSION$$
.. moduleauthor:: Patrick Kelley <pkelley@netflix.com> @monkeysecurity

"""
from security_monkey.datastore import Account
import botocore.session
import boto3
import boto

def connect(account_name, connection_type, **args):
    """

    Examples of use:
    ec2 = sts_connect.connect(environment, 'ec2', region=region, validate_certs=False)
    ec2 = sts_connect.connect(environment, 'ec2', validate_certs=False, debug=1000)
    ec2 = sts_connect.connect(environment, 'ec2')
    where environment is ( test, prod, dev )
    s3  = sts_connect.connect(environment, 's3')
    ses = sts_connect.connect(environment, 'ses')

    :param account: Account to connect with (i.e. test, prod, dev)

    :raises Exception: RDS Region not valid
                       AWS Tech not supported.

    :returns: STS Connection Object for given tech

    :note: To use this method a SecurityMonkey role must be created
            in the target account with full read only privileges.
    """
    if 'assumed_role' in args:
        role = args['assumed_role']
    else:
        account = Account.query.filter(Account.name == account_name).first()
        sts = boto3.client('sts')
        role_name = 'SecurityMonkey'
        if account.role_name and account.role_name != '':
            role_name = account.role_name
        role = sts.assume_role(RoleArn='arn:aws:iam::' + account.number +
                               ':role/' + role_name, RoleSessionName='secmonkey')

    from security_monkey import app


    if connection_type == 'botocore':
        botocore_session = botocore.session.get_session()
        botocore_session.set_credentials(
            role['Credentials']['AccessKeyId'],
            role['Credentials']['SecretAccessKey'],
            token=role['Credentials']['SessionToken']
        )
        return botocore_session

    region = 'us-east-1'
    if 'region' in args:
        region = args.pop('region')
        if hasattr(region, 'name'):
            region = region.name

    if 'boto3' in connection_type:
        # Should be called in this format: boto3.iam.client
        _, tech, api = connection_type.split('.')
        session = boto3.Session(
            aws_access_key_id=role['Credentials']['AccessKeyId'],
            aws_secret_access_key=role['Credentials']['SecretAccessKey'],
            aws_session_token=role['Credentials']['SessionToken'],
            region_name=region
        )
        if api == 'resource':
            return session.resource(tech)
        return session.client(tech)

    module = __import__("boto.{}".format(connection_type))
    for subm in connection_type.split('.'):
        module = getattr(module, subm)

    return module.connect_to_region(
        region,
        aws_access_key_id=role['Credentials']['AccessKeyId'],
        aws_secret_access_key=role['Credentials']['SecretAccessKey'],
        security_token=role['Credentials']['SessionToken']
    )
