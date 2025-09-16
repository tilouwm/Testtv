import requests
import sys
import json
from datetime import datetime

class HaitianTVAPITester:
    def __init__(self, base_url="https://live-stream-boost.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.user_id = f"test_user_{datetime.now().strftime('%H%M%S')}"

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else self.api_url
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                    elif isinstance(response_data, dict):
                        print(f"   Response keys: {list(response_data.keys())}")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")

            return success, response.json() if response.text and response.status_code < 500 else {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout")
            return False, {}
        except requests.exceptions.ConnectionError:
            print(f"❌ Failed - Connection error")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test("Root API Endpoint", "GET", "", 200)

    def test_init_data(self):
        """Initialize sample data"""
        return self.run_test("Initialize Sample Data", "POST", "init-data", 200)

    def test_get_channels(self):
        """Test getting all channels"""
        success, response = self.run_test("Get All Channels", "GET", "channels", 200)
        if success and isinstance(response, list):
            print(f"   Found {len(response)} channels")
            if len(response) > 0:
                sample_channel = response[0]
                required_fields = ['id', 'name', 'logo', 'stream', 'category']
                missing_fields = [field for field in required_fields if field not in sample_channel]
                if missing_fields:
                    print(f"   ⚠️  Missing fields in channel: {missing_fields}")
                else:
                    print(f"   ✅ Channel structure looks good")
        return success, response

    def test_get_channels_with_filters(self):
        """Test channel filtering"""
        # Test category filter
        success1, _ = self.run_test("Get Channels - News Category", "GET", "channels", 200, params={"category": "News"})
        
        # Test search filter
        success2, _ = self.run_test("Get Channels - Search 'tele'", "GET", "channels", 200, params={"search": "tele"})
        
        # Test active only filter
        success3, _ = self.run_test("Get Channels - Active Only", "GET", "channels", 200, params={"active_only": "true"})
        
        return success1 and success2 and success3

    def test_get_categories(self):
        """Test getting categories"""
        success, response = self.run_test("Get Categories", "GET", "categories", 200)
        if success and isinstance(response, list):
            print(f"   Found {len(response)} categories")
            if len(response) > 0:
                sample_category = response[0]
                if 'name' in sample_category and 'count' in sample_category:
                    print(f"   ✅ Category structure looks good")
                else:
                    print(f"   ⚠️  Category missing required fields")
        return success, response

    def test_favorites_functionality(self):
        """Test favorites functionality"""
        # Get initial favorites
        success1, favorites = self.run_test("Get User Favorites", "GET", f"favorites/{self.user_id}", 200)
        
        if not success1:
            return False
        
        # Get a channel ID to test with
        success2, channels = self.run_test("Get Channels for Favorites Test", "GET", "channels", 200)
        if not success2 or not channels:
            print("   ❌ No channels available for favorites test")
            return False
        
        test_channel_id = channels[0]['id']
        
        # Toggle favorite (add)
        success3, _ = self.run_test("Toggle Favorite - Add", "POST", f"favorites/{self.user_id}/toggle/{test_channel_id}", 200)
        
        # Get favorites again to verify
        success4, updated_favorites = self.run_test("Get Updated Favorites", "GET", f"favorites/{self.user_id}", 200)
        
        if success4 and test_channel_id in updated_favorites.get('channel_ids', []):
            print("   ✅ Favorite successfully added")
        else:
            print("   ❌ Favorite was not added properly")
            return False
        
        # Toggle favorite (remove)
        success5, _ = self.run_test("Toggle Favorite - Remove", "POST", f"favorites/{self.user_id}/toggle/{test_channel_id}", 200)
        
        return success1 and success3 and success4 and success5

    def test_channel_management(self):
        """Test channel CRUD operations"""
        # Create a test channel
        test_channel = {
            "name": "Test Channel",
            "logo": "https://example.com/logo.png",
            "stream": "https://example.com/stream.m3u8",
            "category": "Test",
            "description": "Test channel for API testing"
        }
        
        success1, created_channel = self.run_test("Create Channel", "POST", "channels", 200, data=test_channel)
        
        if not success1 or not created_channel:
            return False
        
        channel_id = created_channel.get('id')
        if not channel_id:
            print("   ❌ Created channel missing ID")
            return False
        
        # Get the created channel
        success2, _ = self.run_test("Get Created Channel", "GET", f"channels/{channel_id}", 200)
        
        # Update the channel
        update_data = {"name": "Updated Test Channel"}
        success3, _ = self.run_test("Update Channel", "PUT", f"channels/{channel_id}", 200, data=update_data)
        
        # Delete the channel
        success4, _ = self.run_test("Delete Channel", "DELETE", f"channels/{channel_id}", 200)
        
        # Verify deletion
        success5, _ = self.run_test("Verify Channel Deleted", "GET", f"channels/{channel_id}", 404)
        
        return success1 and success2 and success3 and success4 and success5

def main():
    print("🚀 Starting Haitian TV API Tests")
    print("=" * 50)
    
    tester = HaitianTVAPITester()
    
    # Run all tests
    tests = [
        ("Root Endpoint", tester.test_root_endpoint),
        ("Initialize Data", tester.test_init_data),
        ("Get Channels", tester.test_get_channels),
        ("Channel Filters", tester.test_get_channels_with_filters),
        ("Get Categories", tester.test_get_categories),
        ("Favorites Functionality", tester.test_favorites_functionality),
        ("Channel Management", tester.test_channel_management),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            test_func()
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {str(e)}")
    
    # Print final results
    print(f"\n{'='*50}")
    print(f"📊 Final Results:")
    print(f"   Tests Run: {tester.tests_run}")
    print(f"   Tests Passed: {tester.tests_passed}")
    print(f"   Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "0%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the details above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())