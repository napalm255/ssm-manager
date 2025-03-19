cd ssm-manager
pyinstaller --onedir --noconsole --clean --noconfirm ^
  --add-data "static:static" ^
  --add-data "templates:templates" ^
  --icon="static/favicon.ico" ^
  --name="SSM-Manager" ^
  app.py
