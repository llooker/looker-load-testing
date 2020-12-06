import googleapiclient.discovery
from google.cloud import container_v1
from jinja2 import Template
from pathlib import Path


def get_gke_client(credentials=None):
    """Creates and returns a gke client. Credentials only needed
    if the Auth environment variable is not set.
    """

    client = container_v1.ClusterManagerClient(credentials=credentials)

    return client


def get_compute_client(credentials=None):
    """Creates and returns a compute client. Credentials only needed if the Auth
    environment variable is not set.
    """

    client = googleapiclient.discovery.build("compute", "v1", credentials=credentials)

    return client


def create_global_ip(name, project, client):
    """Creates a global ip address suitable for use with GKE ingress controller.
    Returns a job ID that can be used to track the status of the address creation.
    """

    # https://cloud.google.com/compute/docs/reference/rest/v1/globalAddresses/insert
    body = {"name": name}
    global_address = client.globalAddresses()
    request = global_address.insert(project=project, body=body)
    response = request.execute()

    return response["name"]


def delete_global_ip(name, project, client):
    """Deletes the specified global ip address. Returns a job ID that can be used to
    track the status of the deletion request.
    """

    # https://cloud.google.com/compute/docs/reference/rest/v1/globalAddresses/delete
    global_address = client.globalAddresses()
    request = global_address.delete(project=project, address=name)
    response = request.execute()

    return response["name"]


def compute_task_status(task_name, project, client):
    """Accepts a compute operation name and requests the status of the operation.
    Returns a string of the job status. Possible values are 'PENDING', 'RUNNING'
    and 'DONE'
    """

    # https://cloud.google.com/compute/docs/reference/rest/v1/globalOperations/get
    global_operations = client.globalOperations()
    request = global_operations.get(project=project, operation=task_name)
    response = request.execute()

    return response["status"]


def fetch_ip_address(name, project, client):
    """Fetches the actual IP address once the global address creation has successfully
    completed. Accepts the name provided in the initial request and returns a string of
    the address.
    """

    global_address = client.globalAddresses()
    request = global_address.get(project=project, address=name)
    response = request.execute()

    return response["address"]


def setup_gke_cluster(name, project, zone, node_count, machine_type, client):
    """Creates a GKE compute cluster. Returns a job ID that can be used to track
    the status of the cluster creation.
    """

    parent = f"projects/{project}/locations/{zone}"

    # https://googleapis.dev/python/container/latest/container_v1/types.html
    # https://cloud.google.com/kubernetes-engine/docs/reference/rest/v1/projects.locations.clusters#Cluster
    cluster = {
        "name": name,
        "release_channel": {
            "channel": "REGULAR"
        },
        "node_pools": [
            {
                "name": "load-test-pool",
                "initial_node_count": node_count,
                "config": {
                    "machine_type": machine_type,
                    "oauth_scopes": [
                        "https://www.googleapis.com/auth/cloud-platform"
                    ]
                }
            }
        ]
    }

    request = container_v1.types.CreateClusterRequest(parent=parent, cluster=cluster)
    task = client.create_cluster(request=request)

    return task.name


def delete_gke_cluster(name, project, zone, client):
    """Deletes a GKE cluster. Returns a job ID that can be used to track the
    status of the cluster deletion.
    """

    cluster_name = f"projects/{project}/locations/{zone}/clusters/{name}"
    request = container_v1.types.DeleteClusterRequest(name=cluster_name)
    task = client.delete_cluster(request=request)

    return task.name


def gke_task_status(name, project, zone, client):
    """Returns details on the status of a specified GKE job. This can be used to
    poll for the results of a job. The returned object contains two useful elements:
    1. `status.name` which returns a string of the current status. When this returns
        'DONE' then the job has completed.
    2. `detail` which returns a string with some extra context.
    """

    task_name = f"projects/{project}/locations/{zone}/operations/{name}"
    request = container_v1.types.GetOperationRequest(name=task_name)
    task_status = client.get_operation(request=request)

    return task_status


def setup_cluster_auth_file(name, project, zone, client):
    """Creates a kubeconfig yaml file suitable for use to authorize calls to the
    kubernetes API using GCP service account credentials. This file is assumed to
    be in place in the `rendered` directory before any kubernetes deployments are
    done. While this file sets up the use of GCP service accounts the user will still
    need to set the GOOGLE_APPLICATION_CREDENTIALS environment variable. Returns a
    string with the absolute path to the created credentials file.
    """

    cluster_name = f"projects/{project}/locations/{zone}/clusters/{name}"
    request = container_v1.types.GetClusterRequest(name=cluster_name)
    cluster = client.get_cluster(request=request)

    # We'll need both the CA Certificate and the correct endpoint (IP address)
    ca_cert = cluster.master_auth.cluster_ca_certificate
    endpoint = cluster.endpoint

    # This dict is used to easily render the kubeconfig template with jinja
    vals = {
        "name": name,
        "project": project,
        "zone": zone,
        "ca_cert": ca_cert,
        "endpoint": endpoint
    }

    script_path = Path(__file__).parent
    kubeconfig_template = script_path.joinpath("templates", "kubeconfig.yaml")
    kubeconfig_rendered = script_path.joinpath("rendered", "kubeconfig.yaml")
    template = kubeconfig_template.read_text()
    # Render the template with jinja
    rendered = Template(template).render(**vals)

    with open(kubeconfig_rendered, "w") as f:
        f.write(rendered)

    return kubeconfig_rendered.resolve()
