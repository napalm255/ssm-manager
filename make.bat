cd ssm-manager
pyinstaller --onedir --noconsole --clean ^
  --add-data "static:static" ^
  --add-data "templates:templates" ^
  --add-data "splash.jpg:." ^
  --icon="./static/favicon.ico" ^
  --splash="./splash.jpg" ^
  --name="SSM-Manager" ^
  app.py
