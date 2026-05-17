import os

def write_with_bom(path, content):
    with open(path, 'wb') as f:
        f.write(b'\xef\xbb\xbf') # UTF-8 BOM
        f.write(content.encode('utf-8'))

env_content = """# API Keys
GOOGLE_API_KEY=AIzaSyBLCz01IUkuX7ViDjh6LVAFEsaJL9nqVbA
OPENAI_API_KEY=AIzaSyBjiNgFyfCU3IbCgDzpoatyX_hGlmogCws

# LMS Credentials
LMS_USER=hemalatha@educlaas.com
LMS_PASS=Lathaprakash71

# URLs and Settings
LMS_URL=https://apps.claaslms.educlaas.com/authoring/home
SHAREPOINT_URL=https://educlaas.sharepoint.com/sites/LearningManagementTeamSite
HEADLESS=false
"""

write_with_bom('.env', env_content)
print("Updated .env with BOM")
