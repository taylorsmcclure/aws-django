## Objective
Deploy an EC2 Ubuntu 16.04 instance to AWS running Django on TCP 80.

### Overview
This python3 script `aws-django.py` will do the following:

1) Using provided or stored credentials launch and EC2 Ubuntu 16.04 instance.
2) Use a post launch script to pull this repository to the instance
3) Install and enable Django to run bound to 0.0.0.0 and TCP 80

### AWS Components Created
* EC2 t2.micro instance
* VPC with one subnet routed to an IGW for external access
* Security group allowing access to TCP 22 from your IP and 0.0.0.0/0 for TCP 80

### Usage
#### Requirements
* AWS secret and access keys permitted to create/edit/update EC2 instances and VPC
* AWS secret and access keys are assumed to be in ``~/.aws/credentials`; if not you can super-ceded them via optional arguments.

1) Create a python virtual environment in this repository (Optional if you wish for packages to be available system-wide)
```
virtualenv --python python3 .
pip install -r requirements.txt
python3 aws-django.py run
```

2) Wait until you get instance information output to the terminal. Point your browser to the appropriate address. There you will see the django splash page
