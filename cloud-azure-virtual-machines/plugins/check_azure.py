#!/usr/bin/env python

import datetime
import argparse
import os
import sys
import requests.packages.urllib3
import nagiosplugin
from nagiosplugin import Cookie
from azure.monitor import MonitorClient
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.common.credentials import ServicePrincipalCredentials
from requests.packages.urllib3.exceptions import InsecurePlatformWarning
from requests.packages.urllib3.exceptions import SNIMissingWarning
from azure.monitor.models.error_response import ErrorResponseException
from azure.mgmt.compute import ComputeManagementClient

# Stop SNIMissingWarning and InsecurePlatformWarning warnings
requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
requests.packages.urllib3.disable_warnings(SNIMissingWarning)

MINUTE_IN_SECONDS = 60


class PluginError(Exception):
    pass


class Metric(nagiosplugin.Resource):
    def probe(self):
        dispatch_mode = create_dispatch_table()

        if args.mode == 'generic':
            if not args.provider:
                raise PluginError("Missing the -p provider argument")
            elif not args.aggregation:
                raise PluginError("Missing the -a aggregation argument")
            elif not args.metric:
                raise PluginError("Missing the -M metric argument")

        try:
            metric_result, mode, uom = get_metric(dispatch_mode[args.mode])
        except KeyError:
            raise PluginError("Mode {} does not exist".format(args.mode))

        yield nagiosplugin.Metric(
            mode, int(metric_result), context=args.mode, uom=uom
        )


def get_args():
    parser = argparse.ArgumentParser(
        description="Run any predefined mode"
    )

    parser.add_argument(
        '-H', dest='hostaddress', required=True,
        type=str, help="Name of the system being monitored"
    )
    parser.add_argument(
        '-r', dest='resource', required=True,
        type=str, help="Resource ID"
    )
    parser.add_argument(
        '-s', dest='subscription', required=True,
        type=str, help="Subscription ID"
    )
    parser.add_argument(
        '-C', dest='client', required=True,
        type=str, help="Client ID (Also known as Application ID)"
    )
    parser.add_argument(
        '-S', dest='secret', required=True,
        type=str, help="Secret Key"
    )
    parser.add_argument(
        '-t', dest='tenant', required=True,
        type=str, help="Tenant ID (Also known as Directory ID)"
    )
    parser.add_argument(
        '-m', dest='mode', required=True,
        type=str, help="Metric to be monitored"
    )
    parser.add_argument(
        '-w', dest='warning',
        type=int, help="The warning level"
    )
    parser.add_argument(
        '-c', dest='critical',
        type=int, help="The critical level"
    )
    parser.add_argument(
        '-e', dest='extraprovider',
        type=str, help="Add extra search value to the provider"
    )
    parser.add_argument(
        '-M', dest='metric',
        type=str, help="Metric name for use with generic mode"
    )
    parser.add_argument(
        '-p', dest='provider',
        type=str, help="Provider type of system the metric is taken from"
    )
    parser.add_argument(
        '-a', dest='aggregation', type=str,
        help="Type used for monitoring(Average, Total, Maximum)"
    )
    parser.add_argument(
        '-u', dest='uom', default='',
        type=str, help="The metric type"
    )
    parser.add_argument(
        '--debug', dest='debug', action='store_true',
        help="Output more detail for debugging purposes"
    )

    return parser.parse_args()


def create_dispatch_table():
    vm_provider = 'Microsoft.Compute/VirtualMachines'
    vmss_provider = 'Microsoft.Compute/virtualMachineScaleSets'
    vmssvm_provider = (
        'Microsoft.Compute/virtualMachineScaleSets/' +
        '{}/virtualMachines'.format(args.extraprovider)
    )
    mysql_provider = 'Microsoft.DBforMySQL/servers'
    pgsql_provider = 'Microsoft.DBforPostgreSQL/servers'
    iot_provider = 'Microsoft.Devices/IotHubs'
    sql_provider = (
        'Microsoft.Sql/servers/{}/databases'.format(args.extraprovider)
    )
    ep_provider = (
        'Microsoft.Sql/servers/{}/elasticPools'.format(args.extraprovider)
    )
    redis_provider = 'Microsoft.Cache/redis'

    return {
        'VM.PercentageCPU':
            [vm_provider, '%', 'Average', 'Percentage CPU'],
        'VM.NetworkIn':
            [vm_provider, 'b', 'Total', 'Network In'],
        'VM.NetworkOut':
            [vm_provider, 'b', 'Total', 'Network Out'],
        'VM.BytesRead':
            [vm_provider, 'b', 'Total', 'Disk Read Bytes'],
        'VM.BytesWritten':
            [vm_provider, 'b', 'Total', 'Disk Write Bytes'],
        'VM.WriteOperations':
            [vm_provider, 'PerSecond', 'Average', 'Disk Write Operations/Sec'],
        'VM.ReadOperations':
            [vm_provider, 'PerSecond', 'Average', 'Disk Read Operations/Sec'],
        'VMSS.PercentageCPU':
            [vmss_provider, '%', 'Average', 'Percentage CPU'],
        'VMSS.NetworkIn':
            [vmss_provider, 'b', 'Total', 'Network In'],
        'VMSS.NetworkOut':
            [vmss_provider, 'b', 'Total', 'Network Out'],
        'VMSS.BytesRead':
            [vmss_provider, 'b', 'Total', 'Disk Read Bytes'],
        'VMSS.BytesWritten':
            [vmss_provider, 'b', 'Total', 'Disk Write Bytes'],
        'VMSS.WriteOperations':
            [
                vmss_provider, 'PerSecond',
                'Average', 'Disk Write Operations/Sec'
            ],
        'VMSS.ReadOperations':
            [
                vmss_provider, 'PerSecond',
                'Average', 'Disk Read Operations/Sec'
            ],
        'VMSSVM.PercentageCPU':
            [vmssvm_provider, '%', 'Average', 'Percentage CPU'],
        'VMSSVM.NetworkIn':
            [vmssvm_provider, 'b', 'Total', 'Network In'],
        'VMSSVM.NetworkOut':
            [vmssvm_provider, 'b', 'Total', 'Network Out'],
        'VMSSVM.BytesRead':
            [vmssvm_provider, 'b', 'Total', 'Disk Read Bytes'],
        'VMSSVM.BytesWritten':
            [vmssvm_provider, 'b', 'Total', 'Disk Write Bytes'],
        'VMSSVM.WriteOperations':
            [
                vmssvm_provider, 'PerSecond', 'Average',
                'Disk Write Operations/Sec'
            ],
        'VMSSVM.ReadOperations':
            [
                vmssvm_provider, 'PerSecond', 'Average',
                'Disk Read Operations/Sec'
            ],
        'MYSQL.cpu_percent':
            [mysql_provider, '%', 'Average', 'cpu_percent'],
        'MYSQL.compute_limit':
            [mysql_provider, '', 'Average', 'compute_limit'],
        'MYSQL.compute_consumption_percent':
            [mysql_provider, '%', 'Average', 'compute_consumption_percent'],
        'MYSQL.memory_percent':
            [mysql_provider, '%', 'Average', 'memory_percent'],
        'MYSQL.io_consumption_percent':
            [mysql_provider, '%', 'Average', 'io_consumption_percent'],
        'MYSQL.storage_percent':
            [mysql_provider, '%', 'Average', 'storage_percent'],
        'MYSQL.storage_used':
            [mysql_provider, 'b', 'Average', 'storage_used'],
        'MYSQL.storage_limit':
            [mysql_provider, 'b', 'Average', 'storage_limit'],
        'MYSQL.active_connections':
            [mysql_provider, '', 'Average', 'active_connections'],
        'MYSQL.connections_failed':
            [mysql_provider, '', 'Average', 'connections_failed'],
        'PGSQL.cpu_percent':
            [pgsql_provider, '%', 'Average', 'cpu_percent'],
        'PGSQL.compute_limit':
            [pgsql_provider, '', 'Average', 'compute_limit'],
        'PGSQL.compute_consumption_percent':
            [pgsql_provider, '%', 'Average', 'compute_consumption_percent'],
        'PGSQL.memory_percent':
            [pgsql_provider, '%', 'Average', 'memory_percent'],
        'PGSQL.io_consumption_percent':
            [pgsql_provider, '%', 'Average', 'io_consumption_percent'],
        'PGSQL.storage_percent':
            [pgsql_provider, '%', 'Average', 'storage_percent'],
        'PGSQL.storage_used':
            [pgsql_provider, 'b', 'Average', 'storage_used'],
        'PGSQL.storage_limit':
            [pgsql_provider, 'b', 'Average', 'storage_limit'],
        'PGSQL.active_connections':
            [pgsql_provider, '', 'Average', 'active_connections'],
        'PGSQL.connections_failed':
            [pgsql_provider, '', 'Average', 'connections_failed'],
        'IOT.d2c.telemetry.ingress.allProtocol':
            [iot_provider, '', 'Total', 'd2c.telemetry.ingress.allProtocol'],
        'IOT.d2c.telemetry.ingress.success':
            [iot_provider, '', 'Total', 'd2c.telemetry.ingress.success'],
        'IOT.c2d.commands.egress.complete.success':
            [
                iot_provider, '',
                'Total', 'c2d.commands.egress.complete.success'
            ],
        'IOT.c2d.commands.egress.abandon.success':
            [iot_provider, '', 'Total', 'c2d.commands.egress.abandon.success'],
        'IOT.c2d.commands.egress.reject.success':
            [iot_provider, '', 'Total', 'c2d.commands.egress.reject.success'],
        'IOT.devices.totalDevices':
            [iot_provider, '', 'Total', 'devices.totalDevices'],
        'IOT.devices.connectedDevices.allProtocol':
            [
                iot_provider, '',
                'Total', 'devices.connectedDevices.allProtocol'
            ],
        'IOT.d2c.telemetry.egress.success':
            [iot_provider, '', 'Total', 'd2c.telemetry.egress.success'],
        'IOT.d2c.telemetry.egress.dropped':
            [iot_provider, '', 'Total', 'd2c.telemetry.egress.dropped'],
        'IOT.d2c.telemetry.egress.orphaned':
            [iot_provider, '', 'Total', 'd2c.telemetry.egress.orphaned'],
        'IOT.d2c.telemetry.egress.invalid':
            [iot_provider, '', 'Total', 'd2c.telemetry.egress.invalid'],
        'IOT.d2c.telemetry.egress.fallback':
            [iot_provider, '', 'Total', 'd2c.telemetry.egress.fallback'],
        'IOT.d2c.endpoints.egress.eventHubs':
            [iot_provider, '', 'Total', 'd2c.endpoints.egress.eventHubs'],
        'IOT.d2c.endpoints.latency.eventHubs':
            [iot_provider, 'ms', 'Average', 'd2c.endpoints.latency.eventHubs'],
        'IOT.d2c.endpoints.egress.serviceBusQueues':
            [
                iot_provider, '', 'Total',
                'd2c.endpoints.egress.serviceBusQueues'
            ],
        'IOT.d2c.endpoints.latency.serviceBusQueues':
            [
                iot_provider,
                'ms',
                'Average',
                'd2c.endpoints.latency.serviceBusQueues'
            ],
        'IOT.d2c.endpoints.egress.serviceBusTopics':
            [
                iot_provider, '',
                'Total', 'd2c.endpoints.egress.serviceBusTopics'
            ],
        'IOT.d2c.endpoints.latency.serviceBusTopics':
            [
                iot_provider, 'ms', 'Average',
                'd2c.endpoints.latency.serviceBusTopics'
            ],
        'IOT.d2c.endpoints.egress.builtIn.events':
            [iot_provider, '', 'Total', 'd2c.endpoints.egress.builtIn.events'],
        'IOT.d2c.endpoints.latency.builtIn.events':
            [
                iot_provider, 'ms', 'Average',
                'd2c.endpoints.latency.builtIn.events'
            ],
        'IOT.d2c.twin.read.success':
            [iot_provider, '', 'Total', 'd2c.twin.read.success'],
        'IOT.d2c.twin.read.failure':
            [iot_provider, '', 'Total', 'd2c.twin.read.failure'],
        'IOT.d2c.twin.read.size':
            [iot_provider, 'b', 'Average', 'd2c.twin.read.size'],
        'IOT.d2c.twin.update.success':
            [iot_provider, '', 'Total', 'd2c.twin.update.success'],
        'IOT.d2c.twin.update.failure':
            [iot_provider, '', 'Total', 'd2c.twin.update.failure'],
        'IOT.d2c.twin.update.size':
            [iot_provider, 'b', 'Average', 'd2c.twin.update.size'],
        'IOT.c2d.methods.success':
            [iot_provider, '', 'Total', 'c2d.methods.success'],
        'IOT.c2d.methods.failure':
            [iot_provider, '', 'Total', 'c2d.methods.failure'],
        'IOT.c2d.methods.requestSize':
            [iot_provider, 'b', 'Average', 'c2d.methods.requestSize'],
        'IOT.c2d.methods.responseSize':
            [iot_provider, 'b', 'Average', 'c2d.methods.responseSize'],
        'IOT.c2d.twin.read.success':
            [iot_provider, '', 'Total', 'c2d.twin.read.success'],
        'IOT.c2d.twin.read.failure':
            [iot_provider, '', 'Total', 'c2d.twin.read.failure'],
        'IOT.c2d.twin.read.size':
            [iot_provider, 'b', 'Average', 'c2d.twin.read.size'],
        'IOT.c2d.twin.update.success':
            [iot_provider, '', 'Total', 'c2d.twin.update.success'],
        'IOT.c2d.twin.update.failure':
            [iot_provider, '', 'Total', 'c2d.twin.update.failure'],
        'IOT.c2d.twin.update.size':
            [iot_provider, 'b', 'Average', 'c2d.twin.update.size'],
        'IOT.twinQueries.success':
            [iot_provider, '', 'Total', 'twinQueries.success'],
        'IOT.twinQueries.failure':
            [iot_provider, '', 'Total', 'twinQueries.failure'],
        'IOT.twinQueries.resultSize':
            [iot_provider, 'b', 'Average', 'twinQueries.resultSize'],
        'IOT.jobs.createTwinUpdateJob.success':
            [iot_provider, '', 'Total', 'jobs.createTwinUpdateJob.success'],
        'IOT.jobs.createTwinUpdateJob.failure':
            [iot_provider, '', 'Total', 'jobs.createTwinUpdateJob.failure'],
        'IOT.jobs.createDirectMethodJob.success':
            [iot_provider, '', 'Total', 'jobs.createDirectMethodJob.success'],
        'IOT.jobs.createDirectMethodJob.failure':
            [iot_provider, '', 'Total', 'jobs.createDirectMethodJob.failure'],
        'IOT.jobs.listJobs.success':
            [iot_provider, '', 'Total', 'jobs.listJobs.success'],
        'IOT.jobs.listJobs.failure':
            [iot_provider, '', 'Total', 'jobs.listJobs.failure'],
        'IOT.jobs.cancelJob.success':
            [iot_provider, '', 'Total', 'jobs.cancelJob.success'],
        'IOT.jobs.cancelJob.failure':
            [iot_provider, '', 'Total', 'jobs.cancelJob.failure'],
        'IOT.jobs.queryJobs.success':
            [iot_provider, '', 'Total', 'jobs.queryJobs.success'],
        'IOT.jobs.queryJobs.failure':
            [iot_provider, '', 'Total', 'jobs.queryJobs.failure'],
        'IOT.jobs.completed':
            [iot_provider, '', 'Total', 'jobs.completed'],
        'IOT.jobs.failed':
            [iot_provider, '', 'Total', 'jobs.failed'],
        'IOT.d2c.telemetry.ingress.sendThrottle':
            [iot_provider, '', 'Total', 'd2c.telemetry.ingress.sendThrottle'],
        'IOT.dailyMessageQuotaUsed':
            [iot_provider, '', 'Average', 'dailyMessageQuotaUsed'],
        'SQL.cpu_percent':
            [sql_provider, '%', 'Average', 'cpu_percent'],
        'SQL.physical_data_read_percent':
            [sql_provider, '%', 'Average', 'physical_data_read_percent'],
        'SQL.log_write_percent':
            [sql_provider, '%', 'Average', 'log_write_percent'],
        'SQL.dtu_consumption_percent':
            [sql_provider, '%', 'Average', 'dtu_consumption_percent'],
        'SQL.storage':
            [sql_provider, 'b', 'Maximum', 'storage'],
        'SQL.connection_successful':
            [sql_provider, '', 'Total', 'connection_successful'],
        'SQL.connection_failed':
            [sql_provider, '', 'Total', 'connection_failed'],
        'SQL.blocked_by_firewall':
            [sql_provider, '', 'Total', 'blocked_by_firewall'],
        'SQL.deadlock':
            [sql_provider, '', 'Total', 'deadlock'],
        'SQL.storage_percent':
            [sql_provider, '%', 'Maximum', 'storage_percent'],
        'SQL.xtp_storage_percent':
            [sql_provider, '%', 'Average', 'xtp_storage_percent'],
        'SQL.workers_percent':
            [sql_provider, '%', 'Average', 'workers_percent'],
        'SQL.sessions_percent':
            [sql_provider, '%', 'Average', 'sessions_percent'],
        'SQL.dtu_limit':
            [sql_provider, '', 'Average', 'dtu_limit'],
        'SQL.dtu_used':
            [sql_provider, '', 'Average', 'dtu_used'],
        'SQL.dwu_limit':
            [sql_provider, '', 'Maximum', 'dwu_limit'],
        'SQL.dwu_consumption_percent':
            [sql_provider, '%', 'Maximum', 'dwu_consumption_percent'],
        'SQL.dwu_used':
            [sql_provider, '', 'Maximum', 'dwu_used'],
        'EP.cpu_percent':
            [ep_provider, '%', 'Average', 'cpu_percent'],
        'EP.physical_data_read_percent':
            [ep_provider, '%', 'Average', 'physical_data_read_percent'],
        'EP.log_write_percent':
            [ep_provider, '%', 'Average', 'log_write_percent'],
        'EP.dtu_consumption_percent':
            [ep_provider, '%', 'Average', 'dtu_consumption_percent'],
        'EP.storage_percent':
            [ep_provider, '%', 'Average', 'storage_percent'],
        'EP.workers_percent':
            [ep_provider, '%', 'Average', 'workers_percent'],
        'EP.sessions_percent':
            [ep_provider, '%', 'Average', 'sessions_percent'],
        'EP.eDTU_limit':
            [ep_provider, '', 'Average', 'eDTU_limit'],
        'EP.storage_limit':
            [ep_provider, 'b', 'Average', 'storage_limit'],
        'EP.eDTU_used':
            [ep_provider, '', 'Average', 'eDTU_used'],
        'EP.storage_used':
            [ep_provider, 'b', 'Average', 'storage_used'],
        'EP.xtp_storage_percent':
            [ep_provider, '%', 'Average', 'xtp_storage_percent'],
        'REDIS.connectedclients':
            [redis_provider, '', 'Maximum', 'connectedclients'],
        'REDIS.totalcommandsprocessed':
            [redis_provider, '', 'Total', 'totalcommandsprocessed'],
        'REDIS.cachehits':
            [redis_provider, '', 'Total', 'cachehits'],
        'REDIS.cachemisses':
            [redis_provider, '', 'Total', 'cachemisses'],
        'REDIS.getcommands':
            [redis_provider, '', 'Total', 'getcommands'],
        'REDIS.setcommands':
            [redis_provider, '', 'Total', 'setcommands'],
        'REDIS.evictedkeys':
            [redis_provider, '', 'Total', 'evictedkeys'],
        'REDIS.totalkeys':
            [redis_provider, '', 'Maximum', 'totalkeys'],
        'REDIS.expiredkeys':
            [redis_provider, '', 'Total', 'expiredkeys'],
        'REDIS.usedmemory':
            [redis_provider, 'b', 'Maximum', 'usedmemory'],
        'REDIS.usedmemoryRss':
            [redis_provider, 'b', 'Maximum', 'usedmemoryRss'],
        'REDIS.serverLoad':
            [redis_provider, '%', 'Maximum', 'serverLoad'],
        'REDIS.cacheWrite':
            [redis_provider, 'BPerSecond', 'Maximum', 'cacheWrite'],
        'REDIS.cacheRead':
            [redis_provider, 'BPerSecond', 'Maximum', 'cacheRead'],
        'REDIS.percentProcessorTime':
            [redis_provider, '%', 'Maximum', 'percentProcessorTime'],
        'generic':
            [args.provider, args.uom, args.aggregation, args.metric]}


def get_metric(args_list):
    provider = args_list[0]
    uom = args_list[1]
    aggregation = args_list[2]
    mode = args_list[3]
    metrics_data = setup_get_request(provider, aggregation, mode)
    metric_value = get_metric_value(aggregation, metrics_data)
    return metric_value, mode, uom


def setup_get_request(provider, aggregation, mode):
    """Setup the credentials to access the azure service"""
    credentials = ServicePrincipalCredentials(
        client_id=args.client,
        secret=args.secret,
        tenant=args.tenant
    )

    client = MonitorClient(
        credentials,
        args.subscription
    )

    resource_client = ResourceManagementClient(
        credentials,
        args.subscription
    )

    resource_client.providers.register('Microsoft.Insights')

    # Creating the resource ID of the system also acts as an endpoint
    resource_id = (
        'subscriptions/{0}/'
        'resourceGroups/{1}/'
        'providers/{2}/{3}'
    ).format(args.subscription, args.resource, provider, args.hostaddress)

    if args.debug:
        sys.stderr.write("Available Resource Groups:\n")
        for item in resource_client.resource_groups.list():
            print_item(item)

        sys.stderr.write("Available VMs:\n");
        compute_client = ComputeManagementClient(credentials, args.subscription)
        for vm in compute_client.virtual_machines.list_all():
            sys.stderr.write("\t{}\n".format(vm.name))

        sys.stderr.write( "Available Metric Definitions\n" )
        for metric in client.metric_definitions.list(resource_id):
            sys.stderr.write("\t{}: id={}, unit={}\n".format(
                metric.name.localized_value,
                metric.name.value,
                metric.unit
            ))
# listing available metrics is not useful as without a filter it only shows 
# the first available and not all (as per the docs)
#        print "Available Metrics"
#        for metric in client.metrics.list(resource_id):
#            # azure.monitor.models.MetricDefinition
#            print("\t{}: id={}, unit={}".format(
#                metric.name.localized_value,
#                metric.name.value,
#                metric.unit
#            ))

    end_time = datetime.datetime.utcnow()
    start_time = update_time_state(end_time)
    period = end_time - start_time

    # Setup the call for the data we want
    filter = " and ".join([
        "name.value eq '{}'".format(mode),
        "aggregationType eq '{}'".format(aggregation),
        "startTime eq {}".format(start_time.strftime('%Y-%m-%dT%H:%M:%SZ')),
        "endTime eq {}".format(end_time.strftime('%Y-%m-%dT%H:%M:%SZ')),
        "timeGrain eq duration'PT{}M'".format(int(period.total_seconds() / MINUTE_IN_SECONDS))
    ])


    # if we output the info here then we need to make another call to get the data
    # else the iterator uses up all the info and returns nothing to the caller
    if args.debug:
        metrics_data = client.metrics.list(
            resource_id,
            filter=filter
        )
        sys.stderr.write("Metric filter: "+filter+"\n")
        sys.stderr.write("Metric data returned:\n")
        for metric in metrics_data:
            for data in metric.data:
                sys.stderr.write("\t{}: {}\n".format(data.time_stamp, data.total))

    metrics_data = client.metrics.list(
        resource_id,
        filter=filter
    )

    return metrics_data

def print_item(group):
    """Print a ResourceGroup instance."""
    sys.stderr.write("\tName: {}\n".format(group.name))
    sys.stderr.write("\tId: {}\n".format(group.id))
    sys.stderr.write("\tLocation: {}\n".format(group.location))
    sys.stderr.write("\tTags: {}\n".format(group.tags))
    print_properties(group.properties)

def print_properties(props):
    """Print a ResourceGroup properties instance."""
    if props and props.provisioning_state:
        sys.stderr.write("\tProperties:\n")
        sys.stderr.write("\t\tProvisioning State: {}\n".format(props.provisioning_state))
    sys.stderr.write("\n")

def get_metric_value(aggregation, metrics_data):
    """Get the latest datapoint
    and return the most recent metric"""
    try:
        item = metrics_data.next()
        data = item.data[0]
    except ErrorResponseException:
        raise PluginError(
            "No metric data was found. " +
            "This may be due to the check being run too " +
            "quickly after the last run " +
            "also check resource group or resource."
        )

    if aggregation == 'Average':
        metric_result = data.average
    elif aggregation == 'Total':
        metric_result = data.total
    elif aggregation == 'Maximum':
        metric_result = data.maximum
    elif aggregation == 'Minimum':
        metric_result = data.minimum

    if metric_result is None:
        raise PluginError(
            "No metric data was found. " +
            "This may be due to the check being run too " +
            "quickly after the last run."
        )
    else:
        return metric_result


def update_time_state(time_now):
    """Get the last run time from the file and write the new time"""
    path = check_file_path()
    if args.mode == 'generic':
        state_name = '{0}_{1}'.format(args.metric, args.hostaddress)
    else:
        state_name = '{0}_{1}'.format(args.mode, args.hostaddress)

    with Cookie(path) as cookie:
        last_run_time_cookie = cookie.open()
        last_run_time = last_run_time_cookie.get(state_name, 0)
        cookie[state_name] = time_now.strftime('%Y-%m-%dT%H:%M:%SZ')

    try:
       last_run = datetime.datetime.strptime(last_run_time, '%Y-%m-%dT%H:%M:%SZ')
    except:
       last_run = time_now - datetime.timedelta(minutes=5)

    # last last run < 2 minutes ago, set to 2 mins ago
    # also fix for swapping to UTC from previous incorrect version
    if (time_now - last_run).total_seconds() < 120 or last_run > time_now:
       last_run = time_now - datetime.timedelta(minutes=2)

    return last_run


def check_file_path():
    """Check we have access to the file location, defaults to /tmp"""
    path = '/usr/local/nagios/tmp/azure_time_states.tmp'

    if not os.access(path, os.W_OK + os.R_OK):
        path = '/tmp/azure_time_state_.tmp'

    return path

@nagiosplugin.guarded
def main():
    global args
    args = get_args()
    check = nagiosplugin.Check(
        Metric(),
        nagiosplugin.ScalarContext(args.mode, args.warning, args.critical))
    check.main()


if __name__ == '__main__':
    main()
