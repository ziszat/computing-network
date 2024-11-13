import heapq

connections = [
    ("r0", "r1", 100),
    ("r1", "r2", 200),
    ("r1", "r3", 300),
    ("r2", "r4", 200),
    ("r3", "r5", 300),
    ("r2", "r5", 300),
    ("r4", "r6", 100),
    ("r5", "r6", 100),
]

ROUTER_SIDS = {
    "r0": "fc00:f::a",
    "r1": "fc00:1::a",
    "r2": "fc00:2::a",
    "r3": "fc00:33::a",
    "r4": "fc00:4::a",
    "r5": "fc00:5::a",
    "r6": "fc00:6::a",
}


# 创建邻接表
def create_graph(connections):
    graph = {}
    for src, dst, weight in connections:
        if src not in graph:
            graph[src] = []
        if dst not in graph:
            graph[dst] = []
        graph[src].append((dst, weight))
        graph[dst].append((src, weight))
    return graph


# Dijkstra算法
def dijkstra(graph, start):
    # 初始化最小堆，距离表和前驱节点表
    queue = [(0, start)]  # (距离, 节点)
    distances = {node: float("inf") for node in graph}
    previous_nodes = {node: None for node in graph}

    distances[start] = 0

    while queue:
        current_distance, current_node = heapq.heappop(queue)

        # 如果找到的距离比当前记录的大，跳过
        if current_distance > distances[current_node]:
            continue

        # 遍历相邻节点
        for neighbor, weight in graph[current_node]:
            distance = current_distance + weight

            # 如果找到更短的路径，更新距离和前驱节点
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous_nodes[neighbor] = current_node
                heapq.heappush(queue, (distance, neighbor))

    return distances, previous_nodes


# 打印每个路由器的最短路径和距离
def print_paths(start, distances, previous_nodes):
    paths = []
    for node in distances:
        if (
            node == start
            or node == "r1"
            or node == "r2"
            or node == "r4"
            or node == "r5"
        ):
            continue
        path = []
        current = node
        while current is not None:
            path.append(ROUTER_SIDS[current])
            current = previous_nodes[current]
        path1 = path.copy()
        path2 = path.copy()

        del path1[0]
        path2.reverse()
        del path2[0]

        paths.append(
            f"Shortest path from {node} to {start}: {','.join(path1)}, Distance: {distances[node]}"
        )

        paths.append(
            f"Shortest path from {start} to {node}: {','.join(path2)}, Distance: {distances[node]}"
        )

    return paths


def generate():
    # 生成图
    graph = create_graph(connections)

    # 运行Dijkstra算法，从R0开始
    distances, previous_nodes = dijkstra(graph, "r0")
    # 打印结果
    return print_paths("r0", distances, previous_nodes)
