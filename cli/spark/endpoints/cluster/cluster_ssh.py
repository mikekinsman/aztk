import argparse
import typing
from cli import log
from cli import utils, config
from cli.config import SshConfig
import aztk
import azure.batch.models.batch_error as batch_error
from aztk.models import ClusterConfiguration


def setup_parser(parser: argparse.ArgumentParser):
    parser.add_argument('--id', dest="cluster_id",
                        help='The unique id of your spark cluster')
    parser.add_argument('--webui',
                        help='Local port to port spark\'s master UI to')
    parser.add_argument('--jobui',
                        help='Local port to port spark\'s job UI to')
    parser.add_argument('--jobhistoryui',
                        help='Local port to port spark\'s job history UI to')
    parser.add_argument('--jupyter',
                        help='Local port to port jupyter to')
    parser.add_argument('--namenodeui',
                        help='Local port to port HDFS NameNode UI to')
    parser.add_argument('--rstudioserver',
                        help='Local port to port rstudio server to')
    parser.add_argument('-u', '--username',
                        help='Username to spark cluster')
    parser.add_argument('--host', dest="host",
                        action='store_true',
                        help='Connect to the host of the Spark container')
    parser.add_argument('--no-connect', dest="connect",
                        action='store_false',
                        help='Do not create the ssh session. Only print out \
                        the command to run.')

    parser.set_defaults(connect=True)


http_prefix = 'http://localhost:'


def execute(args: typing.NamedTuple):
    spark_client = aztk.spark.Client(config.load_aztk_screts())
    cluster = spark_client.get_cluster(args.cluster_id)
    ssh_conf = SshConfig()

    ssh_conf.merge(
        cluster_id=args.cluster_id,
        username=args.username,
        job_ui_port=args.jobui,
        job_history_ui_port=args.jobhistoryui,
        web_ui_port=args.webui,
        jupyter_port=args.jupyter,
        name_node_ui_port=args.namenodeui,
        rstudio_server_port=args.rstudioserver,
        host=args.host,
        connect=args.connect
    )

    log.info("-------------------------------------------")
    log.info("spark cluster id:    %s", ssh_conf.cluster_id)
    log.info("open webui:          %s%s", http_prefix, ssh_conf.web_ui_port)
    log.info("open jobui:          %s%s", http_prefix, ssh_conf.job_ui_port)
    log.info("open jobhistoryui:   %s%s", http_prefix,
             ssh_conf.job_history_ui_port)
    log.info("open namenodeui:     %s%s",
             http_prefix, ssh_conf.name_node_ui_port)
    print_plugin_ports(cluster)
    log.info("ssh username:        %s", ssh_conf.username)
    log.info("connect:             %s", ssh_conf.connect)
    log.info("-------------------------------------------")

    # get ssh command
    try:
        ssh_cmd = utils.ssh_in_master(
            client=spark_client,
            cluster_id=ssh_conf.cluster_id,
            webui=ssh_conf.web_ui_port,
            jobui=ssh_conf.job_ui_port,
            jobhistoryui=ssh_conf.job_history_ui_port,
            namenodeui=ssh_conf.name_node_ui_port,
            username=ssh_conf.username,
            host=ssh_conf.host,
            connect=ssh_conf.connect)

        if not ssh_conf.connect:
            log.info("")
            log.info(
                "Use the following command to connect to your spark head node:")
            log.info("\t%s", ssh_cmd)

    except batch_error.BatchErrorException as e:
        if e.error.code == "PoolNotFound":
            raise aztk.error.AztkError(
                "The cluster you are trying to connect to does not exist.")
        else:
            raise


def print_plugin_ports(cluster: ClusterConfiguration):

    if cluster.configuration and cluster.configuration.plugins:
        plugins = cluster.configuration.plugins
        has_ports = False
        for plugin in plugins:
            for port in plugin.definition.ports:
                has_ports = True
                break

        if has_ports > 0:
            log.info("Plugins:")
            for plugin in plugins:
                for port in plugin.definition.ports:
                    log.info("  - open %s %s: %s%s", plugin.name, port.name or '',
                             http_prefix, port.local)
