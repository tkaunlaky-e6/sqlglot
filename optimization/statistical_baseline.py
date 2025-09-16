#!/usr/bin/env python3
"""
Proper Statistical Baseline for TPC-DS Query
Handles outliers, warm-up, and provides robust statistics
"""

import requests
import time
import numpy as np
from scipy import stats
import json

class RobustBaseline:
    def __init__(self, url="http://localhost:8100/convert-query"):
        self.url = url
        self.session = requests.Session()  # Connection pooling
        self.tpcds_query = """SELECT s.s_store_name, s.s_store_id, 
            SUM(CASE WHEN d.d_day_name = 'Sunday' THEN ss.ss_sales_price ELSE 0 END) AS sunday_sales,
            SUM(CASE WHEN d.d_day_name = 'Monday' THEN ss.ss_sales_price ELSE 0 END) AS monday_sales,
            SUM(CASE WHEN d.d_day_name NOT IN ('Sunday', 'Monday') THEN ss.ss_sales_price ELSE 0 END) AS other_weekday_sales
            FROM store_sales ss
            JOIN date_dim d ON ss.ss_sold_date_sk = d.d_date_sk
            JOIN store s ON ss.ss_store_sk = s.s_store_sk
            WHERE d.d_year = 2001
            GROUP BY s.s_store_name, s.s_store_id
            ORDER BY s.s_store_name, s.s_store_id"""
    
    def run_request(self):
        """Single request with timing"""
        start = time.perf_counter()
        response = self.session.post(self.url, data={
            "query": self.tpcds_query,
            "from_sql": "databricks",
            "to_sql": "e6"
        })
        elapsed = (time.perf_counter() - start) * 1000  # ms
        return elapsed, response.status_code
    
    def warmup(self, iterations=30):
        """Warm-up phase to stabilize JIT and caches"""
        print(f"Warm-up phase ({iterations} requests)...")
        for i in range(iterations):
            self.run_request()
            if (i + 1) % 10 == 0:
                print(f"  Warm-up: {i + 1}/{iterations}")
    
    def collect_samples(self, n=100):
        """Collect timing samples"""
        print(f"\nCollecting {n} samples...")
        times = []
        errors = 0
        
        for i in range(n):
            elapsed, status = self.run_request()
            if status == 200:
                times.append(elapsed)
            else:
                errors += 1
            
            if (i + 1) % 20 == 0:
                print(f"  Progress: {i + 1}/{n}")
        
        if errors > 0:
            print(f"  Warning: {errors} requests failed")
        
        return np.array(times)
    
    def remove_outliers(self, data, method="iqr"):
        """Remove outliers using various methods"""
        if method == "iqr":
            # Tukey's method
            Q1 = np.percentile(data, 25)
            Q3 = np.percentile(data, 75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            mask = (data >= lower) & (data <= upper)
        
        elif method == "zscore":
            # Z-score method
            z_scores = np.abs(stats.zscore(data))
            mask = z_scores < 2.5
        
        elif method == "mad":
            # Median Absolute Deviation
            median = np.median(data)
            mad = np.median(np.abs(data - median))
            modified_z = 0.6745 * (data - median) / mad
            mask = np.abs(modified_z) < 3.5
        
        filtered = data[mask]
        outliers = len(data) - len(filtered)
        return filtered, outliers
    
    def calculate_statistics(self, data):
        """Calculate robust statistics"""
        return {
            "n": len(data),
            "mean": np.mean(data),
            "median": np.median(data),
            "std": np.std(data),
            "mad": stats.median_abs_deviation(data),
            "min": np.min(data),
            "max": np.max(data),
            "p25": np.percentile(data, 25),
            "p50": np.percentile(data, 50),
            "p75": np.percentile(data, 75),
            "p90": np.percentile(data, 90),
            "p95": np.percentile(data, 95),
            "p99": np.percentile(data, 99),
            "iqr": np.percentile(data, 75) - np.percentile(data, 25),
            "cv": (np.std(data) / np.mean(data)) * 100  # Coefficient of variation
        }
    
    def run_baseline(self):
        """Complete baseline analysis"""
        print("="*60)
        print("STATISTICAL BASELINE ANALYSIS")
        print("="*60)
        
        # Warm-up
        self.warmup()
        
        # Collect samples
        raw_times = self.collect_samples(100)
        
        # Calculate raw statistics
        print("\n--- RAW DATA STATISTICS ---")
        raw_stats = self.calculate_statistics(raw_times)
        self.print_stats(raw_stats)
        
        # Remove outliers using multiple methods
        print("\n--- OUTLIER REMOVAL ---")
        
        # IQR method
        iqr_filtered, iqr_outliers = self.remove_outliers(raw_times, "iqr")
        print(f"IQR method: Removed {iqr_outliers} outliers")
        
        # MAD method
        mad_filtered, mad_outliers = self.remove_outliers(raw_times, "mad")
        print(f"MAD method: Removed {mad_outliers} outliers")
        
        # Z-score method
        z_filtered, z_outliers = self.remove_outliers(raw_times, "zscore")
        print(f"Z-score method: Removed {z_outliers} outliers")
        
        # Use MAD method (most robust)
        clean_times = mad_filtered
        
        # Calculate clean statistics
        print("\n--- CLEAN DATA STATISTICS (MAD filtered) ---")
        clean_stats = self.calculate_statistics(clean_times)
        self.print_stats(clean_stats)
        
        # Interpretation
        print("\n--- INTERPRETATION ---")
        self.interpret_results(clean_stats)
        
        # Final baseline recommendation
        print("\n--- RECOMMENDED BASELINE ---")
        print(f"Use Median: {clean_stats['median']:.2f} ms")
        print(f"Normal range: {clean_stats['median'] - clean_stats['mad']*2:.2f} - {clean_stats['median'] + clean_stats['mad']*2:.2f} ms")
        print(f"Performance SLA (P95): < {clean_stats['p95']:.2f} ms")
        
        return clean_stats
    
    def print_stats(self, stats):
        """Pretty print statistics"""
        print(f"Samples: {stats['n']}")
        print(f"Mean: {stats['mean']:.2f} ms")
        print(f"Median: {stats['median']:.2f} ms")
        print(f"Std Dev: {stats['std']:.2f} ms")
        print(f"MAD: {stats['mad']:.2f} ms")
        print(f"Min: {stats['min']:.2f} ms")
        print(f"Max: {stats['max']:.2f} ms")
        print(f"P25: {stats['p25']:.2f} ms")
        print(f"P50: {stats['p50']:.2f} ms")
        print(f"P75: {stats['p75']:.2f} ms")
        print(f"P90: {stats['p90']:.2f} ms")
        print(f"P95: {stats['p95']:.2f} ms")
        print(f"P99: {stats['p99']:.2f} ms")
        print(f"IQR: {stats['iqr']:.2f} ms")
        print(f"CV: {stats['cv']:.1f}%")
    
    def interpret_results(self, stats):
        """Interpret statistical results"""
        cv = stats['cv']
        if cv < 10:
            print(f"✓ Excellent stability (CV={cv:.1f}%)")
        elif cv < 20:
            print(f"✓ Good stability (CV={cv:.1f}%)")
        elif cv < 30:
            print(f"⚠ Moderate stability (CV={cv:.1f}%)")
        else:
            print(f"✗ Poor stability (CV={cv:.1f}%) - investigate system")
        
        # Check for skewness
        skew = (stats['mean'] - stats['median']) / stats['std']
        if abs(skew) < 0.5:
            print("✓ Distribution is approximately symmetric")
        elif skew > 0.5:
            print("⚠ Distribution is right-skewed (occasional slow requests)")
        else:
            print("⚠ Distribution is left-skewed (unusual)")
        
        # Performance assessment
        if stats['p95'] < stats['median'] * 1.5:
            print("✓ Consistent performance (P95 < 1.5x median)")
        else:
            print("⚠ Variable performance (P95 > 1.5x median)")

if __name__ == "__main__":
    baseline = RobustBaseline()
    stats = baseline.run_baseline()
    
    # Save results
    with open("baseline_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    print("\nResults saved to baseline_stats.json")