#
# copyright (c) 2018 east301
#
# This software is released under the MIT License.
# http://opensource.org/licenses/mit-license.php
#
# ==========
# Makefile
#

.PHONY: build upload

build:
	pip install setuptools_scm wheel
	rm -rf dist || true
	python3 setup.py bdist_wheel

upload:
	pip install twine
	twine upload dist/gpipe-*-py3-none-any.whl
