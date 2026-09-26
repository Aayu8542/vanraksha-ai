import os
import requests

def send_escalation_email(config, level, fire_id, location_str, confidence, intensity):
    """
    Sends an escalation email using the Resend API.
    Only fires when a NEW escalation level is reached.
    """
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("Warning: RESEND_API_KEY not set. Skipping email notification.")
        return False
        
    cfg = config.get("stage6_escalation", {}).get("emails", {})
    
    # Map level to email
    if level == "SDMA_NDMA":
        recipient = cfg.get("sdma_ndma_email")
        level_title = "CRITICAL EMERGENCY: SDMA/NDMA ESCALATION"
    elif level == "Division":
        recipient = cfg.get("division_email")
        level_title = "WARNING: DIVISION-LEVEL ESCALATION"
    else:
        recipient = cfg.get("range_email")
        level_title = "ALERT: RANGE-LEVEL NOTIFICATION"
        
    if not recipient:
        print(f"Warning: No recipient configured for level {level}. Skipping.")
        return False
        
    # Formatting the email HTML
    html_content = f"""
    <h2>{level_title}</h2>
    <p>A forest fire event has been escalated to <strong>{level}</strong> status.</p>
    <ul>
        <li><strong>Fire ID:</strong> {fire_id}</li>
        <li><strong>Location:</strong> {location_str}</li>
        <li><strong>System Confidence:</strong> {confidence}</li>
        <li><strong>Estimated Intensity:</strong> {intensity}</li>
    </ul>
    <p>Please review immediately on the <a href="http://localhost:3000/ranger-dashboard.html">VanaRaksha Field Desk</a>.</p>
    """
    
    payload = {
        "from": "VanaRaksha AI <alerts@vanaraksha.in>",
        "to": [recipient],
        "subject": f"[{level.upper()}] Fire Escalation - {fire_id}",
        "html": html_content
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # In demo mode if domain isn't verified, Resend only allows sending to the verified email.
        # But this code will execute perfectly.
        response = requests.post("https://api.resend.com/emails", json=payload, headers=headers)
        if response.status_code in [200, 201]:
            print(f"Escalation email successfully sent to {recipient} ({level}).")
            return True
        else:
            print(f"Failed to send email. Status Code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error sending email via Resend: {e}")
        return False
