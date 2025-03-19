rmdir /s /q cache
del /q app.log
del /q preferences.json

cd ssm-manager
rmdir /s /q build
rmdir /s /q dist
rmdir /s /q __pycache__
del /q ssm-manager.spec

pyinstaller --onedir --noconsole --clean --noconfirm ^
  --add-data "static:static" ^
  --add-data "templates:templates" ^
  --icon="static/favicon.ico" ^
  --name="SSM-Manager" ^
  app.py
