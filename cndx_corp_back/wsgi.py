import os

from cndx_corp_back import create_app

application_env = os.environ.get("FLASK_ENV", "prod")

application = create_app(application_env)

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5000, debug=False)
