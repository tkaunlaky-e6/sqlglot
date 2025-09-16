# Simple API Benchmarking

## Files:
- `baseline_curl.sh` - Test single requests
- `run_locust_test.sh` - Load testing  
- `locustfile.py` - Locust configuration
- `queries.txt` - Test queries

## Usage:

### 1. Baseline Test
```bash
./baseline_curl.sh
```
Shows response times for individual requests.

### 2. Load Test  
```bash
./run_locust_test.sh
```
Opens web UI at http://localhost:8089
- Start with 5 users, 1 user/sec spawn rate
- Increase to 10, 25, 50 users
- Watch for response time increases

### 3. Monitor Container
```bash
docker stats api-test
```
Shows CPU/memory usage in real-time.

## Profiling Fix:
**Problem**: py-spy doesn't work in Alpine containers
**Solution**: Use container monitoring:
```bash
# Monitor during load test
docker stats --no-stream api-test

# Check container processes  
docker exec api-test ps aux
```

**Key Metrics**:
- Response time (baseline vs load)
- Requests per second (from Locust)  
- CPU/memory usage (docker stats)