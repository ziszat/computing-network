import json
from flask import Flask, request, jsonify
import subprocess
import requests
from flask_cors import CORS

headers = {
    "Content-Type": "application/json"
}

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
            return data
        else:
            print(f"Failed to get schedule result. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error occurred: {e}")

app = Flask(__name__)
CORS(app)
# HTTP GET 请求处理
@app.route('/schedule', methods=['GET'])
def get_schedule():
    try:
        data = get_schedule_result()
        # print("Best Cluster:", data["best_cluster"])
        # print("Scores:", data["scores"])
        return jsonify({
            "average_resource": data["average_resource"],
            "best_cluster": data["best_cluster"],
            "scores": data["scores"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/dashboard/nodes', methods=['GET'])
def get_nodes():
    try:
        command = "kubectl get nodes -o wide"
        commanda = assign_target(command, "a")
        commandb = assign_target(command, "b")
        url = "http://localhost:5090/execute"
        
        responsea = requests.post(url, headers=headers, data=json.dumps({"command": commanda}))
        responseb = requests.post(url, headers=headers, data=json.dumps({"command": commandb}))
        resulta = responsea.json()
        resultb = responseb.json()
        
        return jsonify({
            "cluster_a": resulta["stdout"],
            "cluster_b": resultb["stdout"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/route/show_paths', methods=['GET'])
def get_paths():
    try:
        url = "http://172.20.2.14:5070/show_paths"
        
        response = requests.get(url)
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/route/show_sid', methods=['GET'])
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
    
@app.route('/route/show_policy', methods=['GET'])
def get_policy():
    try:
        url = "http://172.20.2.14:5070/show_policy"
        router_id = request.args.get("router")
        if not router_id:
            return jsonify({"error": "Missing 'router' parameter"}), 400
        
        response = requests.get(url, params={"router": router_id})
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/route/show_steer', methods=['GET'])
def get_steer():
    try:
        url = "http://172.20.2.14:5070/show_steer_pol"
        router_id = request.args.get("router")
        if not router_id:
            return jsonify({"error": "Missing 'router' parameter"}), 400
        
        response = requests.get(url, params={"router": router_id})
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/route/add_policy', methods=['POST'])
def add_policy():
    try:
        url = "http://172.20.2.14:5070/add_policy"
        router_id = request.args.get("router")
        if not router_id:
            return jsonify({"error": "Missing 'router' parameter"}), 400
        
        data = request.get_json()
        bsid = data.get("bsid")
        sids = data.get("sids")
        
        response = requests.post(url, params={"router": router_id}, headers=headers, data=json.dumps(data))
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/route/steer', methods=['POST'])
def steer():
    try:
        url = "http://172.20.2.14:5070/steer"
        router_id = request.args.get("router")
        if not router_id:
            return jsonify({"error": "Missing 'router' parameter"}), 400
        
        data = request.get_json()
        
        response = requests.post(url, params={"router": router_id}, headers=headers, data=json.dumps(data))
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/route/del_steer', methods=['DELETE'])
def del_steer():
    try:
        url = "http://172.20.2.14:5070/del_steer"
        router_id = request.args.get("router")
        if not router_id:
            return jsonify({"error": "Missing 'router' parameter"}), 400
        
        data = request.get_json()
        
        response = requests.delete(url, params={"router": router_id}, headers=headers, data=json.dumps(data))
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/route/del_policy', methods=['DELETE'])
def del_policy():
    try:
        url = "http://172.20.2.14:5070/del_policy"
        router_id = request.args.get("router")
        if not router_id:
            return jsonify({"error": "Missing 'router' parameter"}), 400
        
        data = request.get_json()
        
        response = requests.delete(url, params={"router": router_id}, headers=headers, data=json.dumps(data))
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/service/show', methods=['GET'])
def get_services():
    try:
        command = "kubectl get svc -A"
        commanda = assign_target(command, "a")
        commandb = assign_target(command, "b")
        url = "http://localhost:5090/execute"
        
        responsea = requests.post(url, headers=headers, data=json.dumps({"command": commanda}))
        responseb = requests.post(url, headers=headers, data=json.dumps({"command": commandb}))
        resulta = responsea.json()
        resultb = responseb.json()
        
        return jsonify({
            "cluster_a": resulta["stdout"],
            "cluster_b": resultb["stdout"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/view', methods=['POST'])
def view():
    data = request.get_json()
    command = data.get('command')
    dst = data.get('dst')
    
    if not command:
        return {'error': '缺少命令参数'}, 400

    # 检查命令是否以 'kubectl' 开头
    if not command.strip().startswith('kubectl'):
        return {'error': '命令必须以 kubectl 开头'}, 400

    if dst not in ["a","b"]:
        return {'error': '目标必须从a或b中选择'}, 400

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
            universal_newlines=True
        )

        # 返回输出
        return jsonify({
            'stdout': result.stdout
        }), 200
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/execute', methods=['POST'])
def execute():
    data = request.get_json()
    command = data.get('command')
    
    if not command:
        return {'error': '缺少命令参数'}, 400

    # 检查命令是否以 'kubectl' 开头
    if not command.strip().startswith('kubectl'):
        return {'error': '命令必须以 kubectl 开头'}, 400

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
            universal_newlines=True
        )

        # 返回输出
        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }), 200
    except Exception as e:
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)