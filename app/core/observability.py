import logging
import json
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict
import logging_loki
from prometheus_client import Counter, Histogram
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from app.core.config import settings

# Create logs directory
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_object = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if hasattr(record, "request_id"):
            log_object["request_id"] = record.request_id
        
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
        
        if hasattr(record, "extra_data"):
            log_object.update(record.extra_data)
        
        return json.dumps(log_object)

def setup_logging():
    """Configure logging with JSON formatting and Loki integration."""
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)
    
    # JSON formatted console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JsonFormatter())
    root_logger.addHandler(console_handler)
    
    # JSON formatted file handler with rotation
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(JsonFormatter())
    root_logger.addHandler(file_handler)
    
    # Loki handler configuration
    loki_handler = logging_loki.LokiHandler(
        url="http://localhost:3100/loki/api/v1/push",
        tags={"app": "gigachat"},
        version="1"
    )
    loki_handler.setFormatter(JsonFormatter())
    root_logger.addHandler(loki_handler)

def setup_tracing():
    """Configure OpenTelemetry tracing."""
    # Create and set tracer provider
    tracer_provider = TracerProvider(
        resource=Resource.create({"service.name": "gigachat"})
    )
    
    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://localhost:4318/v1/traces"
    )
    
    # Add span processor to the tracer provider
    tracer_provider.add_span_processor(
        BatchSpanProcessor(otlp_exporter)
    )
    
    # Set the tracer provider
    trace.set_tracer_provider(tracer_provider)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

CHAT_MESSAGES = Counter(
    "chat_messages_total",
    "Total chat messages",
    ["role", "model"]
)

MODEL_LATENCY = Histogram(
    "model_inference_duration_seconds",
    "Model inference latency",
    ["model"]
)

ERROR_COUNT = Counter(
    "error_count_total",
    "Total error count",
    ["type", "location"]
)

def log_request_metrics(
    method: str,
    endpoint: str,
    status: int,
    duration: float
):
    """Log request metrics to Prometheus."""
    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        status=status
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)

def log_chat_metrics(
    role: str,
    model: str,
    inference_time: float = None
):
    """Log chat-related metrics to Prometheus."""
    CHAT_MESSAGES.labels(
        role=role,
        model=model
    ).inc()
    
    if inference_time is not None:
        MODEL_LATENCY.labels(
            model=model
        ).observe(inference_time)

def log_error(
    error_type: str,
    location: str,
    error: Exception
):
    """Log error metrics and details."""
    ERROR_COUNT.labels(
        type=error_type,
        location=location
    ).inc()
    
    logging.error(
        f"Error in {location}: {str(error)}",
        exc_info=True,
        extra={
            "error_type": error_type,
            "location": location
        }
    )