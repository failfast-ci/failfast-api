import yaml

from ffci.config import FFCONFIG

print(yaml.safe_dump(FFCONFIG.settings, indent=2))
