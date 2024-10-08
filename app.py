import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from api import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, ssl_context=('cert.pem', 'key.pem'))