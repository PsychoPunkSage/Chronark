import os
from pymongo import MongoClient

AUTH_MONGO_DB_HOST = "localhost"
AUTH_MONGO_DB_PORT = 27025
AUTH_MONGO_DB_USERNAME = "mongocusactivity"
AUTH_MONGO_DB_PASSWORD = "customeractivity"

mongo_client = MongoClient(
    username=AUTH_MONGO_DB_USERNAME, 
    password=AUTH_MONGO_DB_PASSWORD, 
    host=AUTH_MONGO_DB_HOST, 
    port=int(AUTH_MONGO_DB_PORT)
)

# db = mongo_client.auth_db
# users_collection = db.users

# def test_mongo_connection():
#     try:
#         # Step 1: Insert a test document into the `users_collection`
#         test_user = {
#             "username": "test_user",
#             "email": "test_user@example.com",
#             "password": "password123"
#         }
#         insert_result = users_collection.insert_one(test_user)
#         print(f"Inserted document ID: {insert_result.inserted_id}")

#         # Step 2: Retrieve the inserted document
#         retrieved_user = users_collection.find_one({"username": "test_user"})
#         if retrieved_user:
#             print(f"Retrieved User: {retrieved_user}")
#         else:
#             return "Error: Test user not found in the collection."

#         # Step 3: Delete the inserted document
#         delete_result = users_collection.delete_one({"username": "test_user"})
#         if delete_result.deleted_count == 1:
#             print("Test user successfully deleted.")
#         else:
#             return "Error: Test user could not be deleted."

#         return "MongoDB connection test passed successfully!"

#     except Exception as e:
#         print(f"An error occurred: {str(e)}")
#         return "MongoDB connection test failed."
    

def retrieve_all_data_from_all_databases():
    try:
        # Step 1: List all databases
        databases = mongo_client.list_database_names()
        print(f"Databases found: {databases}")

        # Step 2: Iterate over all databases
        for db_name in databases:
            if db_name == "info":
                print(f"Accessing Database: {db_name}")
                database = mongo_client[db_name]
                
                # Step 3: List all collections in the current database
                collections = database.list_collection_names()
                print(f"Collections in {db_name}: {collections}")
    
                # Step 4: Iterate over all collections in the current database
                for collection_name in collections:
                    collection = database[collection_name]
                    
                    # Step 5: Retrieve all documents in the current collection
                    documents = list(collection.find({}))
                    
                    print(f"Data in collection '{collection_name}' in database '{db_name}':")
                    for document in documents:
                        print(document)
    
        return "Data retrieval from all databases was successful!"

    except Exception as e:
        print(f"An error occurred while retrieving data: {str(e)}")
        return "Data retrieval from all databases failed."
    

# print("========AUTHENTICATION========")
# print(f"{AUTH_MONGO_DB_HOST}:{AUTH_MONGO_DB_PORT}")
# print(f"{AUTH_MONGO_DB_USERNAME}:{AUTH_MONGO_DB_PASSWORD}")
# print(test_mongo_connection())

print("========RETRIEVING ALL DATA========")
print(retrieve_all_data_from_all_databases())