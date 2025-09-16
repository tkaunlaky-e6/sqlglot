# profiling_middleware.py
import time
import cProfile
import pstats
from pyinstrument import Profiler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

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
            report_filename = f"optimization/profiling/profile_report_{timestamp}.html"
            
            with open(report_filename, "w", encoding="utf-8") as f:
                f.write(profiler.output_html())
            
            print(f"🚀 Profiling report saved to: {report_filename}")

            return response
        else:
            # If not profiling, just process the request normally
            return await call_next(request)