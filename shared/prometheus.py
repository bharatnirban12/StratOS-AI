from prometheus_client import Counter, Histogram

simulation_counter = Counter(
    "simulation_requests_total",
    "Total simulation requests"
)

agent_latency = Histogram(
    "agent_execution_seconds",
    "Agent execution time",
    ["agent_name"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30)
)

agent_failures = Counter(
    "agent_failure_total",
    "Total agent failure",
    ["agent_name"]
)