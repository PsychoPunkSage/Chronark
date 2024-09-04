package authz

default allow = false

roles = {
    "admin": {"all-activity": ["GET"]},
    "user": {"home": ["GET"], "payments": ["GET"], "creditCard": ["GET"], "activity": ["GET"]}
}

allow {
    role := input.roles[_]
    permissions := roles[role]
    methods := permissions[input.path]
    input.method == methods[_]
}
