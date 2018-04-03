#!/usr/bin/python

ANSIBLE_METADATA = {
    'metadata_version': '1.0',
    'status': ['preview'],
    'supported_by': 'Cloud Infrastructure Team, Linx+Neemu+Chaordic'
}

DOCUMENTATION = '''
args:

**zone** : zone to be managed by Role.
**env** :
  all: manage all env dirs.
  {{ env }}: Manages records only for this env.
**zone_files**: Root dir of records
**zone_files_env**: Subdir of records for current env
**global_vars**: Var dict for substitution

'''

EXAMPLES = '''
Example Playbook
----------------

    - name: Rebuild DNS
      hosts: 127.0.0.1
      connection: local
      gather_facts: true

      vars:
        var_no_log: true
        global_vars:
          GLOBAL_DNS_DOMAIN: domain.com
          GLOBAL_DNS_INTERNAL_DOMAIN: domain.internal
          GLOBAL_DNS_DEFAULT_TTL: 60
          GLOBAL_DNS_WEIGHT_ELB: 30
          GLOBAL_DNS_WEIGHT_CDN: 70

      pre_tasks:


        - name: Find zone files
          find:
            paths: "vars/dns/{{ zone }}/"
            recurse: yes
            patterns: '*.yml'
          no_log: "{{ var_no_log }} "
          register: zone_files

        - name: Find zone files for env
          find:
            paths: "vars/dns/{{ zone }}/{{ env }}"
            recurse: yes
            patterns: '*.yml'
          no_log: "{{ var_no_log }} "
          register: zone_files_env

      roles:
        - role: cloud-dns

Example Zone File
----------------

    hosted_zone_id: A1BC23DEF45GHI
    private_zone: false
    route53_zone_records:

      - record: wwww.GLOBAL_DNS_DOMAIN.
        type: CNAME
        overwrite: 'yes'
        state: create
        ttl: GLOBAL_DNS_DEFAULT_TTL
        value:
          - abc.12345678990.us-east-1.elb.amazonaws.com

      - record: prod.GLOBAL_DNS_DOMAIN.
        type: A
        overwrite: 'yes'
        state: create
        value: prod-domain2.com.
        alias: true
        identifier: prod-elb
        weight: GLOBAL_DNS_WEIGHT_ELB
        alias_hosted_zone_id: Z00000000000A
        alias_evaluate_target_health: false

      - record: prod.GLOBAL_DNS_DOMAIN.
        type: A
        overwrite: 'yes'
        state: create
        value: cabcdefghijk1.cloudfront.net.
        alias: true
        identifier: prod-cloudfront
        weight: GLOBAL_DNS_WEIGHT_CDN
        alias_hosted_zone_id: Z00000000000A
        alias_evaluate_target_health: false

How to run playbook
----------------
    ansible-playbook rebuild-dns.yml \
            -i 127.0.0.1, \
            -vvv \
            -e "env=all" \
            -e "zone=domain.com" 
'''

from ansible.module_utils.basic import AnsibleModule
import boto3
import json
import yaml
from collections import OrderedDict
from deepdiff import DeepDiff
r53 = boto3.client('route53')

def jprint(data):
    print(json.dumps(data,indent=4))

def read_files(env, find_output, find_output_env):
    """ Read files in find_output and  find_output_env to return a dict like this example:
    {
    hosted_zone_id: A1BC23DEF45GHI
    private_zone: false
    all_records: [...] # List of records
    env_records: [...]# List of records names to limit what is sent to amazon
    }
    """
    output = {}
    output['all_records'] = []
    output['env_records'] = []
    env_files_list = []
    for file_env in find_output_env:
        env_files_list.append(file_env['path'])
    for file in find_output:
        with open(file['path'], 'r') as infile:
            route53_zone_records_list = yaml.load(infile)
            if 'hosted_zone_id' in route53_zone_records_list:
                output['hosted_zone_id'] = route53_zone_records_list['hosted_zone_id']
            if 'private_zone' in route53_zone_records_list:
                output['private_zone'] = route53_zone_records_list['private_zone']
            for record in route53_zone_records_list['route53_zone_records']:
                output['all_records'].append(record)
                if env != 'all' and file['path'] in env_files_list:
                    output['env_records'].append(record['record'])
    return(output)


def expand_global_vars(records, global_vars):
    """Replace strings in records based in global_vars"""
    records = json.dumps(records)
    for key, value in global_vars.items():
        records = records.replace(key, str(value))

    output = json.loads(records)
    return(output)


def format_records(records):
    """ Create global local_records_names for checks in others functions and
    format the records because after replacing the strings some values may come with incorrect type"""
    global local_records_names
    local_records_names = []
    new_records = []
    for record in records:
        new_record = OrderedDict()
        new_record['record'] = record['record']
        local_records_names.append(record['record'])
        new_record['type'] = record['type']
        if record['overwrite'] == True:
            new_record['overwrite'] = 'yes'
        elif record['overwrite'] == False:
            new_record['overwrite'] = 'no'
        else:
            new_record['overwrite'] = record['overwrite']

        new_record['state'] = record['state']
        if 'identifier' in record.keys():
            new_record['identifier'] = record['identifier']
        if 'ttl' in record.keys():
            new_record['ttl'] = int(record['ttl'])
        new_record['value'] = []
        if 'weight' in record.keys():
            new_record['weight'] = int(record['weight'])
        if 'health_check' in record.keys():
            new_record['health_check'] = record['health_check']
        if 'alias' in record.keys():
            if isinstance(record['value'], list):
                new_record['value'] = record['value']
            else:
                new_record['value'].append(record['value'])
            new_record['alias'] = record['alias']
            new_record['alias_hosted_zone_id'] = record['alias_hosted_zone_id']
            new_record['alias_evaluate_target_health'] = record['alias_evaluate_target_health']
        else:
            if isinstance(record['value'], list):
                new_record['value'] = record['value']
            else:
                new_record['value'].append(record['value'])
        new_records.append(new_record)
    new_records = sorted(new_records)
    return(new_records)


def aws_format_records(records):
    """ Create global aws_records_names for checks in others functions and
    format the records to ansible format"""
    global aws_records_names
    aws_records_names = []
    aws_records = []
    for record in records:
        if record['Type'] == 'NS' or record['Type'] == 'SOA':
            continue
        aws_record = OrderedDict()
        aws_record['record'] = record['Name']
        aws_records_names.append(record['Name'])
        aws_record['type'] = record['Type']
        aws_record['overwrite'] = 'yes'
        aws_record['state'] = 'create'
        if 'SetIdentifier' in record.keys():
            aws_record['identifier'] = record['SetIdentifier']
        if 'Weight' in record.keys():
            aws_record['weight'] = record['Weight']
        if 'TTL' in record.keys():
            aws_record['ttl'] = record['TTL']
        aws_record['value'] = []
        if 'HealthCheckId' in record.keys():
            aws_record['health_check'] = record['HealthCheckId']
        if 'ResourceRecords' in record.keys():
            for ResourceRecords in record['ResourceRecords']:
                aws_record['value'].append(ResourceRecords['Value'])
        elif 'AliasTarget' in record.keys():
            if isinstance(record['AliasTarget']['DNSName'], list):
                aws_record['value'] = record['AliasTarget']['DNSName']
            else:
                aws_record['value'].append(record['AliasTarget']['DNSName'])
            aws_record['alias'] = True
            aws_record['alias_hosted_zone_id'] = record['AliasTarget']['HostedZoneId']
            aws_record['alias_evaluate_target_health'] = record['AliasTarget']['EvaluateTargetHealth']
            aws_record['alias_hosted_zone_id'] = record['AliasTarget']['HostedZoneId']
        aws_records.append(aws_record)
    aws_records = sorted(aws_records)
    return(aws_records)


def get_zone_records(zone_id, next_record=None):
    """ Get records from AWS"""
    if(next_record):
        response = r53.list_resource_record_sets(
            HostedZoneId=zone_id,
            StartRecordName=next_record[0],
            StartRecordType=next_record[1]
        )
    else:
        response = r53.list_resource_record_sets(HostedZoneId=zone_id)
    zone_records = response['ResourceRecordSets']
    if(response['IsTruncated']):
        zone_records += get_zone_records(
            zone_id,
            (response['NextRecordName'],
             response['NextRecordType'])
        )
    return zone_records


def mk_diff(env, var_a, var_b, env_list=None):
    output = {}
    output['diff'] = {}
    output['diff']['changes'] = []
    output['diff']['new_records'] = []
    output['diff']['manual_changes'] = []
    output['send_to_aws'] = []
    change_new = []
    change_old = []
    diff_vars = DeepDiff(var_a, var_b, ignore_order=True)
    if 'iterable_item_added' in diff_vars.keys():
        for record in diff_vars['iterable_item_added']:
            changeid = record
            r53_record = dict(OrderedDict(
                diff_vars['iterable_item_added'][changeid]))

            if r53_record['record'] in local_records_names:
                if env == 'all' or r53_record['record'] in env_list:
                    change_old.append(r53_record)
            else:
                output['diff']['manual_changes'].append(r53_record)
    if 'iterable_item_removed' in diff_vars.keys():
        for record in diff_vars['iterable_item_removed']:
            changeid = record
            r53_record = dict(OrderedDict(
                diff_vars['iterable_item_removed'][changeid]))
            if r53_record['record'] in aws_records_names:
                if env == 'all' or r53_record['record'] in env_list:
                    change_new.append(r53_record)
                    output['send_to_aws'].append(r53_record)
            else:
                if env == 'all' or r53_record['record'] in env_list:
                    output['diff']['new_records'].append(r53_record)
                    output['send_to_aws'].append(r53_record)
    if change_new != [] or change_old != []:
        output['diff']['changes'].append({'after': change_new})
        output['diff']['changes'].append({'before': change_old})
    output = json.dumps(output)
    return(output)


def run_module():

    module_args = dict(
        env=dict(type='str', required=True),
        zone_files=dict(type='list', required=True),
        zone_files_env=dict(type='list', Default=[]),
        global_vars=dict(type='dict', required=True)
    )

    result = dict(
        changed=False,
        local_json='',
        aws_json='',
        json_diff={}
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    env = module.params['env']
    zone_files = module.params['zone_files']
    zone_files_env = module.params['zone_files_env']
    global_vars = module.params['global_vars']

    # Records list for all records
    from_files_records = read_files(env, zone_files, zone_files_env)
    from_files_records = expand_global_vars(from_files_records, global_vars)

    # Records list from local files
    local_r53_zone = format_records(from_files_records['all_records'])

    # private_zone
    private_zone = from_files_records['private_zone']

    # hosted_zone_id
    hosted_zone_id = from_files_records['hosted_zone_id']

    # Get records from aws and format it 
    aws_r53_zone= get_zone_records(hosted_zone_id)
    aws_r53_zone = aws_format_records(aws_r53_zone)

    # Diff between local and aws
    diff_r53_zones = json.loads(mk_diff(
        env, local_r53_zone, aws_r53_zone, env_list=from_files_records['env_records']))

    # Record list to r53-record.yml
    result['local_json'] = local_r53_zone
    result['aws_json'] = aws_r53_zone
    result['json_diff'] = diff_r53_zones['diff']
    result['send_to_aws'] = diff_r53_zones['send_to_aws']
    result['hosted_zone_id'] = hosted_zone_id
    result['private_zone'] = private_zone

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
