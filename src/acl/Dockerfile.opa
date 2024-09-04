FROM openpolicyagent/opa:latest

COPY ./policies /policies

CMD ["run", "--server", "--log-level=debug", "/policies"]
