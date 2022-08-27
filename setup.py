from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in paypal_reconciliation/__init__.py
from paypal_reconciliation import __version__ as version

setup(
	name="paypal_reconciliation",
	version=version,
	description="Reconcile your PayPal Transactions with your bank transactions",
	author="Katzen48",
	author_email="admin@katzen48.de",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
