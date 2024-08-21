import os
from pymongo import MongoClient

AUTH_MONGO_DB_HOST = "localhost"
AUTH_MONGO_DB_PORT = 27018
AUTH_MONGO_DB_USERNAME = "mongoauthentication"
AUTH_MONGO_DB_PASSWORD = "authinfo"

mongo_client = MongoClient(
    username=AUTH_MONGO_DB_USERNAME, 
    password=AUTH_MONGO_DB_PASSWORD, 
    host=AUTH_MONGO_DB_HOST, 
    port=int(AUTH_MONGO_DB_PORT)
)
db = mongo_client.auth_db
users_collection = db.users

def test_mongo_connection():
    try:
        # Step 1: Insert a test document into the `users_collection`
        test_user = {
            "username": "test_user",
            "email": "test_user@example.com",
            "password": "password123"
        }
        insert_result = users_collection.insert_one(test_user)
        print(f"Inserted document ID: {insert_result.inserted_id}")

        # Step 2: Retrieve the inserted document
        retrieved_user = users_collection.find_one({"username": "test_user"})
        if retrieved_user:
            print(f"Retrieved User: {retrieved_user}")
        else:
            return "Error: Test user not found in the collection."

        # Step 3: Delete the inserted document
        delete_result = users_collection.delete_one({"username": "test_user"})
        if delete_result.deleted_count == 1:
            print("Test user successfully deleted.")
        else:
            return "Error: Test user could not be deleted."

        return "MongoDB connection test passed successfully!"

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return "MongoDB connection test failed."
    
print("========AUTHENTICATION========")
print(f"{AUTH_MONGO_DB_HOST}:{AUTH_MONGO_DB_PORT}")
print(f"{AUTH_MONGO_DB_USERNAME}:{AUTH_MONGO_DB_PASSWORD}")
print(test_mongo_connection())