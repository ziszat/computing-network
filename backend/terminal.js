const WebSocket = require('ws');
const { spawn } = require('child_process');

// WebSocket 服务器监听端口
const wss = new WebSocket.Server({ host: '0.0.0.0', port: 2999 });

wss.on('connection', (ws) => {
  // 启动本机的 SSH 会话（连接到 localhost）
  const ssh = spawn('sshpass', ['-p','123456','ssh','-tt','-p', '2210', 'root@localhost']); // 强制分配伪终端


  // 转发 SSH 输出到 WebSocket 客户端（前端）
  ssh.stdout.on('data', (data) => {
    ws.send(data.toString());
  });

  // 转发 SSH 错误输出到 WebSocket 客户端（前端）
  ssh.stderr.on('data', (data) => {
    ws.send(data.toString());
  });

  // 接收来自前端的输入并通过 SSH 发送到本机的 SSH 会话
  ws.on('message', (message) => {
    ssh.stdin.write(message);
  });

  // 关闭 WebSocket 连接时，终止 SSH 会话
  ws.on('close', () => {
    ssh.kill();
  });
});

console.log('WebSocket 服务器已启动');