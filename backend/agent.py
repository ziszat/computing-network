from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)


@app.route("/execute", methods=["POST"])
def execute():
    data = request.get_json()
    command = data["command"]

    if not command:
        return {"error": "缺少命令参数"}, 400

    # 检查命令是否以 'kubectl' 开头
    if not command.strip().startswith("kubectl"):
        return {"error": "命令必须以 kubectl 开头"}, 400

    try:
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
    app.run(host="0.0.0.0", port=5090)
