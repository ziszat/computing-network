from flask import Flask, jsonify, request
import requests
import numpy as np

app = Flask(__name__)

MASTER_IP = {
    "hosta": "localhost",
    "hostb": "localhost",
}

MASTER_PORT = {
    "hosta": 30091,
    "hostb": 30092,
}

masters = ["hosta", "hostb"]


def query_prometheus(prometheus_ip, port, query):
    url = f"http://{prometheus_ip}:{port}/api/v1/query"
    response = requests.get(url, params={"query": query})
    if response.status_code == 200:
        return response.json().get("data", {}).get("result", [])
    else:
        print(f"Error querying Prometheus: {response.status_code}")
        return []


def get_free_resources(prometheus_ip, port):
    # Query for CPU, Memory, and Storage
    cpu_query = (
        'avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100'
    )
    mem_query = "node_memory_MemAvailable_bytes"
    storage_query = 'node_filesystem_avail_bytes{mountpoint="/"}'

    cpu_usage = query_prometheus(prometheus_ip, port, cpu_query)
    memory_available = query_prometheus(prometheus_ip, port, mem_query)
    storage_available = query_prometheus(prometheus_ip, port, storage_query)

    return {
        "cpu_usage": cpu_usage,
        "memory_available": memory_available,
        "storage_available": storage_available,
    }


def get_resource(prometheus_ips, ports):
    resources = []
    for i in range(len(ports)):
        resources.append(get_free_resources(prometheus_ips[i], ports[i]))
    return resources


# 提取并聚合数据
def aggregate_resource_data(resources):
    aggregated_data = []
    for res in resources:
        # 取每个集群中节点的 CPU、内存、存储的平均值
        avg_cpu = np.mean([float(node["value"][1]) for node in res["cpu_usage"]])
        avg_memory = np.mean(
            [float(node["value"][1]) for node in res["memory_available"]]
        )
        avg_storage = np.mean(
            [float(node["value"][1]) for node in res["storage_available"]]
        )

        # 将每个集群的数据聚合为一行，表示为 [cpu, memory, storage]
        aggregated_data.append([avg_cpu, avg_memory, avg_storage])
    return np.array(aggregated_data)


# 归一化处理
def normalize(data):
    min_vals = data.min(axis=0)
    max_vals = data.max(axis=0)
    norm_data = (data - min_vals) / (max_vals - min_vals)
    return norm_data


# 计算熵
def calculate_entropy(norm_data):
    epsilon = 1e-10  # 防止 log(0)
    p = norm_data / norm_data.sum(axis=0)
    entropy = -np.sum(p * np.log(p + epsilon), axis=0) / np.log(len(norm_data))
    return entropy


# 计算权重
def calculate_weights(entropy):
    return (1 - entropy) / (len(entropy) - np.sum(entropy))


# 计算综合评分
def calculate_scores(norm_data, weights):
    p = norm_data / norm_data.sum(axis=0)
    return np.dot(p, weights)


# 选择最优集群
def select_best_cluster(scores):
    return masters[np.argmax(scores)]  # 返回最佳集群


# 调度主函数
def schedule():
    prometheus_ips = []
    ports = []
    for master in masters:
        ports.append(MASTER_PORT[master])
        prometheus_ips.append(MASTER_IP[master])

    resources = get_resource(prometheus_ips, ports)
    aggregated_resources = aggregate_resource_data(resources)
    norm_resources = normalize(aggregated_resources)
    entropy = calculate_entropy(norm_resources)
    weights = calculate_weights(entropy)
    scores = calculate_scores(norm_resources, weights)
    scores = scores * 100
    best_cluster = select_best_cluster(scores)

    return aggregated_resources.tolist(), best_cluster, scores


# HTTP GET 请求处理
@app.route("/schedule", methods=["GET"])
def get_schedule():
    try:
        aggregated, best_cluster, scores = schedule()
        return jsonify(
            {
                "average_resource": aggregated,
                "best_cluster": best_cluster,
                "scores": scores.tolist(),  # 将 numpy 数组转换为列表返回
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5080)

# prometheus_ips = []
# ports = []
# for master in masters:
#     ports.append(MASTER_PORT[master])
#     prometheus_ips.append(MASTER_IP[master])

# resources = get_resource(prometheus_ips, ports)

# # 对resources进行数据聚合处理
# aggregated_resources = aggregate_resource_data(resources)
# print("Aggregated Data (CPU, Memory, Storage):")
# print(aggregated_resources)

# # 归一化处理
# norm_resources = normalize(aggregated_resources)
# print("\nNormalized Data:")
# print(norm_resources)

# # 计算熵
# entropy = calculate_entropy(norm_resources)
# print("\nEntropy:")
# print(entropy)

# # 计算权重
# weights = calculate_weights(entropy)
# print("\nWeights:")
# print(weights)

# # 计算每个集群的综合评分
# scores = calculate_scores(norm_resources, weights)
# print("\nScores:")
# print(scores)

# # 选择最优集群
# best_cluster = select_best_cluster(scores)
# print(f"\nBest Cluster Master: {best_cluster}")
