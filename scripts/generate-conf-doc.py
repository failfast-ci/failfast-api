import yaml
from hub2labhook.config import FFCONFIG


print(yaml.safe_dump(FFCONFIG.settings, indent=2))
