from flask import Flask, request, jsonify, send_file
import requests
from bs4 import BeautifulSoup
from flask_cors import CORS
import urllib3
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
CORS(app)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 