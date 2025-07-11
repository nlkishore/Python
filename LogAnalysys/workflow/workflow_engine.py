# workflow_engine.py

class WorkflowEngine:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.state = {}

    def add_node(self, name, func):
        self.nodes[name] = func

    def add_edge(self, from_node, to_node):
        self.edges.setdefault(from_node, []).append(to_node)

    def run(self, start_node, state=None):
        self.state = state or {}
        current = start_node
        while current:
            print(f"🔄 Executing node: {current}")
            result = self.nodes[current](self.state)
            self.state.update(result or {})
            next_nodes = self.edges.get(current, [])
            current = next_nodes[0] if next_nodes else None
        return self.state