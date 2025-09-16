from locust import HttpUser, task, between

# TPC-DS query for load testing
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

class SqlConverterUser(HttpUser):
    wait_time = between(1, 2)  # Wait 1-2 seconds between requests
    
    def on_start(self):
        """Called when a simulated user starts"""
        # Test health endpoint on start
        self.client.get("/health")
    
    @task  # Single task focusing on TPC-DS query
    def convert_tpcds_query(self):
        """Test TPC-DS query transpilation"""
        form_data = {
            "query": TPCDS_QUERY,
            "from_sql": "databricks",
            "to_sql": "e6"
        }
        # Use catch_response=True to manually handle the response
        with self.client.post(
            "/convert-query", 
            data=form_data, 
            name="/convert-query-tpcds",
            catch_response=True  # Enable manual response handling
        ) as response:
            # Manually mark success or failure based on status code
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got non-200 status code: {response.status_code}")
    
