cd ssm-manager
pyinstaller --onedir --noconsole --clean --noconfirm ^
  --add-data "static:static" ^
  --add-data "templates:templates" ^
  --icon="ssm-manager/static/favicon.ico" ^
  --name="SSM-Manager" ^
  app.py
