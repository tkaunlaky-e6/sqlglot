-- COMPREHENSIVE E6 GENERATOR TEST QUERY
-- This query exercises every major feature of the E6 dialect generator
-- Including: VALUES transpilation, timestamps, complex functions, window functions,
-- type mappings, array operations, string functions, date/time functions, and more

WITH
-- Test VALUES clause transpilation from Databricks to E6 (using UNION ALL instead of VALUES)
sample_data AS (
  SELECT
    1 as store_id,
    'store_a' as store_name,
    CAST('2023-01-01 10:30:00.123' AS TIMESTAMP) as created_at,
    CAST('2023-01-01' AS DATE) as business_date,
    1500.50 as revenue,
    TRUE as is_active,
    ARRAY[1,2,3] as product_ids
  UNION ALL
  SELECT
    2 as store_id,
    'store_b' as store_name,
    CAST('2023-01-02 14:15:30.456' AS TIMESTAMP) as created_at,
    CAST('2023-01-02' AS DATE) as business_date,
    2750.75 as revenue,
    FALSE as is_active,
    ARRAY[4,5,6] as product_ids
  UNION ALL
  SELECT
    3 as store_id,
    'store_c' as store_name,
    CAST('2023-01-03 09:45:15.789' AS TIMESTAMP) as created_at,
    CAST('2023-01-03' AS DATE) as business_date,
    3200.25 as revenue,
    TRUE as is_active,
    ARRAY[7,8,9] as product_ids
  UNION ALL
  SELECT
    4 as store_id,
    'store_d' as store_name,
    CAST('2023-01-04 16:20:45.012' AS TIMESTAMP) as created_at,
    CAST('2023-01-04' AS DATE) as business_date,
    1800.00 as revenue,
    NULL as is_active,
    ARRAY[10,11,12] as product_ids
),

-- Test comprehensive timestamp and date functions
time_transformations AS (
  SELECT
    store_id,
    store_name,
    created_at,
    business_date,

    -- E6 timestamp functions - test TIME_MAPPING transformations
    TO_TIMESTAMP('2023-01-01 10:30:00', 'yyyy-MM-dd HH:mm:ss') as parsed_timestamp,
    FROM_TIMESTAMP(created_at, 'yyyy-MM-dd HH:mm:ss.SSS') as formatted_timestamp,
    TO_DATE('2023-01-01', 'yyyy-MM-dd') as parsed_date,
    FROM_UNIXTIME(1672574200) as unix_to_timestamp,
    TO_UNIX_TIMESTAMP(created_at) as timestamp_to_unix,
    TO_UNIX_TIMESTAMP('2023-01-01 10:30:00', 'yyyy-MM-dd HH:mm:ss') as string_to_unix,

    -- Date arithmetic and extraction
    DATE_ADD(business_date, 30) as date_plus_30,
    DATE_SUB(business_date, 15) as date_minus_15,
    DATEDIFF(CAST('2023-12-31' AS DATE), business_date) as days_to_year_end,

    -- Extract functions
    EXTRACT(YEAR FROM created_at) as extract_year,
    EXTRACT(MONTH FROM created_at) as extract_month,
    EXTRACT(DAY FROM created_at) as extract_day,
    EXTRACT(HOUR FROM created_at) as extract_hour,
    EXTRACT(MINUTE FROM created_at) as extract_minute,
    EXTRACT(SECOND FROM created_at) as extract_second,

    -- Date truncation
    DATE_TRUNC('month', created_at) as month_start,
    DATE_TRUNC('week', created_at) as week_start,
    DATE_TRUNC('day', created_at) as day_start,
    DATE_TRUNC('hour', created_at) as hour_start,

    -- Current time functions
    CURRENT_TIMESTAMP() as current_ts,
    CURRENT_DATE() as current_dt,
    NOW() as now_ts,

    revenue,
    is_active,
    product_ids
  FROM sample_data
),

-- Test array operations and functions (E6 transforms ArrayXxx functions)
array_operations AS (
  SELECT
    store_id,
    store_name,
    product_ids,

    -- Array functions that get transformed by E6
    SIZE(product_ids) as array_size,
    ARRAY_CONTAINS(product_ids, 5) as contains_five,
    CARDINALITY(product_ids) as array_cardinality,

    -- Array aggregations
    ARRAY_AGG(store_id) OVER (ORDER BY store_id ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) as windowed_array_agg,

    -- Array slicing and manipulation
    SLICE(product_ids, 1, 2) as array_slice,
    ARRAY_CONCAT(product_ids, ARRAY[99, 100]) as concatenated_array,

    -- Array to string conversion
    ARRAY_JOIN(product_ids, ',') as joined_string,
    ARRAY_TO_STRING(product_ids, '|') as pipe_separated,

    created_at,
    revenue
  FROM time_transformations
),

-- Test string functions and operations
string_operations AS (
  SELECT
    store_id,
    store_name,

    -- String manipulation
    UPPER(store_name) as uppercase_name,
    LOWER(store_name) as lowercase_name,
    INITCAP(store_name) as title_case_name,
    LENGTH(store_name) as name_length,
    CHAR_LENGTH(store_name) as char_count,

    -- String searching and extraction
    LOCATE('_', store_name) as underscore_position,
    SUBSTR(store_name, 1, 5) as name_prefix,
    SUBSTRING(store_name, -1, 1) as last_character,
    LEFT(store_name, 3) as left_3_chars,
    RIGHT(store_name, 2) as right_2_chars,

    -- String padding and trimming
    LPAD(store_name, 15, '*') as left_padded,
    RPAD(store_name, 15, '*') as right_padded,
    TRIM(CONCAT(' ', store_name, ' ')) as trimmed_name,
    LTRIM(CONCAT('   ', store_name)) as left_trimmed,
    RTRIM(CONCAT(store_name, '   ')) as right_trimmed,

    -- String replacement and regex
    REPLACE(store_name, 'store_', 'shop_') as replaced_name,
    REGEXP_REPLACE(store_name, '[aeiou]', 'X') as vowels_replaced,

    -- String splitting and joining
    SPLIT(CONCAT(store_name, '_extra_part'), '_') as name_parts,

    -- JSON string functions (E6 supports JSON type)
    TO_JSON(STRUCT('store', store_name, 'id', CAST(store_id AS STRING))) as json_representation,

    product_ids,
    created_at,
    revenue
  FROM array_operations
),

-- Test mathematical and statistical functions
math_operations AS (
  SELECT
    store_id,
    store_name,
    revenue,

    -- Basic math functions
    ABS(-revenue) as abs_revenue,
    ROUND(revenue, 2) as rounded_revenue,
    FLOOR(revenue) as floored_revenue,
    CEIL(revenue) as ceiling_revenue,
    SQRT(revenue) as sqrt_revenue,
    POWER(revenue, 0.5) as power_half,
    LN(revenue) as natural_log,
    LOG(10, revenue) as log_base_10,
    EXP(1) as euler_number,

    -- Trigonometric functions
    SIN(revenue / 1000) as sine_value,
    COS(revenue / 1000) as cosine_value,
    TAN(revenue / 1000) as tangent_value,

    -- Statistical window functions
    SUM(revenue) OVER (ORDER BY store_id ROWS UNBOUNDED PRECEDING) as running_total,
    AVG(revenue) OVER (PARTITION BY EXTRACT(MONTH FROM created_at) ORDER BY store_id) as monthly_avg,
    COUNT(*) OVER (ORDER BY revenue DESC ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) as count_window,
    MIN(revenue) OVER (PARTITION BY EXTRACT(YEAR FROM created_at)) as yearly_min,
    MAX(revenue) OVER (PARTITION BY EXTRACT(YEAR FROM created_at)) as yearly_max,

    -- Ranking functions
    ROW_NUMBER() OVER (ORDER BY revenue DESC) as row_num,
    RANK() OVER (ORDER BY revenue DESC) as revenue_rank,
    DENSE_RANK() OVER (ORDER BY revenue DESC) as dense_rank,
    PERCENT_RANK() OVER (ORDER BY revenue) as percent_rank,
    NTILE(4) OVER (ORDER BY revenue) as quartile,

    -- Lead/Lag functions
    LAG(revenue, 1, 0) OVER (ORDER BY created_at) as prev_revenue,
    LEAD(revenue, 1, 0) OVER (ORDER BY created_at) as next_revenue,
    FIRST_VALUE(revenue) OVER (PARTITION BY EXTRACT(MONTH FROM created_at) ORDER BY created_at) as first_monthly_revenue,
    LAST_VALUE(revenue) OVER (PARTITION BY EXTRACT(MONTH FROM created_at) ORDER BY created_at ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as last_monthly_revenue,

    created_at,
    product_ids
  FROM string_operations
),

-- Test type casting and conversion functions (E6 CAST_SUPPORTED_TYPE_MAPPING)
type_conversions AS (
  SELECT
    store_id,
    store_name,
    revenue,
    created_at,

    -- Test various CAST operations that use E6's TYPE_MAPPING
    CAST(store_id AS VARCHAR(10)) as id_as_string,
    CAST(store_id AS BIGINT) as id_as_bigint,
    CAST(store_id AS INT) as id_as_int,
    CAST(store_id AS BOOLEAN) as id_as_boolean,
    CAST(revenue AS DECIMAL(10,2)) as revenue_decimal,
    CAST(revenue AS FLOAT) as revenue_float,
    CAST(revenue AS DOUBLE) as revenue_double,
    CAST('2023-01-01' AS DATE) as string_as_date,
    CAST(created_at AS DATE) as timestamp_as_date,
    CAST(created_at AS TIMESTAMP) as preserved_timestamp,

    -- TRY_CAST for safe conversions
    TRY_CAST('invalid_number' AS INT) as safe_cast_null,
    TRY_CAST('123' AS INT) as safe_cast_success,

    -- Test interval casting (E6 has special double_colon_interval_sql)
    created_at + INTERVAL '1 day' as plus_one_day,
    created_at + INTERVAL '2 hours' as plus_two_hours,
    created_at + INTERVAL '30 minutes' as plus_thirty_minutes,

    product_ids
  FROM math_operations
),

-- Test conditional functions and null handling
conditional_operations AS (
  SELECT
    store_id,
    store_name,
    revenue,
    is_active,

    -- CASE expressions
    CASE
      WHEN revenue > 3000 THEN 'High Revenue'
      WHEN revenue > 2000 THEN 'Medium Revenue'
      WHEN revenue > 1000 THEN 'Low Revenue'
      ELSE 'Very Low Revenue'
    END as revenue_category,

    CASE is_active
      WHEN TRUE THEN 'Active Store'
      WHEN FALSE THEN 'Inactive Store'
      ELSE 'Unknown Status'
    END as activity_status,

    -- Null handling functions (E6 supports NVL2)
    COALESCE(is_active, FALSE) as coalesced_active,
    NVL(is_active, FALSE) as nvl_active,
    NVL2(is_active, 'Has Value', 'Is Null') as nvl2_result,
    ISNULL(is_active) as is_null_check,
    ISNOTNULL(is_active) as is_not_null_check,
    NULLIF(revenue, 0) as nullif_zero,

    -- IF function
    IF(revenue > 2000, 'High', 'Low') as if_high_low,

    -- Greatest/Least (E6 transforms to MAX_OR_GREATEST/MIN_OR_LEAST)
    GREATEST(revenue, 1000, 500) as max_value,
    LEAST(revenue, 5000, 10000) as min_value,

    created_at,
    product_ids
  FROM type_conversions
),

-- Test aggregation functions including E6-specific transforms
aggregation_functions AS (
  SELECT
    EXTRACT(MONTH FROM created_at) as month_num,
    COUNT(*) as store_count,
    COUNT(DISTINCT store_name) as unique_stores,

    -- Basic aggregations
    SUM(revenue) as total_revenue,
    AVG(revenue) as avg_revenue,
    MIN(revenue) as min_revenue,
    MAX(revenue) as max_revenue,

    -- Statistical functions
    STDDEV(revenue) as revenue_stddev,
    VARIANCE(revenue) as revenue_variance,
    STDDEV_POP(revenue) as pop_stddev,
    VAR_POP(revenue) as pop_variance,

    -- E6 transforms these functions
    APPROX_COUNT_DISTINCT(store_name) as approx_distinct_stores,
    APPROX_PERCENTILE(revenue, 0.5) as median_revenue,
    ARBITRARY(store_name) as any_store_name,
    MAX_BY(store_name, revenue) as highest_revenue_store,
    MIN_BY(store_name, revenue) as lowest_revenue_store,

    -- Array aggregation
    ARRAY_AGG(store_name ORDER BY revenue DESC) as stores_by_revenue,

    -- Collect functions
    COLLECT_LIST(store_name) as collected_names,
    COLLECT_SET(EXTRACT(DAY FROM created_at)) as unique_days,

    -- Boolean aggregations
    BOOL_AND(COALESCE(is_active, FALSE)) as all_active,
    BOOL_OR(COALESCE(is_active, FALSE)) as any_active,

    -- String aggregation
    STRING_AGG(store_name, ', ' ORDER BY store_id) as concatenated_names,
    LISTAGG(store_name, '|') WITHIN GROUP (ORDER BY revenue DESC) as pipe_separated_names

  FROM conditional_operations
  GROUP BY EXTRACT(MONTH FROM created_at)
),

-- Test JSON functions (E6 supports JSON type)
json_operations AS (
  SELECT
    month_num,
    store_count,
    total_revenue,

    -- JSON construction
    TO_JSON(STRUCT(month_num, store_count, total_revenue)) as month_stats_json,
    JSON_OBJECT('month', month_num, 'stores', store_count, 'revenue', total_revenue) as json_obj,
    JSON_ARRAY(month_num, store_count, total_revenue) as json_arr,

    -- JSON extraction (if supported)
    JSON_EXTRACT('{"month": 1, "revenue": 1500}', '$.month') as extracted_month,
    JSON_EXTRACT_SCALAR('{"store": "store_a"}', '$.store') as extracted_store,

    stores_by_revenue
  FROM aggregation_functions
),

-- Test complex data types: STRUCT, ARRAY, MAP
complex_types AS (
  SELECT
    month_num,

    -- STRUCT operations (E6 supports STRUCT type)
    STRUCT(month_num, store_count, total_revenue) as month_summary,
    STRUCT(
      month_num as month,
      total_revenue as revenue,
      ARRAY[store_count, CAST(total_revenue AS INT)] as metrics
    ) as complex_struct,

    -- Nested arrays
    ARRAY[
      STRUCT(month_num, total_revenue),
      STRUCT(month_num + 1, total_revenue * 1.1)
    ] as forecast_array,

    stores_by_revenue,
    store_count,
    total_revenue
  FROM json_operations
)

-- Final SELECT with all E6 generator features
SELECT
  month_num,
  store_count,
  FORMAT_NUMBER(total_revenue, 2) as formatted_revenue,

  -- URL and encoding functions (if supported by E6)
  BASE64(CAST(month_summary AS STRING)) as base64_encoded,
  MD5(CAST(month_num AS STRING)) as month_hash,
  SHA1(CAST(total_revenue AS STRING)) as revenue_hash,

  -- Type inspection functions
  TYPEOF(complex_struct) as struct_type,

  -- Complex expressions combining multiple features
  CASE
    WHEN total_revenue > 5000 THEN
      CONCAT('Hot Month ', CAST(month_num AS STRING), ' with $', FORMAT_NUMBER(total_revenue, 0))
    WHEN total_revenue > 3000 THEN
      CONCAT('Good Month ', CAST(month_num AS STRING), ' with $', FORMAT_NUMBER(total_revenue, 0))
    ELSE
      CONCAT('Regular Month ', CAST(month_num AS STRING), ' with $', FORMAT_NUMBER(total_revenue, 0))
  END as performance_summary,

  -- Window functions with complex expressions
  LAG(total_revenue, 1, 0) OVER (ORDER BY month_num) as prev_month_revenue,
  (total_revenue - LAG(total_revenue, 1, 0) OVER (ORDER BY month_num)) /
    NULLIF(LAG(total_revenue, 1, 0) OVER (ORDER BY month_num), 0) * 100 as growth_percentage,

  -- Array and struct access
  SIZE(stores_by_revenue) as num_stores_in_array,

  -- Final complex computation
  ROUND(
    POWER(
      total_revenue /
      GREATEST(
        AVG(total_revenue) OVER (),
        1
      ),
      0.5
    ) * 100,
    2
  ) as performance_index,

  -- Current timestamp for report generation
  CURRENT_TIMESTAMP() as report_generated_at,

  -- All complex data for final output
  month_summary,
  complex_struct,
  forecast_array,
  stores_by_revenue

FROM complex_types
ORDER BY month_num
LIMIT 100;