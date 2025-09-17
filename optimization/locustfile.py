from locust import HttpUser, task, between
import json
import time

# Original TPC-DS query for baseline testing
TPCDS_QUERY = """SELECT s.s_store_name, s.s_store_id,
    SUM(CASE WHEN d.d_day_name = 'Sunday' THEN ss.ss_sales_price ELSE 0 END) AS sunday_sales,
    SUM(CASE WHEN d.d_day_name = 'Monday' THEN ss.ss_sales_price ELSE 0 END) AS monday_sales,
    SUM(CASE WHEN d.d_day_name NOT IN ('Sunday', 'Monday') THEN ss.ss_sales_price ELSE 0 END) AS other_weekday_sales
    FROM store_sales ss
    JOIN date_dim d ON ss.ss_sold_date_sk = d.d_date_sk
    JOIN store s ON ss.ss_store_sk = s.s_store_sk
    WHERE d.d_year = 2001
    GROUP BY s.s_store_name, s.s_store_id
    ORDER BY s.s_store_name, s.s_store_id"""

# Comprehensive E6 generator stress test query - exercises all dialect features
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
    WHEN revenue > 3000 THEN CONCAT('Top Store: ', store_name)
    ELSE CONCAT('Regular Store: ', store_name)
  END as performance_summary,
  LAG(revenue, 1, 0) OVER (ORDER BY store_id) as prev_store_revenue,
  ROUND(revenue / GREATEST(AVG(revenue) OVER (), 1) * 100, 2) as performance_index,
  CURRENT_TIMESTAMP() as report_time
FROM conditional_operations
ORDER BY revenue DESC
LIMIT 50
"""

class SqlConverterUser(HttpUser):
    wait_time = between(1, 2)  # Wait 1-2 seconds between requests

    def on_start(self):
        """Called when a simulated user starts"""
        # Test health endpoint on start
        self.client.get("/health")

    @task  # Comprehensive E6 generator stress test
    def convert_comprehensive_query(self):
        """Test comprehensive E6 generator features - exercises all dialect transformations"""
        form_data = {
            "query": COMPREHENSIVE_E6_QUERY,
            "from_sql": "databricks",
            "to_sql": "e6"
        }
        # Use catch_response=True to manually handle the response
        with self.client.post(
            "/convert-query",
            data=form_data,
            name="/convert-query-comprehensive-e6",
            catch_response=True  # Enable manual response handling
        ) as response:
            # Manually mark success or failure based on status code
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got non-200 status code: {response.status_code}")

    # @task  # Commented out - TPC-DS baseline query
    # def convert_tpcds_query(self):
    #     """Test TPC-DS query transpilation (baseline)"""
    #     form_data = {
    #         "query": TPCDS_QUERY,
    #         "from_sql": "databricks",
    #         "to_sql": "e6"
    #     }
    #     with self.client.post(
    #         "/convert-query",
    #         data=form_data,
    #         name="/convert-query-tpcds",
    #         catch_response=True
    #     ) as response:
    #         if response.status_code == 200:
    #             response.success()
    #         else:
    #             response.failure(f"Got non-200 status code: {response.status_code}")
    
