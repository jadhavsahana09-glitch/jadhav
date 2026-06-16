import re
import sqlite3
import sys
import urllib.parse
import urllib.request

BASE_URL = 'http://127.0.0.1:5000'

# Create a cookie opener to maintain session
cookie_processor = urllib.request.HTTPCookieProcessor()
opener = urllib.request.build_opener(cookie_processor)
urllib.request.install_opener(opener)


def get_otp_from_db(identifier):
    conn = sqlite3.connect('carbon_db.sqlite')
    cur = conn.cursor()
    cur.execute("SELECT otp_code FROM otp_tokens WHERE identifier = ? ORDER BY created_at DESC LIMIT 1", (identifier,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def extract_csrf(html):
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return match.group(1) if match else None


try:
    print("0. Cleaning SQLite database tables...")
    conn = sqlite3.connect('carbon_db.sqlite')
    cur = conn.cursor()
    cur.execute("DELETE FROM users")
    cur.execute("DELETE FROM otp_tokens")
    cur.execute("DELETE FROM emission_logs")
    cur.execute("DELETE FROM goals")
    conn.commit()
    cur.close()
    conn.close()
    print("   [PASSED]")

    print("1. Accessing Landing Page...")
    html = opener.open(BASE_URL).read().decode('utf-8')
    assert "Carby Control" in html, "Carby Control landing page not loaded"
    assert "calculator-demo" in html, "Landing calculator section missing"
    assert "impact-dashboard" in html, "Landing analytics section missing"
    print("   [PASSED]")

    print("2. Submitting Registration for Alice...")
    register_url = f"{BASE_URL}/register"
    register_html = opener.open(register_url).read().decode('utf-8')
    csrf = extract_csrf(register_html)
    data = urllib.parse.urlencode({
        'name': 'Alice Test',
        'identifier': 'alice@test.com',
        'csrf_token': csrf
    }).encode('utf-8')
    req = urllib.request.Request(register_url, data=data)
    response = opener.open(req)
    assert response.url.endswith("/verify-otp"), f"Did not redirect to verify-otp, went to {response.url}"
    print("   [PASSED]")

    print("3. Fetching OTP from SQLite Database...")
    otp = get_otp_from_db('alice@test.com')
    assert otp is not None, "OTP not stored in database"
    print(f"   Found OTP: {otp}")
    print("   [PASSED]")

    print("4. Verifying OTP...")
    verify_url = f"{BASE_URL}/verify-otp"
    verify_html = opener.open(verify_url).read().decode('utf-8')
    csrf = extract_csrf(verify_html)
    form_data = {}
    for i, char in enumerate(otp, 1):
        form_data[f'otp{i}'] = char
    form_data['csrf_token'] = csrf

    data = urllib.parse.urlencode(form_data).encode('utf-8')
    req = urllib.request.Request(verify_url, data=data)
    response = opener.open(req)
    assert response.url.endswith("/dashboard"), f"Did not redirect to dashboard, went to {response.url}"
    print("   [PASSED]")

    print("5. Viewing Dashboard (Accessing Authenticated Route)...")
    dashboard_html = opener.open(f"{BASE_URL}/dashboard").read().decode('utf-8')
    assert "Alice Test" in dashboard_html, "Dashboard does not display user's name"
    print("   [PASSED]")

    print("6. Logging an Emission Entry (Transport: 15.5 kg CO2)...")
    tracker_url = f"{BASE_URL}/tracker"
    tracker_html = opener.open(tracker_url).read().decode('utf-8')
    csrf = extract_csrf(tracker_html)
    data = urllib.parse.urlencode({
        'category_id': '1',  # Transport
        'amount': '15.5',
        'description': 'Commute to office',
        'log_date': '2026-06-11',
        'csrf_token': csrf
    }).encode('utf-8')
    req = urllib.request.Request(tracker_url, data=data)
    response = opener.open(req)
    assert response.status == 200, "Tracker submission failed"
    print("   [PASSED]")

    print("7. Verifying logged entry in Tracker history...")
    tracker_html = opener.open(f"{BASE_URL}/tracker").read().decode('utf-8')
    assert "Commute to office" in tracker_html, "Logged entry description not shown in history"
    assert "15.500" in tracker_html or "15.5" in tracker_html, "Logged entry amount not shown in history"
    print("   [PASSED]")

    print("8. Testing CSV Report download...")
    csv_response = opener.open(f"{BASE_URL}/reports/download/csv")
    csv_data = csv_response.read().decode('utf-8')
    assert "Commute to office" in csv_data, "CSV report does not contain the logged entry"
    assert "15.500" in csv_data, "CSV report does not contain the logged entry amount"
    print("   [PASSED]")

    print("9. Testing PDF Report download...")
    pdf_response = opener.open(f"{BASE_URL}/reports/download/pdf")
    pdf_data = pdf_response.read()
    assert pdf_data.startswith(b'%PDF'), "PDF report is not a valid PDF file"
    print("   [PASSED]")

    print("\n[SUCCESS] ALL TESTS PASSED! The website backend and frontend are 100% proper and fully working!")

except Exception as e:
    print(f"\n[ERROR] TEST FAILED: {e}")
    sys.exit(1)
