from enum import Enum

class Capability(str, Enum):
    MARKET_ANALYSIS = "market_analysis"
    BUSINESS_BLUEPRINTING = "business_blueprinting"

completed_tasks = {"business_blueprinting"}
layer = [Capability.MARKET_ANALYSIS, Capability.BUSINESS_BLUEPRINTING]

pending = [cap for cap in layer if cap not in completed_tasks]
print(pending)
