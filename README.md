cloud-dns
=========

Role to manage Route53 registers.

Requirements
------------

ansible 2.4 or newer.

Variables
--------------

- ***zone***: zone to be managed by Role.
- ***env***:
  * all: manage all env dirs.
  * {{ env }}: Manages records only for this env.
- **global_vars**: Var dict for substitution

Dependencies
------------
- boto
- boto3
- DeepDiff 

Example Playbook
----------------
```yaml
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
```
Example Zone File
----------------
```yaml
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
```
How to run playbook
----------------
```bash
ansible-playbook rebuild-dns.yml \
        -i 127.0.0.1, \
        -vvv \
        -e "env=all" \
        -e "zone=domain.com" 
```
License
-------

GPLv3

Author Information
------------------

Cloud Infrastructure Team, Linx+Neemu+Chaordic
