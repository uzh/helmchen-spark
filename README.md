# Setting up a stand-alone spark cluster on OpenStack


The ansible playbooks here enable the deployment of a [Spark](http://spark.apache.org) + [Hadoop](http://hadoop.apache.org) + [Jupyterhub](https://github.com/jupyter/jupyterhub) + [thunder](http://thunder-project.org/) cluster for neuroscience "Big Data" analysis on OpenStack. 

The open stack dymamic inventory code presented here is adapted from: https://github.com/lukaspustina/dynamic-inventory-for-ansible-with-openstack

Currently, `Spark` and `Jupyterhub` are controlled as services via `supervisord` while standard scripts are used for Hadoop daemons. 

## Preamble

- Create a "management" host from which to run ansible in your OpenStack dashboard
- `ssh` to the machine you just created.
- Install the pre-requisites:
```
sudo apt-get install python-pip python-dev git
sudo pip install ansible
sudo pip install python-novaclient
```
- Clone this repository:
```
git clone https://github.com/uzh/helmchen-spark
```
- Create the `roles/common/files` directory and create passwordless ssh keys there using `ssh-keygen` - these are used for authentication among the nodes: 
```
mkdir roles/common/files && ssh-keygen -f roles/common/files/spark-nodes.key
```
- Download you OpenStack RC file from the OpenStack dashboard (it's available under "Access & Security -> API Access") 
- Source your OpenStack RC file: `source <path to rc file>`, and fill in your OpenStack password. This will load information about you OpenStack Setup into your environment.
- Create the security group for spark. Since spark will start some services on random ports this will allow all tcp traffic within the security group:
```
nova secgroup-create spark "internal security group for spark"
nova secgroup-add-group-rule spark spark tcp 1 65535
```
- if you want to access the Spark/Hadoop/Jupyterhub services from the outside, you have to additionally open up these ports: 4040, 8000, 8080, 8081, 50070
- Setup the name of your network. `export OS_NETWORK_NAME="<name of your network>"` If you like you can add this to your OpenStack RC file, or set it in your `bash_rc`. (You can find the name of your network in your OpenStack dashboard)


## Create the spark/hadoop nodes


- Edit the setup variables to fit your setup. Open `group_vars/all` and setup the variables as explained there.
- Once all the variables are in place you should now be able to create your instances:
```
ansible-playbook -i localhost_inventory --private-key=<your_ssh_key> create_spark_cloud_playbook.yml
```


## Deploy Spark, Hadoop and Jupyterhub

The `spark-hadoop.yml` ansible playbook runs the necessary roles to deploy the full spark/hadoop/thunder/jupyterhub stack. It is organized into roles for each of the components. We use the [Continuum analytics miniconda installer](http://conda.pydata.org/miniconda.html) and the [ansible-conda](https://github.com/UDST/ansible-conda) to manage the required python packages. For controlling the spark and jupyterhub services, we use [supervisord](http://supervisord.org/). 

### User accounts

The playbook will automatically create user accounts for list of users specified in the `users` variable in `user_data/user-defines.yml`. For each user you must  include his/her public key named `<username>.key.pub` in `roles/common/files/user_keys`. These public keys will be injected into their `authorized_key` file. 

### Running the playbook 

The playbook is organized into roles, each of which deploys one of the components. The role layout looks like this: 

```
- roles
    - supervisord
    - miniconda
    - thunder
    - spark
    - hadoop
    - jupyterhub
```

To run the whole playbook at once, run it with (don't forget to authenticate to OS by sourcing the OpenStack RC file):
```
ansible-playbook --private-key=<private-key> -i openstack_inventory.py spark-hadoop.yml
```

In addition, the tasks are organized via tags, so you can e.g. only run the user configuration or just change the configuration files. The tags you can use are as follows: 
* `general`: java installation, ipv6 and network settings
* `user-accounts`: creating hadoop user, regular user account creation
* `downloads`: download only of spark/hadoop and other packages
* `configuration`: deploy spark/hadoop configuration files - trigers restart of daemons
* `start-service`: start/restart spark, hadoop, and jupyterhub services

In addition, each of the roles has a tag by the same name, so if you want to only run the spark tasks simply use the `spark` tag. Tags are added to the command-line: 

```
ansible-playbook --private-key=<private-key> -i openstack_inventory.py spark-hadoop.yml -t 'spark'
```

or for multiple tags

```
ansible-playbook --private-key=<private-key> -i openstack_inventory.py spark-hadoop.yml -t ['spark', 'hadoop']
```

### Hadoop

Should you need to reformat the hadoop filesystem after the instances have already been initialized and you don't want to wipe them clean, you can do this by passing the variable `hdfs_reformat=true` to the ansible playbook:

```
ansible-playbook --private-key=/Users/rok/.ssh/neurospark.pem -i openstack_inventory.py spark-hadoop.yml -t hadoop --extra-vars "hdfs_reformat=true"
```

This will wipe the hdfs clean, so make sure it's really what you want!

### Jupyterhub

Jupyterhub requires users to log in using a password. You can set an initial password for each user using a dictionary of `<username> : <password-hash>` stored in `user_data/user-passwords.yml`. To generate the hashed password, run

```
python -c "from passlib.hash import sha512_crypt; import getpass; print sha512_crypt.encrypt(getpass.getpass())"
```

You may have to first pip install the `passlib` package, depending on your system. Copy the hash into the `user_data.yml` file before configuring jupyterhub. 

### Accessing services

Once your cluster is deployed, it is recommended that you place the IPs into your `/etc/hosts` to make browsing and ssh easier. If you have done this, then the services can be reached as follows: 

spark master: http://spark-master:8080
hdfs status: http://spark-master:50070
jupyterhub: https://spark-master:8000

Note that jupyterhub uses SSL encryption, hence the 'https'.



Acknowledements
---------------
Initial version based on https://github.com/johandahlberg/ansible_spark_openstack
