import re

filepath = r"C:\Users\ASUS\.gemini\antigravity\brain\6dbf7a68-9d59-4377-a872-3dd93568bb0f\.system_generated\logs\overview.txt"

with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# Let's search for "conic" or "gradient" or "chat-input-wrapper"
for m in re.finditer(r'chat-input-wrapper|conic|gradient-angle', content, re.IGNORECASE):
    idx = m.start()
    print(f"Match at {idx}:")
    print(content[max(0, idx-500):min(len(content), idx+1500)])
    print("="*80)
