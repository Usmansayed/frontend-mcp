import importlib.metadata as m
import navigation
from pathlib import Path

print("nav", navigation.__file__)
print("ver", m.version("frontend-perception-engine"))
print("alias", m.version("frontend-mcp"))
p = Path(navigation.__file__).parent
print("r12", (p / "coordination_intelligence/artifacts/runtime/situation_policy_catalog.v1.yaml").exists())
text = (p / "mcp/handlers.py").read_text(encoding="utf-8")
for line in text.splitlines():
    if "server_version" in line:
        print(line.strip())
        break
