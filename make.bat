cd ssm-manager
pyinstaller --onedir --noconsole --add-data "static:static" --add-data "templates:templates" --add-data "splash.jpg:." --add-data "icon.ico:." --icon=icon.ico --name="SSM-Manager" --clean app.py
