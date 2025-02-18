from flask import Flask, request, jsonify, send_file
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS
import urllib3
import os
from dotenv import load_dotenv
from functools import wraps

# Load environment variables
load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
CORS(app)

# Get configuration from environment variables
API_TIMEOUT = int(os.getenv('API_TIMEOUT', 10))
USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0')

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Bulk Heading Harvester</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 20px auto; padding: 20px; }
        textarea { width: 100%; height: 150px; padding: 10px; margin: 10px 0; }
        button { padding: 10px 20px; background: #4CAF50; color: white; border: none; cursor: pointer; }
        .heading-item { margin: 10px 0; padding: 10px; background: #f5f5f5; }
        .url-section { margin: 20px 0; padding: 10px; border: 1px solid #ddd; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>Bulk Heading Harvester</h1>
    <textarea id="urlInput" placeholder="Enter URLs (one per line)&#10;example.com&#10;python.org"></textarea>
    <button onclick="harvestHeadings()">Harvest Headings</button>
    <div id="results"></div>

    <script>
        async function harvestHeadings() {
            const urls = document.getElementById('urlInput').value.split('\\n').filter(url => url.trim());
            const results = document.getElementById('results');
            results.innerHTML = 'Processing...';
            
            try {
                const response = await fetch('/harvest', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({urls: urls})
                });
                const data = await response.json();
                
                results.innerHTML = data.results.map(result => `
                    <div class="url-section">
                        <h3>${result.url}</h3>
                        ${result.status === 'error' ? 
                            `<div class="error">${result.error}</div>` :
                            result.headings.map(h => `
                                <div class="heading-item">
                                    <strong>${h.type}</strong> ${h.text}
                                </div>
                            `).join('')
                        }
                    </div>
                `).join('');
            } catch (error) {
                results.innerHTML = `<div class="error">Error: ${error.message}</div>`;
            }
        }
    </script>
</body>
</html>
'''

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key and api_key == os.getenv('API_KEY'):
            return f(*args, **kwargs)
        return jsonify({"error": "Invalid or missing API key"}), 401
    return decorated

@app.route('/')
def home():
    return HTML_TEMPLATE

@app.route('/harvest', methods=['POST'])
def harvest_headings():
    try:
        urls = request.json.get('urls', [])
        results = []
        
        for url in urls:
            try:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                
                response = requests.get(url.strip(), 
                    headers={'User-Agent': 'Mozilla/5.0'}, 
                    verify=False, 
                    timeout=10
                )
                soup = BeautifulSoup(response.text, 'html.parser')
                headings = [
                    {'type': tag.name.upper(), 'text': tag.get_text().strip()}
                    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if tag.get_text().strip()
                ]
                
                results.append({
                    'url': url,
                    'status': 'success',
                    'headings': headings
                })
            except Exception as e:
                results.append({
                    'url': url,
                    'status': 'error',
                    'error': str(e)
                })
                
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/harvest', methods=['POST'])
def api_harvest_headings():
    try:
        urls = request.json.get('urls', [])
        if not urls:
            return jsonify({
                'error': 'No URLs provided',
                'status': 'error'
            }), 400
            
        results = []
        
        for url in urls:
            try:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                
                response = requests.get(
                    url.strip(), 
                    headers={'User-Agent': USER_AGENT}, 
                    verify=False, 
                    timeout=API_TIMEOUT
                )
                soup = BeautifulSoup(response.text, 'html.parser')
                headings = [
                    {'type': tag.name.upper(), 'text': tag.get_text().strip()}
                    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if tag.get_text().strip()
                ]
                
                results.append({
                    'url': url,
                    'status': 'success',
                    'headings': headings
                })
            except Exception as e:
                results.append({
                    'url': url,
                    'status': 'error',
                    'error': str(e)
                })
                
        return jsonify({
            'status': 'success',
            'results': results
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

def extract_headings(urls, heading_types=None):
    if isinstance(urls, str):
        urls = [urls]
    
    if not heading_types:
        heading_types = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    elif isinstance(heading_types, str):
        heading_types = [heading_types]
    
    extracted_data = []
    
    for url in urls:
        try:
            headers = {'User-Agent': os.getenv('USER_AGENT', 'Mozilla/5.0')}
            response = requests.get(url, headers=headers, timeout=int(os.getenv('API_TIMEOUT', 10)))
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            url_data = {
                "url": url,
                "extracted_headings": []
            }
            
            for tag in heading_types:
                tag = tag.lower()
                if not tag.startswith('h'):
                    tag = 'h' + tag
                
                headings = soup.find_all(tag)
                for heading in headings:
                    clean_text = ' '.join(heading.get_text().strip().split())
                    if clean_text:  # Only add non-empty headings
                        url_data["extracted_headings"].append({
                            "type": tag,
                            "text": clean_text
                        })
            
            extracted_data.append(url_data)
            
        except Exception as e:
            extracted_data.append({
                "url": url,
                "error": str(e)
            })
    
    return extracted_data

@app.route('/extract', methods=['POST'])
@require_api_key
def extract():
    try:
        data = request.get_json()
        urls = data.get('urls') or data.get('url')
        heading_types = data.get('heading_types')
        
        if not urls:
            return jsonify({
                "status": "error",
                "message": "URLs are required"
            }), 400
            
        results = extract_headings(urls, heading_types)
        
        return jsonify({
            "status": "success",
            "data": results
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    app.run(host=host, port=port) 
