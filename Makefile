build:
	cd ssm-manager && \
	pyinstaller --onedir --noconsole --clean --noconfirm \
		--add-data "static:static" \
		--add-data "templates:templates" \
		--icon="static/favicon.ico" \
		--name="ssm-manager" \
		app.py

clean:
	rm -rf app.log *.spec __pycache__ build dist
