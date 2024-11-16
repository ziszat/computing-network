import json
import requests
import re
import yaml
from collections import defaultdict


def assign_target(command, dst):
    if dst == "a":
        command = command + " --kubeconfig=config-a"
    elif dst == "b":
        command = command + " --kubeconfig=config-b"
    else:
        command = command + " --kubeconfig=config-a"
    return command


def schedule_target(command):
    try:
        dst = get_schedule_result()
        if dst["best_cluster"] == "hosta":
            command = command + " --kubeconfig=config-a"
        elif dst["best_cluster"] == "hostb":
            command = command + " --kubeconfig=config-b"
        else:
            command = command + " --kubeconfig=config-a"
        return command
    except Exception as e:
        return e


def get_schedule_result():
    try:
        # 目标调度服务的URL
        url = "http://172.20.2.14:5080/schedule"

        # 发送GET请求
        response = requests.get(url)

        # 检查响应状态码
        if response.status_code == 200:
            # 将响应数据转换为JSON格式
            data = response.json()
            resources = data["average_resource"]
            for resource in resources:
                resource[1] = resource[1] / 1024 / 1024
                resource[2] = resource[2] / 1024 / 1024
            return data
        else:
            print(f"Failed to get schedule result. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error occurred: {e}")


def parse_sr_policies(data):
    # 正则表达式匹配各个部分
    bsid_pattern = r"BSID: ([\w:]+)"
    behavior_pattern = r"Behavior: ([\w\s]+)"
    type_pattern = r"Type: (\w+)"
    fib_table_pattern = r"FIB table: (\d+)"
    segment_list_pattern = (
        r"Segment Lists:\s+(.*?)weight: \d+"  # 匹配 segment list 中的内容
    )

    # 切分数据
    policies = data.split("-----------\r\n")
    parsed_policies = []

    for policy in policies:
        if not policy.strip():
            continue

        # 提取各个字段
        bsid = re.search(bsid_pattern, policy)
        behavior = re.search(behavior_pattern, policy)
        policy_type = re.search(type_pattern, policy)
        fib_table = re.search(fib_table_pattern, policy)
        segment_lists = re.search(segment_list_pattern, policy)

        clean_behavior = behavior.group(1).split("\r\n")[0] if behavior else None
        clean_slist = segment_lists.group(1).split("- < ")[1].split(", \b\b")[0]
        # 构建 JSON 格式的数据
        parsed_policy = {
            "BSID": bsid.group(1) if bsid else None,
            "Behavior": clean_behavior,
            "Type": policy_type.group(1) if policy_type else None,
            "FIB_table": int(fib_table.group(1)) if fib_table else None,
            "Segment_Lists": clean_slist,  # 原样存放
        }

        parsed_policies.append(parsed_policy)

    return parsed_policies


def parse_pod_info_to_json(pod_info):
    lines = pod_info.splitlines()
    headers = lines[0].split()  # 提取表头作为键
    pods = []
    index = -1
    if "LABELS" in headers:
        index = headers.index("LABELS")
        headers[index] = "UUID"
    if "INTERNAL-IP" in headers:
        headers[headers.index("INTERNAL-IP")] = "ADDRESS"

    for line in lines[1:]:
        values = line.split(maxsplit=len(headers) - 1)  # 分割每一行的值
        if index != -1:
            values[index] = values[index].split(",")[-1]
        pod_dict = dict(zip(headers, values))  # 将值与键匹配生成字典
        pods.append(pod_dict)

    return pods


def process_steer_data(raw_data):
    # 分割数据为行
    lines = raw_data.split("\r\n")

    # 找到从哪里开始有数据（跳过头部的标题部分）
    start_index = 2

    # 存储处理后的政策列表
    policies = []

    # 处理每一行数据
    for line in lines[start_index:]:
        # 跳过空行
        if not line.strip():
            continue

        # 按制表符分割每一行数据
        columns = line.split("\t")

        # 确保行数据符合预期
        if len(columns) == 2:
            traffic, bsid = columns
            policy = {"Traffic": traffic.strip().split("L3 ")[1], "BSID": bsid.strip()}
            policies.append(policy)

    return policies


def extract_labels(yaml_content):
    # 将YAML内容加载为字典
    data = yaml.safe_load(yaml_content)

    # 提取namespace和app label
    namespace = data.get("metadata", {}).get("namespace", "N/A")
    app_label = (
        data.get("spec", {})
        .get("selector", {})
        .get("matchLabels", {})
        .get("app", "N/A")
    )

    # 返回JSON响应
    result = {"namespace": namespace, "app_label": app_label}

    return result


def extract_pod_logs(log_data: str, pod_name: str):
    # 将日志按行分割
    log_lines = log_data.splitlines()

    # 提取与指定Pod相关的日志行
    pod_logs = [line for line in log_lines if pod_name in line]

    plugin_score_regex = re.compile(
        r'pod="(?P<pod>[\w-]+)" plugin="(?P<plugin>[\w]+)" node="(?P<node>[\w-]+)" score=(?P<score>\d+)'
    )
    final_score_regex = re.compile(
        r'pod="(?P<pod>[\w-]+)" node="(?P<node>[\w-]+)" score=(?P<final_score>\d+)'
    )

    result = {
        "plugin_scores": defaultdict(lambda: defaultdict(int)),
        "final_scores": defaultdict(int),
    }

    for line in pod_logs:
        # 匹配插件打分信息
        plugin_score_match = plugin_score_regex.search(line)
        if plugin_score_match:
            data = plugin_score_match.groupdict()
            result["plugin_scores"][data["plugin"]][data["node"]] = int(data["score"])
            continue

        # 匹配最终综合分数
        final_score_match = final_score_regex.search(line)
        if final_score_match:
            data = final_score_match.groupdict()
            result["final_scores"][data["node"]] = int(data["final_score"])
            continue

    result["plugin_scores"] = {
        plugin: dict(nodes) for plugin, nodes in result["plugin_scores"].items()
    }
    result["final_scores"] = {dict(nodes) for nodes in result["final_scores"].items()}
    return result
