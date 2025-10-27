"""
Simple API test script to verify frontend-backend integration.
Run this after starting the backend server to test key endpoints.

Usage:
    python test_api.py
"""
import requests
import json

BASE_URL = "http://localhost:8000/api"

# Test credentials
TEST_USER = {
    "username": "testuser",
    "password": "testpass123"
}

def print_response(response, title="Response"):
    """Pretty print response"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(f"Body: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"Body: {response.text}")
    print(f"{'='*60}\n")

def test_auth():
    """Test authentication"""
    print("\n🔐 Testing Authentication...")
    
    # Login
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json=TEST_USER
    )
    print_response(response, "Login Response")
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("data", {}).get("accessToken") or data.get("accessToken")
        return token
    return None

def test_users(token):
    """Test user CRUD operations"""
    print("\n👤 Testing User Operations...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # List users
    response = requests.get(f"{BASE_URL}/user/", headers=headers)
    print_response(response, "List Users")
    
    # Get user info
    response = requests.get(f"{BASE_URL}/user/info", headers=headers)
    print_response(response, "User Info")

def test_projects(token):
    """Test project CRUD operations"""
    print("\n📁 Testing Project Operations...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create project
    project_data = {
        "projectName": "Test Project API",
        "description": "Created via API test"
    }
    response = requests.post(
        f"{BASE_URL}/projects/",
        headers=headers,
        json=project_data
    )
    print_response(response, "Create Project")
    
    project_id = None
    if response.status_code in [200, 201]:
        data = response.json()
        project_id = data.get("data", {}).get("projectId") or data.get("projectId")
    
    # List projects
    response = requests.get(f"{BASE_URL}/projects/?skip=0&limit=10", headers=headers)
    print_response(response, "List Projects")
    
    return project_id

def test_subjects(token):
    """Test subject CRUD operations"""
    print("\n🧪 Testing Subject Operations...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create subject
    subject_data = {
        "subjectName": "Test Subject API"
    }
    response = requests.post(
        f"{BASE_URL}/subjects/",
        headers=headers,
        json=subject_data
    )
    print_response(response, "Create Subject")
    
    subject_id = None
    if response.status_code in [200, 201]:
        data = response.json()
        subject_id = data.get("data", {}).get("subjectId") or data.get("subjectId")
    
    # List subjects
    response = requests.get(f"{BASE_URL}/subjects/?skip=0&limit=10", headers=headers)
    print_response(response, "List Subjects")
    
    return subject_id

def test_data_items(token, project_id, subject_id):
    """Test data item CRUD operations"""
    print("\n📊 Testing Data Item Operations...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create data item
    data_item = {
        "name": "Test Data Item",
        "projectId": project_id,
        "subjectId": subject_id,
        "fileDescription": "Test data item created via API",
        "dataType": "raw",
        "fileName": "test.csv",
        "fileType": "csv"
    }
    response = requests.post(
        f"{BASE_URL}/data-items/",
        headers=headers,
        json=data_item
    )
    print_response(response, "Create Data Item")
    
    data_item_id = None
    if response.status_code in [200, 201]:
        data = response.json()
        data_item_id = data.get("data", {}).get("dataItemId") or data.get("dataItemId")
    
    # List data items
    response = requests.get(
        f"{BASE_URL}/data-items/?skip=0&limit=10&projectId={project_id}",
        headers=headers
    )
    print_response(response, "List Data Items")
    
    return data_item_id

def test_tags(token):
    """Test tag operations"""
    print("\n🏷️  Testing Tag Operations...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create tag
    tag_data = {
        "tagName": "API Test Tag",
        "tagDescription": "Created for API testing"
    }
    response = requests.post(
        f"{BASE_URL}/tags/",
        headers=headers,
        json=tag_data
    )
    print_response(response, "Create Tag")
    
    tag_id = None
    if response.status_code in [200, 201]:
        data = response.json()
        tag_id = data.get("data", {}).get("tagId") or data.get("tagId")
    
    # List tags
    response = requests.get(f"{BASE_URL}/tags/?skip=0&limit=10", headers=headers)
    print_response(response, "List Tags")
    
    return tag_id

def test_entity_tags(token, tag_id, project_id):
    """Test entity tag operations"""
    if not tag_id or not project_id:
        print("\n⚠️  Skipping entity tag test - missing tag_id or project_id")
        return
    
    print("\n🔗 Testing Entity Tag Operations...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create entity tag
    entity_tag_data = {
        "tagId": tag_id,
        "entityId": project_id,
        "entityType": "Project"
    }
    response = requests.post(
        f"{BASE_URL}/entity-tags/",
        headers=headers,
        json=entity_tag_data
    )
    print_response(response, "Create Entity Tag")
    
    # List entity tags
    response = requests.get(
        f"{BASE_URL}/entity-tags/?entityId={project_id}&entityType=Project",
        headers=headers
    )
    print_response(response, "List Entity Tags for Project")

def test_user_projects(token):
    """Test user-project association operations"""
    print("\n👥 Testing User-Project Operations...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # List user projects
    response = requests.get(f"{BASE_URL}/user-projects/", headers=headers)
    print_response(response, "List User-Projects")

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 Starting API Integration Tests")
    print("="*60)
    
    # Authenticate
    token = test_auth()
    if not token:
        print("❌ Authentication failed. Cannot proceed with tests.")
        return
    
    print(f"\n✅ Authentication successful! Token: {token[:20]}...")
    
    # Run tests
    test_users(token)
    project_id = test_projects(token)
    subject_id = test_subjects(token)
    data_item_id = test_data_items(token, project_id, subject_id)
    tag_id = test_tags(token)
    test_entity_tags(token, tag_id, project_id)
    test_user_projects(token)
    
    print("\n" + "="*60)
    print("✅ All API tests completed!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
