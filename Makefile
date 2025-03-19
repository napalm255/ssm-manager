build:
	pyinstaller --onedir --noconsole \
		--add-data "static/css:static/css" --add-data "static/js:static/js" \
		--add-data "templates:templates" --add-data "preferences.json:." \
		--add-data "image:image" --add-data "splash.jpg:." \
		--add-data "icon.ico:." --icon=icon.ico \
		--name="SSM-Manager" \
		--clean app.py

clean:
	rm -rf app.log *.spec __pycache__ build dist
