#!/bin/bash

# Baseline measurement with curl for containerized API
echo "=== CONTAINERIZED API BASELINE MEASUREMENT ==="
echo "Container: api-test (2 CPU, 2GB RAM limit)"
echo "Testing TPC-DS query to establish ground truth..."

# Store the TPC-DS query
TPCDS_QUERY="SELECT s.s_store_name, s.s_store_id, SUM(CASE WHEN d.d_day_name = 'Sunday' THEN ss.ss_sales_price ELSE 0 END) AS sunday_sales, SUM(CASE WHEN d.d_day_name = 'Monday' THEN ss.ss_sales_price ELSE 0 END) AS monday_sales, SUM(CASE WHEN d.d_day_name NOT IN ('Sunday', 'Monday') THEN ss.ss_sales_price ELSE 0 END) AS other_weekday_sales FROM store_sales ss JOIN date_dim d ON ss.ss_sold_date_sk = d.d_date_sk JOIN store s ON ss.ss_store_sk = s.s_store_sk WHERE d.d_year = 2001 GROUP BY s.s_store_name, s.s_store_id ORDER BY s.s_store_name, s.s_store_id"

# Test health endpoint first
echo -e "\n0. Health check:"
curl -s -w "Status: %{http_code}, Time: %{time_total}s\n" http://localhost:8100/health

# Test the TPC-DS query multiple times
echo -e "\n1. Testing TPC-DS query (5 iterations):"
for i in {1..5}; do
  response_time=$(curl -o /dev/null -s -w "%{time_total}" \
    -X POST \
    -F "from_sql=databricks" \
    -F "to_sql=e6" \
    -F "query=$TPCDS_QUERY" \
    http://localhost:8100/convert-query)
  
  # Convert to milliseconds
  response_ms=$(echo "$response_time * 1000" | bc)
  printf "  Iteration %d: %6.2f ms\n" $i $response_ms
done

echo -e "\n=== BASELINE COMPLETE ==="
echo "Note these times - they are your target to maintain under load."
echo ""
echo "Container Resource Usage:"
docker stats --no-stream api-test