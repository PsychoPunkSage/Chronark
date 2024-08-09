import datetime
import jwt

print(jwt.__file__)


SECRET_KEY = 'your_super_complex_secret_key_here'

payload = {
    'user': 'test_user',
    'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
}

# token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
token = jwt.encode({
                'user': "AP",
                'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
            }, 'SECRET_KEY', algorithm='HS256')
print(token)