from locust import HttpUser, task, between
import json
import time
import psutil
import docker
import sqlglot
import cProfile
import re
import os
import pstats
from datetime import datetime
import threading
import hashlib

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

# Load comprehensive query from file
with open('/Users/tanaykulkarni/Documents/e6-data-sqlglot/sqlglot/optimization/comprehensive_test_query.sql', 'r') as f:
    COMPREHENSIVE_E6_QUERY = f.read()

# Global stats tracking
docker_stats_history = []
conversion_times = []

# Create timestamped profiling directory
PROFILE_DIR = f"/Users/tanaykulkarni/Documents/e6-data-sqlglot/sqlglot/optimization/profiling_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
os.makedirs(PROFILE_DIR, exist_ok=True)
print(f"Profiling data will be saved to: {PROFILE_DIR}")

# Profiling interval (30 seconds)
PROFILE_INTERVAL = 30
last_profile_time = time.time()

class SqlConverterUser(HttpUser):
    wait_time = between(0, 0)  # No wait time for maximum throughput testing

    def on_start(self):
        """Called when a simulated user starts"""
        # Test health endpoint on start
        self.client.get("/health")

        # Track start time for 5-minute test
        self.test_start_time = time.time()

        # Initialize Docker monitoring for port 8100
        try:
            self.docker_client = docker.from_env()
            self.container = None
            for container in self.docker_client.containers.list():
                # More precise port detection for 8100
                ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                if '8100/tcp' in ports and ports['8100/tcp']:
                    self.container = container
                    print(f"Monitoring container: {container.name} (ID: {container.short_id})")
                    break
        except Exception as e:
            print(f"Docker monitoring setup failed: {e}")
            self.container = None

    @task  # Comprehensive E6 generator stress test
    def convert_comprehensive_query(self):
        """Test comprehensive E6 generator features - exercises all dialect transformations"""
        form_data = {
            "query": COMPREHENSIVE_E6_QUERY,
            "from_sql": "databricks",
            "to_sql": "e6"
        }
        # Use catch_response=True to manually handle the response
        # Check if profiling should be triggered using existing middleware
        url = "/convert-query?profile=true" if getattr(self, 'should_profile_next', False) else "/convert-query"
        if hasattr(self, 'should_profile_next'):
            delattr(self, 'should_profile_next')  # Reset flag after use

        with self.client.post(
            url,
            data=form_data,
            name="/convert-query-comprehensive-e6",
            catch_response=True  # Enable manual response handling
        ) as response:
            # Validate both HTTP status and actual conversion success
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    converted_query = response_data.get('converted_query', '')

                    # ASSERTION-BASED VALIDATION: Check for successful transpilation
                    try:
                        # Assert we have a successful conversion (not an error)
                        assert "converted_query" in response_data, "Response missing 'converted_query' key"
                        assert "detail" not in response_data, f"API returned error: {response_data.get('detail', 'Unknown error')}"

                        # Assert the conversion is substantial (comprehensive query should be large)
                        assert len(converted_query) > 10000, f"Converted query too short: {len(converted_query)} chars (expected >10000)"

                        # Assert essential SQL structure exists
                        assert "SELECT" in converted_query.upper(), "Missing SELECT statement"
                        assert "FROM" in converted_query.upper(), "Missing FROM clause"
                        assert "WITH" in converted_query.upper(), "Missing WITH clause"

                        # Assert E6-specific transformations occurred
                        e6_transformations = [
                            "ARRAY_AGG",           # E6 array function
                            "DATE_TRUNC",          # E6 date function
                            "NAMED_STRUCT",        # E6 struct function
                            "ARRAY_SLICE",         # E6 array slicing
                            "DATE_DIFF",           # E6 date difference
                            "TO_UNIX_TIMESTAMP"    # E6 timestamp function
                        ]

                        found_transformations = [t for t in e6_transformations if t in converted_query.upper()]
                        assert len(found_transformations) >= 3, f"Insufficient E6 transformations. Found: {found_transformations}"

                        # All assertions passed - mark as successful
                        response.success()

                        # Collect Docker stats and profiling
                        docker_stats = self._collect_docker_stats()
                        self._check_profiling_interval()

                        # Track conversion metrics with memory management
                        conversion_time = response.elapsed.total_seconds()
                        conversion_times.append(conversion_time)

                        # Keep only last 1000 conversion times for memory efficiency
                        if len(conversion_times) > 1000:
                            conversion_times.pop(0)

                        # Enhanced logging with Docker stats
                        elapsed_mins = (time.time() - self.test_start_time) / 60
                        stats_msg = ""
                        if docker_stats:
                            stats_msg = f" | CPU: {docker_stats['cpu_percent']}% | Mem: {docker_stats['memory_mb']}MB"

                        print(f"✅ E6 conversion [{elapsed_mins:.1f}min]: {len(converted_query)} chars | {conversion_time:.3f}s{stats_msg} | E6 features: {len(found_transformations)}")

                        # Print summary every minute based on actual time
                        if not hasattr(self, 'last_summary_time'):
                            self.last_summary_time = time.time()
                        elif time.time() - self.last_summary_time >= 60:  # Every 60 seconds
                            self._print_performance_summary()
                            self.last_summary_time = time.time()

                    except AssertionError as e:
                        response.failure(f"Transpilation assertion failed: {str(e)}")
                        print(f"❌ Assertion failed: {str(e)}")

                    except Exception as e:
                        response.failure(f"Unexpected validation error: {str(e)}")
                        print(f"❌ Validation error: {str(e)}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
                except Exception as e:
                    response.failure(f"Response validation error: {str(e)}")
            else:
                response.failure(f"Got non-200 status code: {response.status_code}")

    def _collect_docker_stats(self):
        """Collect Docker container stats using docker stats command for accuracy"""
        if not self.container:
            return None

        try:
            # Get Docker stats with CPU calculation
            stats = self.container.stats(stream=False)

            # Memory calculation
            memory_usage = stats['memory_stats']['usage']
            memory_mb = memory_usage / (1024 * 1024)

            # CPU calculation with error handling
            cpu_percent = 0
            try:
                cpu_stats = stats['cpu_stats']
                precpu_stats = stats['precpu_stats']

                cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
                system_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']

                if system_delta > 0 and cpu_delta >= 0:
                    num_cpus = len(cpu_stats['cpu_usage'].get('percpu_usage', [1]))
                    if num_cpus == 0:
                        num_cpus = 1
                    cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
                    cpu_percent = min(cpu_percent, 100.0)  # Cap at 100%
            except:
                cpu_percent = 0

            current_stats = {
                'timestamp': time.time(),
                'cpu_percent': round(cpu_percent, 2),
                'memory_mb': round(memory_mb, 2)
            }

            # Add to global history with time-based cleanup
            global docker_stats_history
            docker_stats_history.append(current_stats)
            cutoff_time = time.time() - 300  # 5 minutes
            docker_stats_history = [s for s in docker_stats_history if s['timestamp'] > cutoff_time]

            return current_stats

        except Exception as e:
            return None

    def _print_performance_summary(self):
        """Print 5-minute test performance summary"""
        if not docker_stats_history or not conversion_times:
            return

        # Docker stats analysis
        cpu_values = [s['cpu_percent'] for s in docker_stats_history]
        memory_values = [s['memory_mb'] for s in docker_stats_history]

        # Conversion time analysis
        avg_conversion = sum(conversion_times) / len(conversion_times)
        peak_conversion = max(conversion_times)
        optimal_conversion = min(conversion_times)

        elapsed_mins = (time.time() - self.test_start_time) / 60

        print(f"\n📊 PERFORMANCE SUMMARY [{elapsed_mins:.1f}min elapsed]")
        print(f"   Docker CPU  - Peak: {max(cpu_values):.1f}% | Avg: {sum(cpu_values)/len(cpu_values):.1f}% | Optimal: {min(cpu_values):.1f}%")
        print(f"   Docker Mem  - Peak: {max(memory_values):.0f}MB | Avg: {sum(memory_values)/len(memory_values):.0f}MB | Optimal: {min(memory_values):.0f}MB")
        print(f"   Conversions - Peak: {peak_conversion:.3f}s | Avg: {avg_conversion:.3f}s | Optimal: {optimal_conversion:.3f}s | Total: {len(conversion_times)}")
        print(f"   Throughput  - {len(conversion_times)/elapsed_mins:.1f} conversions/min\n")

    def _check_profiling_interval(self):
        """Check if it's time to trigger profiling using existing middleware"""
        global last_profile_time
        current_time = time.time()

        if current_time - last_profile_time >= PROFILE_INTERVAL:
            # Set flag to trigger profiling on next request using existing middleware
            self.should_profile_next = True
            last_profile_time = current_time
            print(f"📊 Profiling scheduled for next request (HTML report will be saved)")

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
    
