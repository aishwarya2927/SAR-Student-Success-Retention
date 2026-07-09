# quick check
from tools.get_risk_profile import get_risk_profile
profile = get_risk_profile("STU202600011")
print(profile)
print(type(profile.get("top_factors")))
if profile.get("top_factors"):
    print(profile["top_factors"][0])