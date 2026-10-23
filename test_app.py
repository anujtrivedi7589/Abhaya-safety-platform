import unittest
from fastapi.testclient import TestClient
from app import app

class TestAbhayaApp(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_html(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ABHAYA", response.text)
        self.assertIn("Nearest Emergency Services Finder", response.text)

    def test_sos_trigger_tier_1(self):
        payload = {
            "device_id": "TEST-DEV-001",
            "lat": 26.8467,
            "lng": 80.9462,
            "user_tier": 1,
            "user_name": "Anuj Test",
            "user_phone": "+91-7355988498"
        }
        response = self.client.post("/api/sos", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "SOS_TRANSMITTED")
        self.assertIn("sos_id", data)
        self.assertEqual(data["view_payload"]["view_type"], "TIER_1_EXACT_POLICE_GPS")

    def test_sos_trigger_tier_3_asymmetric(self):
        payload = {
            "device_id": "TEST-DEV-002",
            "lat": 26.8467,
            "lng": 80.9462,
            "user_tier": 3
        }
        response = self.client.post("/api/sos", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["view_payload"]["view_type"], "TIER_3_ANONYMOUS_SECTOR_ALERT")

    def test_nearby_emergency_services(self):
        # Test fetching police, hospital, and medical stores
        for category in ["all", "police", "hospital", "medical_store"]:
            response = self.client.get(f"/api/nearby?lat=26.8467&lng=80.9462&category={category}")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("services", data)
            self.assertGreater(len(data["services"]), 0, f"No services returned for {category}")
            # Ensure distance and maps link are populated
            first_svc = data["services"][0]
            self.assertIn("distance_km", first_svc)
            self.assertIn("google_maps_url", first_svc)
            self.assertIn("phone", first_svc)

    def test_full_triage_flow(self):
        # 1. Trigger SOS
        sos_res = self.client.post("/api/sos", json={
            "device_id": "DEV-TRIAGE-TEST",
            "lat": 26.8500,
            "lng": 80.9500,
            "user_tier": 1
        }).json()
        sos_id = sos_res["sos_id"]

        # 2. Answer Triage Questions
        triage_res = self.client.post("/api/triage", json={
            "sos_id": sos_id,
            "question_id": "INJURED",
            "answer": "YES"
        }).json()
        self.assertEqual(triage_res["updated_threat_level"], 4)

        # 3. Audio Analysis Escalation
        audio_res = self.client.post("/api/audio-analysis", json={
            "sos_id": sos_id,
            "audio_transcript_sample": "Help! There is a gun and knife!"
        }).json()
        self.assertEqual(audio_res["escalation_status"], "AUTOMATIC_LEVEL_5_ESCALATION")

    def test_dashboard_api(self):
        response = self.client.get("/api/dashboard")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("active_sos_count", data)
        self.assertIn("recent_emergency_events", data)

if __name__ == "__main__":
    unittest.main()
