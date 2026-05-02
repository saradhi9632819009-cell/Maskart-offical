import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_content = re.sub(r'"price": \d+', r'"price": 10', content)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Prices updated successfully!")
