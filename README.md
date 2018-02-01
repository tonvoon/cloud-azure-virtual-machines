
# Azure - Virtual Machines Opspack

Azure Virtual Machines gives you the flexibility of virtualization for a wide range of computing solutions including development and testing, running applications, and extending your data centre. With the power to deploy applications instantly, Azure enhances security measures, provides flexibility to operate within multiple environments and scales depending on your needs.

## What You Can Monitor

Opsview Monitor's Azure Virtual Machines Opspack provides all the latest metrics to track your IAAS VM metrics. Our Opspack allows you to pull all your metrics into dashboards, graphs and powerful reporting to get the information you need to diagnose performance issues. 


## Service Checks

| Service Check |
|:------------- |
| Percentage CPU
| Network In
| Network Out
| Disk Read Bytes
| Disk Write Bytes
| Disk Write Operations/Sec
| Disk Read Operations/Sec

## Prerequisites

Tested with Python 2.7.
In order for the Opspack to run, you will need to have these packages installed by running the commands using pip.

If a cryptography error occurs when trying to install the Azure packages, you can run the commands which should fix the problem.

**Ubuntu**

```apt-get install build-essential libssl-dev libffi-dev python-dev```

**Centos**

```yum install gcc libffi-devel python-devel openssl-devel```
```
sudo apt-get install python-pip
pip install requests
pip install nagiosplugin
pip install azure
pip install azure.monitor
pip install azure.mgmt
```

## Setup and Configuration

**Setup Azure for Monitoring**

Step 1: This requires Admin access to Azure.

For the plugin to be able to connect to Azure, you will need the subscription ID, Client ID (Application ID), Secret Key and your Tenant ID (Directory ID).

First, the subscription ID can be found in the subscriptions section under the more services section.

![](/docs/img/1.png?raw=true)

![](/docs/img/2.png?raw=true)

Step 2 : Next the Tenant ID (Directory ID) can be found in the properties of the Azure Active Directory.

The client ID and Secret Key require the setup of an App in the App Registration.

Press the add button and give the App a Name, set the app type and create a sign-on URL.

![](/docs/img/3.png?raw=true)

Step 3: The Client ID called Application ID can be found in the properties of your new App.

![](/docs/img/4.png?raw=true)

Step 4: The Secret Key can be created by clicking on the All Settings of your new App and then going into the keys section.

There you can create a new key by adding the description, when it will expire and the value.

The Secret Key will be created from these details.

![](/docs/img/5.png?raw=true)

Step 5: The final step is to give access to the subscription you wish to monitor.

To do this, navigate to the Subscriptions section of Azure.

In the Subscription to be monitored, click Access Control (IAM).

Then click the add button and select Reader. After that, select the new App we created.

![](/docs/img/6.png?raw=true)

![](/docs/img/7.png?raw=true)

If you are running more than one subscription these steps will need to be done for each one you wish to monitor.

**Configure**

Step 1: Add the host template and the 'Cloud - Azure - Virtual Machines' Opspack to the host monitoring the VM's software.

![Add Host Template](/docs/img/host-template.png?raw=true)

Step 2: Add and configure the host Variables tab, add in 'AZURE_CREDENTIALS' and give it the resource group name in the value location, Subscription ID, Client ID, Secret Key and Tenant ID.

![Add Variables](/docs/img/variable.png?raw=true)

Step 3: Reload and view the VM statistics.

![View Output](/docs/img/output.png?raw=true)
