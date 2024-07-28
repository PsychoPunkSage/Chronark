from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
# from opentelemetry.instrumentation.pymongo import PymongoInstrumentor

# import redis
# import pymongo

def setup_tracer(service_name: str, jaeger_host: str, jaeger_port: int):
    # Configure the tracer
    trace.set_tracer_provider(
        TracerProvider(
            resource=Resource.create({SERVICE_NAME: service_name})
        )
    )

    # Configure the Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name=jaeger_host,
        agent_port=jaeger_port,
    )

    # Configure the span processor to use the Jaeger exporter
    span_processor = BatchSpanProcessor(jaeger_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)

    return trace.get_tracer(__name__)

def instrument_app(app):
    # Instrument Flask application
    FlaskInstrumentor().instrument_app(app)
    
    # Instrument Redis
    RedisInstrumentor().instrument()
    
    # Instrument MongoDB
    # PymongoInstrumentor().instrument()