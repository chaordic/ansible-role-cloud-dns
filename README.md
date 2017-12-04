Role Name
=========

Role to manage Route53 registers.

Requirements
------------

ansible 2.1 and newer.

Role Variables
--------------

**route53_zones** : the list of zones and it's registers to be managed by Role.

Dependencies
------------


Example Playbook
----------------

    - hosts: servers
      vars:
        route53_zones:
          - zone: example.com
            state: ignore
            records:
              - record: "www.example.com"
                type: CNAME
                value: 'elb.aws.com'
                ttl: 600
                overwrite: yes
                identifier: "www-elb"
                weight: 50
                health_check: "d994b780-3150-49fd-9205-356abdd42e75"
              - record: "www.example.com"
                type: CNAME
                value: 'cdn.aws.com'
                ttl: 600
                overwrite: yes
                identifier: "www-cdn"
                weight: 50
                health_check: "d994b780-3150-49fd-9205-356abdd42e75"

      roles:
         - { role: cloud-dns }

License
-------

GPLv3

Author Information
------------------

Cloud Infrastructure Team, Linx+Neemu+Chaordic
