from app import app

with app.app_context():
    for rule in app.url_map.iter_rules():
        methods = ",".join(rule.methods)
        print(f"{rule.endpoint:30} -> {rule} [{methods}]")
