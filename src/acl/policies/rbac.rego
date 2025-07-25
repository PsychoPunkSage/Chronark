package authz

default allow = false

roles = {
    "admin": {"all-activity": ["GET"]},
    "user": {"activity": ["GET"]}
}

allow if {
    role := input.roles[_]
    permissions := roles[role]
    methods := permissions[input.path]
    input.method == methods[_]
}
