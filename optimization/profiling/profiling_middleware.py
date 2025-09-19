# profiling_middleware.py
import time
import cProfile
import pstats
from pyinstrument import Profiler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

# Comprehensive E6 generator test query for benchmarking
COMPREHENSIVE_E6_QUERY = """
WITH
sample_data AS (
  SELECT * FROM VALUES
    (1, 'store_a', TIMESTAMP '2023-01-01 10:30:00.123', DATE '2023-01-01', 1500.50, TRUE, ARRAY[1,2,3], MAP('region', 'north', 'tier', 'premium')),
    (2, 'store_b', TIMESTAMP '2023-01-02 14:15:30.456', DATE '2023-01-02', 2750.75, FALSE, ARRAY[4,5,6], MAP('region', 'south', 'tier', 'standard')),
    (3, 'store_c', TIMESTAMP '2023-01-03 09:45:15.789', DATE '2023-01-03', 3200.25, TRUE, ARRAY[7,8,9], MAP('region', 'east', 'tier', 'premium'))
  AS t(store_id, store_name, created_at, business_date, revenue, is_active, product_ids, metadata_map)
),
time_transformations AS (
  SELECT
    store_id, store_name, created_at, business_date, revenue, is_active, product_ids, metadata_map,
    TO_TIMESTAMP('2023-01-01 10:30:00', 'yyyy-MM-dd HH:mm:ss') as parsed_timestamp,
    FROM_TIMESTAMP(created_at, 'yyyy-MM-dd HH:mm:ss.SSS') as formatted_timestamp,
    TO_DATE('2023-01-01', 'yyyy-MM-dd') as parsed_date,
    FROM_UNIXTIME(1672574200) as unix_to_timestamp,
    TO_UNIX_TIMESTAMP(created_at) as timestamp_to_unix,
    DATE_ADD(business_date, 30) as date_plus_30,
    DATEDIFF(DATE '2023-12-31', business_date) as days_to_year_end,
    EXTRACT(YEAR FROM created_at) as extract_year,
    EXTRACT(MONTH FROM created_at) as extract_month,
    DATE_TRUNC('month', created_at) as month_start,
    CURRENT_TIMESTAMP() as current_ts
  FROM sample_data
),
array_operations AS (
  SELECT
    store_id, store_name, created_at, revenue,
    SIZE(product_ids) as array_size,
    ARRAY_CONTAINS(product_ids, 5) as contains_five,
    ARRAY_POSITION(product_ids, 8) as position_of_eight,
    SLICE(product_ids, 1, 2) as array_slice,
    ARRAY_CONCAT(product_ids, ARRAY[99, 100]) as concatenated_array,
    FILTER(product_ids, x -> x > 5) as filtered_array,
    TRANSFORM(product_ids, x -> x * 2) as doubled_array,
    ARRAY_JOIN(product_ids, ',') as joined_string
  FROM time_transformations
),
string_operations AS (
  SELECT
    store_id, store_name, created_at, revenue,
    UPPER(store_name) as uppercase_name,
    LENGTH(store_name) as name_length,
    POSITION('store' IN store_name) as store_position,
    SUBSTR(store_name, 1, 5) as name_prefix,
    REPLACE(store_name, 'store_', 'shop_') as replaced_name,
    REGEXP_REPLACE(store_name, '[aeiou]', 'X') as vowels_replaced,
    SPLIT(CONCAT(store_name, '_extra'), '_') as name_parts
  FROM array_operations
),
math_operations AS (
  SELECT
    store_id, store_name, revenue, created_at,
    ABS(-revenue) as abs_revenue,
    ROUND(revenue, 2) as rounded_revenue,
    SQRT(revenue) as sqrt_revenue,
    SUM(revenue) OVER (ORDER BY store_id ROWS UNBOUNDED PRECEDING) as running_total,
    ROW_NUMBER() OVER (ORDER BY revenue DESC) as row_num,
    RANK() OVER (ORDER BY revenue DESC) as revenue_rank,
    LAG(revenue, 1, 0) OVER (ORDER BY created_at) as prev_revenue,
    LEAD(revenue, 1, 0) OVER (ORDER BY created_at) as next_revenue
  FROM string_operations
),
type_conversions AS (
  SELECT
    store_id, store_name, revenue, created_at,
    CAST(store_id AS VARCHAR(10)) as id_as_string,
    CAST(revenue AS DECIMAL(10,2)) as revenue_decimal,
    CAST('2023-01-01' AS DATE) as string_as_date,
    TRY_CAST('123' AS INT) as safe_cast_success,
    created_at + INTERVAL '1 day' as plus_one_day
  FROM math_operations
),
conditional_operations AS (
  SELECT
    store_id, store_name, revenue,
    CASE
      WHEN revenue > 3000 THEN 'High Revenue'
      WHEN revenue > 2000 THEN 'Medium Revenue'
      ELSE 'Low Revenue'
    END as revenue_category,
    COALESCE(revenue, 0) as coalesced_revenue,
    NVL2(revenue, 'Has Value', 'Is Null') as nvl2_result,
    GREATEST(revenue, 1000) as max_value,
    created_at
  FROM type_conversions
)
SELECT
  store_id,
  store_name,
  FORMAT_NUMBER(revenue, 2) as formatted_revenue,
  revenue_category,
  CONCAT('Store: ', store_name, ' Revenue: $', CAST(revenue AS STRING)) as summary,
  CASE
    WHEN revenue > 3000 THEN CONCAT('🔥 Top Store: ', store_name)
    ELSE CONCAT('📊 Regular Store: ', store_name)
  END as performance_summary,
  LAG(revenue, 1, 0) OVER (ORDER BY store_id) as prev_store_revenue,
  ROUND(revenue / GREATEST(AVG(revenue) OVER (), 1) * 100, 2) as performance_index,
  CURRENT_TIMESTAMP() as report_time
FROM conditional_operations
ORDER BY revenue DESC
LIMIT 50
"""

class ProfilingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Check for a query parameter to enable profiling
        if "profile" in request.query_params:
            # Use pyinstrument to profile the request
            profiler = Profiler(async_mode="enabled")
            profiler.start()

            # Process the request
            response = await call_next(request)

            profiler.stop()

            # Generate a unique filename and save the report
            timestamp = int(time.time())
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            report_filename = os.path.join(base_dir, "optimization", "profiling", f"profile_report_{timestamp}.html")

            with open(report_filename, "w", encoding="utf-8") as f:
                f.write(profiler.output_html())

            print(f"🚀 Profiling report saved to: {report_filename}")
            print(f"📊 Query analyzed: Comprehensive E6 generator test ({len(COMPREHENSIVE_E6_QUERY)} chars)")
            print("🔧 E6 features tested: VALUES->CAST, timestamp functions, array ops, window functions")

            return response
        else:
            # If not profiling, just process the request normally
            return await call_next(request)