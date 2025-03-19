cd ssm-manager
pyinstaller --onedir --noconsole --add-data "static:static" --add-data "templates:templates" --add-data "splash.jpg:." --add-data "static/favicon.ico:icon.ico" --icon="static/favicon.ico" --name="SSM-Manager" --clean --noupx app.py
