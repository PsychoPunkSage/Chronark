## Load Testing

### Fields for User creation

```json
{
    "username": f"user{i}",
    "password": f"user{i}",
    "name": f"User {i}",
    "email": f"user{i}@example.com",
    "contact": f"+91 98765432{i:02d}",
    "address": f"{i}00 Main St, Anytown, AnyState"
}
```

### Load testing

> Register X-users

```sh
./load.sh --load X
# X => no. of user to register.
```

> Remove users

```sh
./load.sh --load username1 username2 username1 .....
# Ensure whitespace seperated usernames.
```