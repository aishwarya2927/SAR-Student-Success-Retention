from agents.intent_router import classify_intent

questions = [
    "Why is my attendance low?",
    "How can I become an AI Engineer?",
    "Why is my risk score high?",
    "Do you have scholarships?",
    "What is attendance policy?"
]

for q in questions:
    print(q)
    print(classify_intent(q))
    print("----------------------")