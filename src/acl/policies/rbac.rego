package rbac

# Define roles and their permissions
roles = {
  "admin": ["create", "read", "update", "delete"],
  "user": ["read"],
  "manager": ["read", "update"]
}

# Define policies
default allow = false

# Rule to allow access if the user has permission
allow {
  roles[input.role][_] == input.action
}
