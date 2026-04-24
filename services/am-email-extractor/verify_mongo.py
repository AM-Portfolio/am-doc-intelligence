import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

try:
    import pymongo
    print("pymongo is installed.")
except ImportError:
    print("Error: pymongo is NOT installed. Please run: pip install pymongo")
    sys.exit(1)

from database import Database

def test_connection():
    print("Testing MongoDB connection...")
    db = Database()
    try:
        db.connect()
        print("Successfully connected to MongoDB!")
        print(f"Database: {db.db_name}")
        
        # Test insert
        print("Testing insert...")
        doc_id = db.save_holdings(
            user_id="test_user",
            broker="test_broker",
            holdings=[{"symbol": "TEST", "quantity": 1}],
            metadata={"source": "verification_script"}
        )
        print(f"Successfully inserted document with ID: {doc_id}")
        
        # Test retrieval
        print("Testing retrieval...")
        latest = db.get_latest_holdings("test_user", "test_broker")
        if latest and latest['holdings'][0]['symbol'] == 'TEST':
            print("Successfully retrieved document!")
        else:
            print("Retrieval failed or data mismatch.")
            
    except Exception as e:
        print(f"Connection failed: {e}")
        print("Make sure MongoDB is running on localhost:27017")

if __name__ == "__main__":
    test_connection()
