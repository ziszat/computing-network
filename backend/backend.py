import json
from flask import Flask, request, jsonify
import subprocess
import requests
import re
from flask_cors import CORS
from utils import (
    assign_target,
    get_schedule_result,
    parse_pod_info_to_json,
    parse_sr_policies,
    process_steer_data,
    extract_labels,
    extract_pod_logs,
)

headers = {"Content-Type": "application/json"}

app = Flask(__name__)
CORS(app)


# HTTP GET 请求处理
@app.route("/schedule", methods=["GET"])
def get_schedule():
    try:
        data = get_schedule_result()
        # print("Best Cluster:", data["best_cluster"])
        # print("Scores:", data["scores"])
        return jsonify(
            {
                "average_resource": data["average_resource"],
                "best_cluster": data["best_cluster"],
                "scores": data["scores"],
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/dashboard/nodes", methods=["GET"])
def get_nodes():
    try:
        command = "kubectl get nodes -o wide --show-labels"
        commanda = assign_target(command, "a")
        commandb = assign_target(command, "b")
        url = "http://localhost:5090/execute"

        responsea = requests.post(
            url, headers=headers, data=json.dumps({"command": commanda})
        )
        responseb = requests.post(
            url, headers=headers, data=json.dumps({"command": commandb})
        )
        resulta = responsea.json()
        resultb = responseb.json()

        resulta = parse_pod_info_to_json(resulta["stdout"])
        resultb = parse_pod_info_to_json(resultb["stdout"])

        return jsonify({"cluster_a": resulta, "cluster_b": resultb})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/route/show_paths", methods=["GET"])
def get_paths():
    try:
        url = "http://172.20.2.14:5070/show_paths"

        response = requests.get(url)
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/route/show_sid", methods=["GET"])
def get_sid():
    try:
        url = "http://172.20.2.14:5070/show_sid"
        router_id = request.args.get("router")
        if not router_id:
            return jsonify({"error": "Missing 'router' parameter"}), 400

        response = requests.get(url, params={"router": router_id})
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/route/show_policy", methods=["GET"])
def get_policy():
    try:
        url = "http://172.20.2.14:5070/show_policy"
        router_id = request.args.get("router")
        if not router_id:
            return jsonify({"error": "Missing 'router' parameter"}), 400

        response = requests.get(url, params={"router": router_id})
        data = response.json()
        data = parse_sr_policies(data["policies"])
        return jsonify({"policies": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/route/show_steer", methods=["GET"])
def get_steer():
    try:
        url = "http://172.20.2.14:5070/show_steer_pol"
        router_id = request.args.get("router")
        if not router_id:
            return jsonify({"error": "Missing 'router' parameter"}), 400

        response = requests.get(url, params={"router": router_id})
        data = response.json()
        data = process_steer_data(data["steering_policies"])
        return jsonify({"steer": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/route/add_policy", methods=["POST"])
def add_policy():
    try:
        url = "http://172.20.2.14:5070/add_policy"
        router_id = request.args.get("router")
        if not router_id:
            return (
                jsonify({"error": "Missing 'router' parameter", "success": False}),
                400,
            )

        data = request.get_json()
        bsid = data.get("bsid")
        sids = data.get("sids")

        response = requests.post(
            url, params={"router": router_id}, headers=headers, data=json.dumps(data)
        )
        data = response.json()
        return jsonify({"message": data["message"], "success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/route/steer", methods=["POST"])
def steer():
    try:
        url = "http://172.20.2.14:5070/steer"
        router_id = request.args.get("router")
        if not router_id:
            return (
                jsonify({"error": "Missing 'router' parameter", "success": False}),
                400,
            )

        data = request.get_json()

        response = requests.post(
            url, params={"router": router_id}, headers=headers, data=json.dumps(data)
        )
        data = response.json()
        return jsonify({"message": data["message"], "success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/route/del_steer", methods=["DELETE"])
def del_steer():
    try:
        url = "http://172.20.2.14:5070/del_steer"
        router_id = request.args.get("router")
        if not router_id:
            return (
                jsonify({"error": "Missing 'router' parameter", "success": False}),
                400,
            )

        data = request.get_json()

        response = requests.delete(
            url, params={"router": router_id}, headers=headers, data=json.dumps(data)
        )
        data = response.json()
        return jsonify({"message": data["message"], "success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/route/del_policy", methods=["DELETE"])
def del_policy():
    try:
        url = "http://172.20.2.14:5070/del_policy"
        router_id = request.args.get("router")
        if not router_id:
            return (
                jsonify({"error": "Missing 'router' parameter", "success": False}),
                400,
            )

        data = request.get_json()

        response = requests.delete(
            url, params={"router": router_id}, headers=headers, data=json.dumps(data)
        )
        data = response.json()
        return jsonify({"message": data["message"], "success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/service/show", methods=["GET"])
def get_services():
    try:
        command = "kubectl get svc -A"
        commanda = assign_target(command, "a")
        commandb = assign_target(command, "b")
        url = "http://localhost:5090/execute"

        responsea = requests.post(
            url, headers=headers, data=json.dumps({"command": commanda})
        )
        responseb = requests.post(
            url, headers=headers, data=json.dumps({"command": commandb})
        )
        resulta = responsea.json()
        resultb = responseb.json()

        resulta = resulta["stdout"]
        resultb = resultb["stdout"]

        resulta = parse_pod_info_to_json(resulta)
        resultb = parse_pod_info_to_json(resultb)

        return jsonify({"cluster_a": resulta, "cluster_b": resultb})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/service/deploy", methods=["POST"])
def deploy_service():
    try:
        url = "http://172.20.2.14:5090/deploy"

        data = request.get_json()
        yaml_content = data["yaml"]
        dst = data["dst"]

        response = requests.post(
            url, headers=headers, data=json.dumps({"dst": dst, "yaml": yaml_content})
        )
        data = response.json()
        if data["returncode"] == 0:
            return jsonify({"stdout": data["stdout"], "error": False})
        else:
            return jsonify({"stdout": data["stdout"], "error": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/pod/show", methods=["GET"])
def get_pods():
    try:
        command = "kubectl get pods -A -owide"
        commanda = assign_target(command, "a")
        commandb = assign_target(command, "b")
        url = "http://localhost:5090/execute"

        responsea = requests.post(
            url, headers=headers, data=json.dumps({"command": commanda})
        )
        responseb = requests.post(
            url, headers=headers, data=json.dumps({"command": commandb})
        )
        resulta = responsea.json()
        resultb = responseb.json()

        resulta = resulta["stdout"]
        resultb = resultb["stdout"]

        resulta = parse_pod_info_to_json(resulta)
        resultb = parse_pod_info_to_json(resultb)

        return jsonify({"cluster_a": resulta, "cluster_b": resultb})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/pod/deploy", methods=["POST"])
def deploy_pod():
    try:
        url = "http://172.20.2.14:5090/deploy"

        data = request.get_json()
        # print(data)
        yaml_content = data["yaml"]
        dst = get_schedule_result()
        if dst["best_cluster"] == "hosta":
            dst = "a"
        elif dst["best_cluster"] == "hostb":
            dst = "b"

        response = requests.post(
            url, headers=headers, data=json.dumps({"dst": dst, "yaml": yaml_content})
        )
        data = response.json()
        if data["returncode"] == 0:
            if "created" in data["stdout"]:
                deployment = extract_labels(yaml_content)
                command = f"kubectl get pods -l app={deployment['app_label']} -n {deployment['namespace']}"
                command = assign_target(command, dst)
                t_url = "http://localhost:5090/execute"
                t_response = requests.post(
                    t_url, headers=headers, data=json.dumps({"command": command})
                )
                pod = t_response.json()["stdout"]
                pods = parse_pod_info_to_json(pod)
                pod_names = []
                for po in pods:
                    pod_names.append(po["NAME"])

                command = f"kubectl logs kube-scheduler-host{dst} -n kube-system"
                command = assign_target(command, dst)
                command = command + f" | grep score"
                t_response = requests.post(
                    t_url, headers=headers, data=json.dumps({"command": command})
                )
                schedule = t_response.json()["stdout"]

                for pod_name in pod_names:
                    logs = extract_pod_logs(schedule, pod_name)
                    print(logs)

            return jsonify({"stdout": data["stdout"], "dst": dst, "error": False})
        else:
            return jsonify({"stdout": data["stdout"], "dst": dst, "error": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/view", methods=["POST"])
def view():
    data = request.get_json()
    command = data.get("command")
    dst = data.get("dst")

    if not command:
        return {"error": "缺少命令参数"}, 400

    # 检查命令是否以 'kubectl' 开头
    if not command.strip().startswith("kubectl"):
        return {"error": "命令必须以 kubectl 开头"}, 400

    if dst not in ["a", "b"]:
        return {"error": "目标必须从a或b中选择"}, 400

    try:
        if dst == "a":
            command += " --kubeconfig=config-a"
        elif dst == "b":
            command += " --kubeconfig=config-b"
        # 执行命令
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        # 返回输出
        return jsonify({"stdout": result.stdout}), 200
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/execute", methods=["POST"])
def execute():
    data = request.get_json()
    command = data.get("command")

    if not command:
        return {"error": "缺少命令参数"}, 400

    # 检查命令是否以 'kubectl' 开头
    if not command.strip().startswith("kubectl"):
        return {"error": "命令必须以 kubectl 开头"}, 400

    try:
        dst = get_schedule_result()
        if dst["best_cluster"] == "hosta":
            command += " --kubeconfig=config-a"
        elif dst["best_cluster"] == "hostb":
            command += " --kubeconfig=config-b"
        # 执行命令
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        # 返回输出
        return (
            jsonify(
                {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                }
            ),
            200,
        )
    except Exception as e:
        return {"error": str(e)}, 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
