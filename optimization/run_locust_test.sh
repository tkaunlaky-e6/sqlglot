#!/bin/bash

# Run Locust load test against containerized API
echo "=== LOCUST LOAD TEST FOR CONTAINERIZED API ==="
echo "Target: http://localhost:8100 (containerized API)"
echo ""
echo "Starting Locust web interface..."
echo "Open http://localhost:8089 in your browser"
echo ""
echo "Recommended test parameters:"
echo "- Start with 5 users, spawn rate 1 user/sec"
echo "- Gradually increase: 10, 25, 50, 100 users"
echo "- Watch for when RPS plateaus and response times spike"
echo ""
echo "Key metrics to monitor:"
echo "- Requests per Second (RPS)"
echo "- Response Time (95th percentile)"
echo "- Failure rate"
echo ""
echo "In another terminal, monitor container resources:"
echo "  watch -n 1 'docker stats --no-stream api-test'"
echo ""

# Install locust if not available
if ! command -v locust &> /dev/null; then
    echo "Installing locust..."
    pip install locust
fi

# Change to optimization directory and run locust
cd "$(dirname "$0")"

# Run locust pointing to the containerized API
locust -f locustfile.py --host=http://localhost:8100