"""Good mini-repo: the same agent, instrumented with OpenTelemetry tracing."""
from openai import OpenAI
from opentelemetry import trace
from opentelemetry.instrumentation.openai import OpenAIInstrumentor

OpenAIInstrumentor().instrument()
tracer = trace.get_tracer(__name__)
client = OpenAI()


def answer(q: str) -> str:
    with tracer.start_as_current_span("answer"):
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": q}],
            timeout=10,
            max_tokens=256,
        )
    return resp.choices[0].message.content
