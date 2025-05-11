FROM openpolicyagent/opa:latest

COPY ./policies/rbac.rego /policies/rbac.rego

CMD ["run", "--server", "--log-level=debug", "/policies"]
