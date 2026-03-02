import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.supabase import supabase

async def test_supabase_connection():
    print("Testing Supabase connection...")
    try:
        # Check if we can reach the auth service
        # (Simply checking SUPABASE_URL and KEY presence handled in config)
        print(f"Supabase URL: {os.getenv('SUPABASE_URL')}")
        
        # Test basic table query (assuming 'users' table exists)
        response = await asyncio.to_thread(
            supabase.table("users").select("count", count="exact").limit(1).execute
        )
        print(f"Connection successful! User count: {response.count}")
    except Exception as e:
        print(f"Connection failed: {e}")

async def test_supabase_insert_cleanup():
    print("\nTesting Supabase insert/delete...")
    test_user = {
        "name": "Integration Test",
        "email": "integration@test.com",
        "qr_code_data": "test-qr-123"
    }
    
    try:
        # Insert
        insert_res = await asyncio.to_thread(
            supabase.table("users").insert(test_user).execute
        )
        print(f"Insert successful! Created user: {insert_res.data[0]['name']}")
        
        # Cleanup
        await asyncio.to_thread(
            supabase.table("users").delete().eq("qr_code_data", "test-qr-123").execute
        )
        print("Cleanup successful!")
    except Exception as e:
        print(f"CRUD test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_supabase_connection())
    asyncio.run(test_supabase_insert_cleanup())
