from flask import Flask, request, redirect
import os
from api.future_routes import future_blueprint
app = Flask(__name__)

# Register the blueprints
app.register_blueprint(future_blueprint, url_prefix='/api')

@app.before_request
def redirect_to_api():
    if not request.path.startswith('/api'):
        return redirect('/api', code=301)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

