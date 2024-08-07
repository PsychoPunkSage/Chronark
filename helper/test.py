from pymongo import MongoClient

# mongo_client = MongoClient(
#     username="mongoauth", 
#     password="authentication", 
#     host="localhost", 
#     port=27017
# )

class MongoDBHandler:
    def __init__(self, username, password, host, port):
        self.client = MongoClient(
            username=username,
            password=password,
            host=host,
            port=port
        )
        self.db = self.client.contact

    def get_all_data(self):
        storage_data = list(self.db.storage.find())
        contacts_data = list(self.db.contacts.find())
        faqs_data = list(self.db.faq.find())
        conversation_data = list(self.db.conversation.find())

        return {
            "storage": storage_data,
            "contacts": contacts_data,
            "faq": faqs_data,
            "conversation": conversation_data
        }
    
    def test_connection(self):
        # Create a temporary database and collection for testing
        temp_db = self.client["temp_db"]
        temp_collection = temp_db["temp_collection"]

        # Insert a test document
        test_document = {"name": "Test", "value": 123}
        insert_result = temp_collection.insert_one(test_document)
        print(f"Inserted document ID: {insert_result.inserted_id}")

        # Fetch the test document
        fetched_document = temp_collection.find_one({"name": "Test"})
        print(f"Fetched document: {fetched_document}")

        # Delete the test document
        delete_result = temp_collection.delete_one({"name": "Test"})
        print(f"Deleted document count: {delete_result.deleted_count}")

        # Clean up the temporary database
        self.client.drop_database("temp_db")

# MongoDB connection details
MONGO_USERNAME = "mongoauth"
MONGO_PASSWORD = "authentication"
MONGO_HOST = "localhost"
MONGO_PORT = 27018

# Initialize MongoDBHandler
mongodb_handler = MongoDBHandler(
    username=MONGO_USERNAME,
    password=MONGO_PASSWORD,
    host=MONGO_HOST,
    port=MONGO_PORT
)

# Get all data from collections
data = mongodb_handler.get_all_data()

mongodb_handler.test_connection()

# Print the retrieved data
# print("Storage Data:", data['storage'])
# print("Contacts Data:", data['contacts'])
# print("FAQs Data:", data['faq'])
# print("Conversation Data:", data['conversation'])

# db = mongo_client.auth_db
# users_collection = db.users

# try :
#     test_user = {"username": "test_user", "password": "test_password"}
#     insert_result = users_collection.insert_one(test_user)
#     print(f"Inserted document ID: {insert_result.inserted_id}")
#     fetched_user = users_collection.find_one({"username": "test_user"})
#     print(f"Fetched document: {fetched_user}")
#     delete_result = users_collection.delete_one({"username": "test_user"})
#     print(f"Deleted document count: {delete_result.deleted_count}")
# except Exception as e:
#     print(f"An error occurred: {e}")