cloudbak
========

cloudbak - a command-line tool to backup a directory to AWS S3

Requirements
------------

Python - http://python.org - tested with version 2.6.1

Boto - http://boto.readthedocs.org/en/latest/ - tested with version 2.13.3

Installation
------------

 git clone https://github.com/lee-engel-os/cloudbak.git

Configuration
-------------

Here is an example of a configuration file:

<pre>
[global]
aws_secret_access_key = XXX-YOUR-SECRET-GOES-HERE-XXX
aws_access_key_id = XXX-YOUR-KEY-GOES-HERE-XXX

[bucket:default-backups-bucket]
enable_http = true

[bucket:sensitive-backups-bucket]
enable_http = false

[/srv/data]
bucket = default-backups-bucket
expire = 60

[/srv/secure/data]
bucket = sensitive-backups-bucket
expire = 365
</pre>

Running
-------

 /path/to/cloudbak -c /path/to/cloudbak.ini
