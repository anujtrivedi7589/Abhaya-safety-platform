// State Management
let currentTab = 'sos-tab';
let currentActiveSOS = null;
let currentTriageQuestionId = 'INJURED';
let userCategoryFilter = 'all';

// Mock User Location (Kanpur / Lucknow Tech Park Precinct)
const userLocation = { lat: 26.8467, lng: 80.9462 };
const deviceId = "DEV-ABHAYA-" + Math.floor(1000 + Math.random() * 9000);

// Initialize App on DOM Load
document.addEventListener("DOMContentLoaded", () => {
  loadNearbyServices();
  updateDecoyClock();
  setInterval(updateDecoyClock, 1000);
});

// Tab Navigation
function switchTab(tabId) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));

  document.getElementById(tabId).classList.add('active');
  
  const activeBtn = Array.from(document.querySelectorAll('.nav-btn')).find(
    btn => btn.getAttribute('onclick').includes(tabId)
  );
  if (activeBtn) activeBtn.classList.add('active');

  if (tabId === 'nearby-tab') loadNearbyServices();
  if (tabId === 'command-tab') loadDashboard();
}

// SOS Trigger Handler
async function handleSOSTrigger() {
  const sosBtn = document.getElementById("sos-main-btn");
  const feedback = document.getElementById("sos-feedback");
  const statusPill = document.getElementById("sos-status-pill");

  // Haptic Feedback simulation
  if (navigator.vibrate) {
    navigator.vibrate(200);
  }

  sosBtn.style.transform = "scale(0.92)";
  setTimeout(() => sosBtn.style.transform = "scale(1)", 150);

  statusPill.className = "status-pill red";
  statusPill.innerHTML = '<span class="dot"></span> EMERGENCY SOS ACTIVE';
  feedback.innerText = "Transmitting encrypted GPS, IP, and Device ID to Police & Verified Citizens...";

  try {
    const response = await fetch("/api/sos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        device_id: deviceId,
        lat: userLocation.lat,
        lng: userLocation.lng,
        user_tier: 1, // Default trigger
        user_name: "Anuj Trivedi",
        user_phone: "+91-7355988498"
      })
    });

    const data = await response.json();
    currentActiveSOS = data.sos_id;
    
    feedback.innerText = `SOS ACTIVE! Session ID: ${data.sos_id} | Priority: IMMEDIATE RED ALERT`;
    
    // Activate Triage Widget
    startSilentTriage();
  } catch (err) {
    console.error("SOS Transmission Error:", err);
    feedback.innerText = "Network Error - Falling back to Offline SMS Alert Protocol.";
  }
}

// Silent AI Triage Flow
function startSilentTriage() {
  document.getElementById("triage-options-box").style.display = "flex";
  document.getElementById("triage-question-text").innerText = "1. Are you or anyone with you injured?";
  currentTriageQuestionId = "INJURED";
  document.getElementById("triage-threat-badge").innerText = "Threat Level: 3 (Assessing)";
}

async function submitTriageAnswer(answer) {
  if (!currentActiveSOS) {
    alert("Please trigger SOS first.");
    return;
  }

  try {
    const res = await fetch("/api/triage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sos_id: currentActiveSOS,
        question_id: currentTriageQuestionId,
        answer: answer
      })
    });

    const data = await res.json();
    
    document.getElementById("triage-threat-badge").innerText = `Threat Level: ${data.updated_threat_level} (${data.threat_label})`;
    
    if (data.next_question.next_id === "COMPLETE") {
      document.getElementById("triage-question-text").innerText = "✅ " + data.next_question.text;
      document.getElementById("triage-options-box").style.display = "none";
    } else {
      currentTriageQuestionId = data.next_question.next_id;
      document.getElementById("triage-question-text").innerText = data.next_question.text;
    }
  } catch (err) {
    console.error("Triage Error:", err);
  }
}

// Ambient Audio Simulation
async function simulateAmbientAudio() {
  if (!currentActiveSOS) {
    alert("Trigger SOS first to initiate ambient audio analysis.");
    return;
  }

  const outputBox = document.getElementById("audio-analysis-output");
  outputBox.innerText = "🎙️ Recording 10s encrypted ambient clip... Analyzing Speech-to-Text keywords...";

  setTimeout(async () => {
    try {
      const res = await fetch("/api/audio-analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sos_id: currentActiveSOS,
          audio_transcript_sample: "Help! He has a knife! Don't touch me!"
        })
      });

      const data = await res.json();
      outputBox.innerHTML = `
        <strong style="color: var(--accent-red);">🚨 AUDIO ALERT:</strong> Detected Threat Keywords: [${data.detected_keywords.join(", ")}] <br>
        <strong>Status:</strong> ${data.escalation_status} — ${data.dispatch_action}
      `;
      document.getElementById("triage-threat-badge").innerText = "Threat Level: 5 (CRITICAL EMERGENCY)";
    } catch (err) {
      console.error("Audio Analysis Error:", err);
    }
  }, 1200);
}

// Blackout & Decoy Toggle
function toggleBlackout() {
  const overlay = document.getElementById("blackout-overlay");
  overlay.classList.toggle("active");
}

function toggleDecoy() {
  const overlay = document.getElementById("decoy-overlay");
  overlay.classList.toggle("active");
}

function updateDecoyClock() {
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  document.getElementById("decoy-time").innerText = `${hours}:${minutes}`;
  
  const options = { weekday: 'long', month: 'long', day: 'numeric' };
  document.getElementById("decoy-date").innerText = now.toLocaleDateString('en-US', options);
}

// Nearby Emergency Services Finder
function filterCategory(cat, btn) {
  userCategoryFilter = cat;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadNearbyServices();
}

async function loadNearbyServices() {
  const container = document.getElementById("services-list-container");
  container.innerHTML = '<p style="text-align: center; color: var(--text-muted); padding: 1.5rem;">Calculating nearest emergency services using GPS...</p>';

  try {
    const res = await fetch(`/api/nearby?lat=${userLocation.lat}&lng=${userLocation.lng}&category=${userCategoryFilter}`);
    const data = await res.json();

    if (!data.services || data.services.length === 0) {
      container.innerHTML = '<p style="text-align: center; padding: 1.5rem;">No emergency services found nearby.</p>';
      return;
    }

    let html = '';
    data.services.forEach(svc => {
      let badgeClass = 'badge-police';
      let icon = '🚔';
      if (svc.category === 'hospital') { badgeClass = 'badge-hospital'; icon = '🏥'; }
      if (svc.category === 'medical_store') { badgeClass = 'badge-medical'; icon = '💊'; }

      html += `
        <div class="service-card">
          <div class="service-info">
            <div class="service-name">${icon} ${svc.name}</div>
            <div class="service-meta">
              <span class="badge ${badgeClass}">${svc.category.replace('_', ' ')}</span>
              ${svc.is_open_24x7 ? '<span class="badge badge-24x7">24x7 Open</span>' : ''}
              <span>📏 <strong>${svc.distance_km} km</strong> away</span>
              <span>🚗 ~${svc.estimated_drive_mins} min drive</span>
              <span>🚶 ~${svc.estimated_walk_mins} min walk</span>
              <span>⭐ ${svc.rating}</span>
            </div>
            <div style="font-size: 0.82rem; color: var(--text-muted);">
              📍 ${svc.address} | 📞 ${svc.phone}
            </div>
          </div>

          <div class="service-actions">
            <a href="tel:${svc.phone}" class="btn-action btn-call">📞 Call Now</a>
            <a href="${svc.google_maps_url}" target="_blank" class="btn-action btn-nav">🗺️ Navigate Map</a>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  } catch (err) {
    console.error("Error loading services:", err);
    container.innerHTML = '<p style="text-align: center; color: var(--accent-red); padding: 1.5rem;">Failed to fetch nearby emergency services.</p>';
  }
}

// Command Center Feed
async function loadDashboard() {
  const container = document.getElementById("command-feed-container");
  const tier = document.getElementById("responder-tier-select").value;

  try {
    const res = await fetch("/api/dashboard");
    const data = await res.json();

    let html = `
      <div style="display: flex; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap;">
        <div style="background: var(--bg-primary); padding: 0.8rem 1.2rem; border-radius: 8px; flex: 1;">
          <div style="font-size: 0.75rem; color: var(--text-muted);">Active Emergencies</div>
          <div style="font-size: 1.4rem; font-weight: 800; color: var(--accent-red);">${data.active_sos_count}</div>
        </div>
        <div style="background: var(--bg-primary); padding: 0.8rem 1.2rem; border-radius: 8px; flex: 1;">
          <div style="font-size: 0.75rem; color: var(--text-muted);">Target Response Time</div>
          <div style="font-size: 1.1rem; font-weight: 700; color: var(--accent-green);">${data.average_civilian_response_time_target}</div>
        </div>
        <div style="background: var(--bg-primary); padding: 0.8rem 1.2rem; border-radius: 8px; flex: 1;">
          <div style="font-size: 0.75rem; color: var(--text-muted);">ERSS 112 Bridge</div>
          <div style="font-size: 1.1rem; font-weight: 700; color: var(--accent-blue);">${data.erss_112_bridge_status}</div>
        </div>
      </div>
    `;

    if (data.recent_emergency_events.length === 0) {
      html += '<p style="text-align: center; padding: 1.5rem; color: var(--text-muted);">No active SOS emergency dispatches.</p>';
    } else {
      data.recent_emergency_events.forEach(evt => {
        let locationDisplay = '';
        if (tier == 1) {
          locationDisplay = `<strong>Tier 1 Police Exact GPS:</strong> ${evt.exact_location.lat.toFixed(4)}, ${evt.exact_location.lng.toFixed(4)} (<a href="https://maps.google.com/?q=${evt.exact_location.lat},${evt.exact_location.lng}" target="_blank" style="color:var(--accent-blue);">Open Dispatch Map</a>)`;
        } else if (tier == 2) {
          locationDisplay = `<strong>Tier 2 Verified Citizen GPS:</strong> ${evt.exact_location.lat.toFixed(4)}, ${evt.exact_location.lng.toFixed(4)} (Verified Citizen Access)`;
        } else {
          locationDisplay = `<strong>Tier 3 Anonymous View:</strong> Alert in ${evt.sector} (Exact pin withheld for community safety to prevent attacker tracking).`;
        }

        html += `
          <div class="service-card" style="border-left: 4px solid ${evt.threat_level >= 4 ? 'var(--accent-red)' : 'var(--accent-amber)'};">
            <div style="width: 100%;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                <span style="font-size: 1rem; font-weight: 800; color: var(--accent-red);">🚨 ${evt.sos_id}</span>
                <span class="badge ${evt.threat_level >= 4 ? 'badge-hospital' : 'badge-police'}">Threat Level ${evt.threat_level}/5</span>
              </div>
              <div style="font-size: 0.85rem; color: var(--text-main); margin-bottom: 0.4rem;">
                ${locationDisplay}
              </div>
              <div style="font-size: 0.8rem; color: var(--text-muted);">
                <strong>Audio Keywords Detected:</strong> ${evt.audio_keywords || 'None'} | 
                <strong>Triage Log:</strong> ${evt.triage_summary || 'Pending'} |
                <strong>Time:</strong> ${evt.timestamp}
              </div>
            </div>
          </div>
        `;
      });
    }

    container.innerHTML = html;
  } catch (err) {
    console.error("Dashboard Error:", err);
    container.innerHTML = '<p style="text-align: center; color: var(--accent-red); padding: 1.5rem;">Failed to load Command Center feed.</p>';
  }
}
