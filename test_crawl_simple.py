#!/usr/bin/env python3
"""
Simple test script for recursive crawling functionality
"""
import requests
import json
import time

def test_recursive_crawl():
    """Test the recursive crawling endpoint"""
    base_url = "http://localhost:3000"
    
    # Test payload for homelabing.com crawl
    crawl_request = {
        "start_url": "https://homelabing.com",
        "max_pages": 5,
        "scope": "domain"
    }
    
    print("🧪 Testing Recursive Crawling")
    print("=" * 40)
    
    # Start crawl
    print(f"Starting crawl of {crawl_request['start_url']}...")
    try:
        response = requests.post(
            f"{base_url}/api/crawl/",
            json=crawl_request,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job_id')
            print(f"✅ Crawl job started: {job_id}")
            
            # Monitor progress
            for i in range(10):  # Check for up to 10 iterations
                time.sleep(5)
                
                status_response = requests.get(f"{base_url}/api/crawl/{job_id}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"📊 Status: {status['status']} - Pages: {status.get('pages_crawled', 0)}")
                    
                    if status['status'] in ['completed', 'failed', 'stopped']:
                        break
                else:
                    print(f"❌ Failed to get status: {status_response.status_code}")
                    break
        else:
            print(f"❌ Failed to start crawl: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_recursive_crawl()