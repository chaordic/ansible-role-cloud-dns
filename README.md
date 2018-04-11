cloud-dns
=========

What this role do?
  * Compare all local dns records wich aws and generate a var wich
    * changed records
    * Diferences between AWS and local records
  * Notifies slack or hipchat of changes
  * Apply chaged records
  * Notifies fails or sucessfuly rebuilds

Requirements
------------

ansible 2.3 or newer.

Variables
--------------
```yaml
# route53_check vars
hosted_zone_id: Hosted zone id
private_zone: default false
zone: zone name
zone_all_records: list with all zone records
zone_records_filter: list of records names to be changed

# Notify vars
notify_to:
  service: slack/hipchat
  room: room name to hipchat
  channel: channel name to slack

```
Dependencies
------------
- boto
- boto3
- deepdiff 

Example Playbook
----------------
```yaml
Example Playbook
----------------

    - name: Rebuild DNS
      hosts: 127.0.0.1
      connection: local
      gather_facts: true

      roles:
        - role: cloud-dns
          vars:
            hosted_zone_id: A1BC23DEF45GHI
            private_zone: false
            zone: example.com.

            zone_all_records:
              - record: wwww.example.com.
                type: CNAME
                overwrite: 'yes'
                state: create
                ttl: 60
                value:
                  - abc.12345678990.us-east-1.elb.amazonaws.com

              - record: prod.example.com.
                type: A
                overwrite: 'yes'
                state: create
                value: prod-domain2.com.
                alias: true
                identifier: prod-elb
                weight: GLOBAL_DNS_WEIGHT_ELB
                alias_hosted_zone_id: Z00000000000A
                alias_evaluate_target_health: false

              - record: prod.example.com.
                type: A
                overwrite: 'yes'
                state: create
                value: cabcdefghijk1.cloudfront.net.
                alias: true
                identifier: prod-cloudfront
                weight: 100
                alias_hosted_zone_id: Z00000000000A
                alias_evaluate_target_health: false

            zone_records_filter:
              - prod.example.com.
```
License
-------

GPLv3

Author Information
------------------

Cloud Infrastructure Team, Linx+Neemu+Chaordic
