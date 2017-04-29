import sys
import time
import requests
import kubernetes
import eventlet
from eventlet import greenthread
from settings import settings
import copy
import etcd
import json
import os

from httplib2 import Http

from log import LOG

kube_client = kubernetes.Api(base_url=settings.K8S_API_SERVER)
etcd_client = etcd.Client(host=settings.ETCD_SERVER, port=settings.ETCD_PORT)

TIMEOUT = 10.0

def get_app_json(app_name):
    response = requests.get('{}/api/v1/applications/{}'.format(
                                settings.PAAS_API_SERVER, app_name),
                            timeout=TIMEOUT)
    app_json = response.json()
    if app_json['kind'] == 'Application':
        return app_json
    else:
        return None

def get_app_controllers():
    response = requests.get('{}/api/v1/application_controllers'.format(
                                settings.PAAS_API_SERVER),
                            timeout=TIMEOUT)
    controllers = response.json()
    return controllers['items']

def check_app(app_json, app_controller):
    for component in app_json['components']:
        if not check_component(app_json['name'], component, app_controller):
            return

def monitor_app_status():
    fname = 'monitory_app_status'
    while True:
        LOG.info('{}: start'.format(fname))
        try:
            controllers = get_app_controllers()
            for controller in controllers:
                LOG.info('check app controller <{}>'.format(controller['name']))
                app_json = get_app_json(controller['name'])
                if app_json:
                    check_app(app_json, controller)
        except Exception, e:
            LOG.error('{}: {}'.format(fname, e))

        LOG.info('{}: done'.format(fname))
        greenthread.sleep(settings.APP_MONITOR_INTERVAL)

def push_pod_status(namespace, pod_name, pod_container):
    ''' pod_name = namespace/pod_name '''
    key = '/paas/applications/{}/pods/{}'.format(namespace, pod_name) 
    pod_container['timestamp'] = int(time.time())
    value = json.dumps(pod_container)
    etcd_client.write(key, value)

def push_node_status(type, node_name, node_json, version=None):
    '''
    @param type: masters/nodes
    '''
    key = '/paas/{}/{}'.format(type, node_name)
    if version:
        key = '/paas/{}/{}/{}'.format(type, version, node_name)
    node_json['timestamp'] = int(time.time())
    node_json['name'] = node_name
    value = json.dumps(node_json)
    etcd_client.write(key, value)

def do_etcd_gc():
    fname = 'do_etcd_gc'
    while True:
        LOG.info('{}: start'.format(fname))
        key = '/paas/applications'
        try:
            value = etcd_client.read(key)
        except etcd.EtcdKeyNotFound as e:
            greenthread.sleep(60)
            continue

        namespace_list = []
        for sub_item in value._children:
            namespace_list.append(os.path.basename(sub_item['key']))

        for namespace in namespace_list:
            pod_names = {}
            pod_list = kube_client.GetPods(namespace).Items
            for pod in pod_list:
                pod_names['/paas/applications/{}/pods/{}'.format(namespace, pod.Name)] = None

            key = '/paas/applications/{}/pods'.format(namespace)
            try:
                value = etcd_client.read(key)
                for sub_item in value._children:
                    if sub_item['key'] not in pod_names:
                        etcd_client.delete(sub_item['key'])
                        LOG.info('{} is delete from ETCD'.format(sub_item['key']))
            except Exception, e:
                LOG.error('{}: {}'.format(fname, e))

        LOG.info('{}: done'.format(fname))
        greenthread.sleep(60)


def _collect_node_info(node, session):
    url = 'http://{}:12305/api/v1.0/machine'.format(node.name)
    try:
        res = session.get(url, timeout=TIMEOUT)
        if res.status_code != 200:
            LOG.warning('Can not connect to agent <{}>'.format(node.name))
            return
    except Exception, e:
        LOG.warning('Can not connect to agent <{}>'.format(e.message))
        return
    node_json = res.json()
    node_json['mem_request_used'] = node.mem_request_used
    push_node_status('nodes', node.name, node_json)


def _post_dict(url, dictionary):
    http = Http(timeout=TIMEOUT)
    resp, content = http.request(
        uri=url,
        method='POST',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=json.dumps(dictionary)
    )
    return resp, content


def _read_svc_tmpl(path, ip):
    try:
        with open(path) as fp:
            data = json.load(fp)
            for k1, v1 in data.items():
                for k2, v2 in v1.items():
                    if type(v2) == unicode:
                        v1[k2] = v2.encode('utf-8').replace('NODE_IP', ip)
            return data
    except Exception as e:
        LOG.error("read file failed: %s" % path)


def _collect_node_info_v1_1(node):
    svc = _read_svc_tmpl('svc_node.json', node.name)
    url = 'http://{}:12305/api/v1.1/machine'.format(node.name)
    try:
        resp, content = _post_dict(url, svc)
        LOG.debug(resp, content)
        if resp.status != 200:
            LOG.warning('Post failed <{}>'.format(node.name))
            return
    except Exception as e:
        LOG.warning('Post failed <{}>'.format(e.message))
        LOG.exception(e)
        return
    node_json = json.loads(content)
    node_json['mem_request_used'] = node.mem_request_used
    push_node_status('nodes', node.name, node_json, version=1.1)


def _collect_master_info_v1_1(master_ip):
    svc = _read_svc_tmpl('svc_master.json', master_ip)
    url = 'http://{}:12305/api/v1.1/machine'.format(master_ip)
    try:
        resp, content = _post_dict(url, svc)
        if resp.status != 200:
            LOG.warning('Post failed <{}>'.format(master_ip))
            return
    except Exception, e:
        LOG.warning('Post failed <{}>'.format(e.message))
        return
    node_json = json.loads(content)
    push_node_status('masters', master_ip, node_json, version=1.1)


def collect_cluster_resource_usage():
    fname = 'collect_cluster_resource_usage'
    while True:
        try:
            LOG.info('{}: start'.format(fname))
            # 1. sync master
            master_ip = settings.K8S_API_SERVER.split('/')[2].split(':')[0]
            _collect_master_info_v1_1(master_ip)
            # 2. sync nodes
            pod_list = kube_client.GetPods().Items
            assert pod_list is not None
            node_list = kube_client.GetNodes()
            assert node_list is not None
            for node in node_list:
                session = requests.Session()
                _collect_node_info(node, session)
                _collect_node_info_v1_1(node)

                if not node.is_ready():
                    continue
                # get pod container status
                url = 'http://{}:12305/api/v1.0/docker'.format(node.name)
                try:
                    res = session.get(url, timeout=TIMEOUT)
                    if res.status_code != 200:
                        LOG.warning('Can not connect to agent <{}>'.format(node.name))
                        continue
                except Exception, e:
                    LOG.warning('Can not connect to agent <{}>'.format(e.message))
                    continue
                pod_containers = res.json()
                assert pod_containers is not None
                for key, pod_container in pod_containers.items():
                    found = False
                    for pod in pod_list:
                        try:
                            if pod.Status.ContainerStatuses[0]['containerID'][9:] == key:
                                found = True
                                break
                        except:
                            pass

                    if not found:
                        continue

                    push_pod_status(pod_container['namespace'], pod_container['pod_name'], pod_container)

            LOG.info("{}: done".format(fname))
        except Exception, e:
            LOG.error('{}: {}'.format(fname, e))

        greenthread.sleep(settings.RESOURCE_COLLECTOR_INTERVAL)

def check_component(app_name, component_json, app_controller):
    fname = 'check_component'
    '''
    If current component's status is OK, return True.
    If current component's status is not OK, return False
    '''
    if component_json['replicas'] != len(component_json['pods']):
        return False

    if component_json['replicas'] == 1:
        return True
    
    pod_need_killed = None
    is_component_ready = True
    for pod in component_json['pods']:
        if not pod['is_ready'] or not pod['is_running']:
            is_component_ready = False
            break
        try:
            if float(pod['mem_usage']) / float(pod['max_mem_limit']) * 100 >= app_controller['memory_threshold']:
                pod_need_killed = pod
        except Exception, e:
            LOG.error('{}: {}'.format(fname, e))

    if is_component_ready and pod_need_killed:
        # kill the pod
        kube_client.DeletePods(pod_need_killed['name'], namespace=app_name)
        LOG.info('Pod <{}> is deleted because its memory usage {}/{} is over {}'.format(pod_need_killed['name'], pod_need_killed['mem_usage'], pod_need_killed['max_mem_limit'], app_controller['memory_threshold']))
        return False
    elif is_component_ready:
        return True
    else:
        return False

def main(argv):
    eventlet.spawn(monitor_app_status)
    eventlet.spawn(collect_cluster_resource_usage)
    eventlet.spawn(do_etcd_gc)
    while True:
        eventlet.sleep(3600)

if __name__ == '__main__':
    main(sys.argv[1:])
    #print _read_svc_tmpl('svc_node.json', "1.1.1.1")

