## Commands

#### 1. Login (save cookie using `--cookie-jar`)

```sh
curl -X POST http://localhost:4001/login \
-d "username=user1&password=user1" \
--cookie-jar cookies.txt
```
* `cookie.txt` will be created which will be used to interact with protected-routes.

#### 2. Access Protected routes:

```sh
curl -L http://localhost:4001/activity --cookie cookies.txt
# Get html code

curl -L http://localhost:4001 --cookie cookies.txt | grep About
#   % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
#                                  Dload  Upload   Total   Spent    Left  Speed
# 100 11286  100 11286    0     0   686    <h2 class="text-center mt-2">About 4001</h2>
# k      0 --:--:-- --:--:-- --:--:--  688k
#           <h5 class="text-uppercase">About Us</h5>
#               <a href="/about" class="text-light">About</a>
```

```sh
curl -L http://localhost:4001/all-activity --cookie cookies.txt
# Unauthorized
```


#### 3. Logout:

```sh
curl -L http://localhost:4001/logout --cookie cookies.txt --cookie-jar cookies.txt
# HTML of Login Page
```
* `--cookie cookies.txt` sends the session cookies so the server knows which session to clear.
* `--cookie-jar cookies.txt` saves any changes to the cookies (e.g., if the server invalidates the session).

#### 4. Try access after Logout (wo logging in):

```sh
curl -L http://localhost:4001 --cookie cookies.txt
# HTML of Login Page
```

