from pathlib import Path
import yaml

p = Path('c:/Users/Bonix/Desktop/atv611/radar-enem-network/docker-compose.yml')
text = p.read_text(encoding='utf-8')
data = yaml.safe_load(text)
print('YAML_OK', sorted(data.keys()))
print('services', list(data.get('services', {}).keys()))
print('networks', list(data.get('networks', {}).keys()))
