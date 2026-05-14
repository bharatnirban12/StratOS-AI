from prometheus_client import start_http_server

def start_metrics_server():
    start_http_server(8001, addr="0.0.0.0")
