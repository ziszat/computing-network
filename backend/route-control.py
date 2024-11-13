import json
from flask import Flask, request, jsonify
import paramiko
from route_gen import generate

app = Flask(__name__)

ROUTER_PORT = {"r0": 2208, "r3": 2203, "r6": 2209}

ROUTER_SIDS = {
    "r0": "fc00:f::a",
    "r1": "fc00:1::a",
    "r2": "fc00:2::a",
    "r3": "fc00:33::a",
    "r4": "fc00:4::a",
    "r5": "fc00:5::a",
    "r6": "fc00:6::a",
}


def load_config():
    data = {}
    with open("./route-control/config.json", "r") as f:
        data = json.loads(f.read())
    return data


class VPPController_CLI(object):
    def __init__(self, port, username, password):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname="localhost", port=port, username=username, password=password
        )

    def show_sid(self):
        stdin, stdout, stderr = self.client.exec_command("vppctl show sr localsids")
        return stdout.readlines()

    def show_policy(self):
        stdin, stdout, stderr = self.client.exec_command("vppctl show sr policies")
        return stdout.readlines()

    def show_steering_policies(self):
        stdin, stdout, stderr = self.client.exec_command(
            "vppctl show sr steering-policies"
        )
        return stdout.readlines()

    def add_policy(self, bsid, sids):
        sid_param = " ".join(f"next {sid}" for sid in sids)
        cmd = f"vppctl sr policy add bsid {bsid} {sid_param} encap"
        # print(cmd)
        stdin, stdout, stderr = self.client.exec_command(cmd)
        result = stdout.readlines()
        for line in result:
            if "already a FIB entry for the BindingSID address" in line:
                return {
                    "error": "already a FIB entry for the BindingSID address"
                }, False
        return result, True

    def update_steering(self, ip_prefix, bsid):
        cmd = f"vppctl sr steer l3 {ip_prefix} via bsid {bsid}"
        stdin, stdout, stderr = self.client.exec_command(cmd)
        return stdout.readlines()

    def del_policy(self, bsid):
        cmd = f"vppctl sr policy del bsid {bsid}"
        stdin, stdout, stderr = self.client.exec_command(cmd)
        return stdout.readlines()

    def del_steering_policies(self, ip):
        cmd = f"vppctl sr steer del l3 {ip}"
        stdin, stdout, stderr = self.client.exec_command(cmd)
        return stdout.readlines()


# def controller():
#     print("==========SRv6 Controller==========\n")
#     config=load_config()

#     while True:
#         router = input("Choose a router(r0, r1, ..., r6): ").strip().lower()
#         router = config[router]
#         router = VPPController_CLI(router["port"], router["username"], router["password"])

#         # Get user input for operation and paths
#         print("\n==============OPTIONS==============")
#         print("1: Show SR policies")
#         print("2: Show localsids")
#         print("3: Add a policy to a BindingSID")
#         print("4: Steer a destination to a policy")
#         print("5: Delete a policy")
#         print("6: Exit")
#         print("===================================\n")

#         operation = input("Enter an option number: ").strip().lower()
#         if operation == "6":
#             break

#         if operation not in ["1", "2", "3", "4", "5"]:
#             print("Invalid operation. Please use numbers 1-6.")
#             continue

#         if operation == "1":
#             router.show_policy()

#         if operation == "2":
#             router.show_sid()

#         if operation == "3":
#             bsid = input("Assign a BindingSID: ").strip().lower()
#             path = input("Enter segments (comma-separated, e.g., fc00:1::a,fc00:2::a): ").strip().split(",")
#             router.add_policy(bsid, path)

#         if operation == "4":
#             dst = input("Enter destination (e.g., 10.0.0.0/24): ").strip()
#             print("Known policies:")
#             router.show_policy()
#             bsid = input("Choose a BindingSID: ").strip()
#             router.update_steering(dst, bsid)

#         if operation == "5":
#             print("Known policies:")
#             router.show_policy()
#             bsid = input("Choose a BindingSID to delete: ").strip()
#             router.del_policy(bsid)


# 用于验证并获取对应 router 配置
def get_router_from_params():
    router_id = request.args.get("router")
    if not router_id:
        return None, jsonify({"error": "Missing 'router' parameter"}), 400

    config = load_config()
    if router_id not in config:
        return None, jsonify({"error": "Router not found"}), 404

    router_conf = config[router_id]
    return (
        VPPController_CLI(
            router_conf["port"], router_conf["username"], router_conf["password"]
        ),
        None,
    )


@app.route("/show_paths", methods=["GET"])
def show_paths():
    return jsonify({"paths": generate()})


@app.route("/show_policy", methods=["GET"])
def show_policy():
    router, error_response = get_router_from_params()
    if error_response:
        return error_response

    return jsonify({"policies": router.show_policy()})


@app.route("/show_sid", methods=["GET"])
def show_sid():
    router, error_response = get_router_from_params()
    if error_response:
        return error_response

    return jsonify({"localsids": router.show_sid()})


@app.route("/show_steer_pol", methods=["GET"])
def show_steer():
    router, error_response = get_router_from_params()
    if error_response:
        return error_response

    return jsonify({"steering_policies": router.show_steering_policies()})


@app.route("/add_policy", methods=["POST"])
def add_policy():
    router, error_response = get_router_from_params()
    if error_response:
        return error_response

    data = request.get_json()
    bsid = data.get("bsid")
    sids = data.get("sids")
    if not bsid or not sids:
        return jsonify({"error": "Missing BSID or SIDs"}), 400

    sids = sids.strip().split(",")
    result, success = router.add_policy(bsid, sids)
    if success:
        return jsonify({"message": "Policy added", "result": result})
    else:
        return jsonify(result), 400


@app.route("/steer", methods=["POST"])
def steer_policy():
    router, error_response = get_router_from_params()
    if error_response:
        return error_response

    data = request.get_json()
    ip_prefix = data.get("ip_prefix")
    bsid = data.get("bsid")
    if not ip_prefix or not bsid:
        return jsonify({"error": "Missing IP prefix or BSID"}), 400

    result = router.update_steering(ip_prefix, bsid)
    return jsonify({"message": "Steering updated", "result": result})


@app.route("/del_policy", methods=["DELETE"])
def del_policy():
    router, error_response = get_router_from_params()
    if error_response:
        return error_response

    data = request.get_json()
    bsid = data.get("bsid")
    if not bsid:
        return jsonify({"error": "Missing BSID"}), 400

    result = router.del_policy(bsid)
    return jsonify({"message": "Policy deleted", "result": result})


@app.route("/del_steer", methods=["DELETE"])
def del_steer():
    router, error_response = get_router_from_params()
    if error_response:
        return error_response

    data = request.get_json()
    ip = data.get("ip_prefix")
    if not ip:
        return jsonify({"error": "Missing IP"}), 400

    result = router.del_steering_policies(ip)
    return jsonify({"message": f"Steer to {ip} deleted", "result": result})


if __name__ == "__main__":
    # print("==========Generate Route==========\n")
    # generate()
    app.run(host="0.0.0.0", port=5070)
    # controller()
