# Copyright (c) 2022, Katzen48 and contributors
# For license information, please see license.txt

from email.utils import formatdate
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, formatdate, getdate, today
import requests
import json

token_url = (
	"https://api-m.paypal.com/v1/oauth2/token?grant_type=client_credentials"
)
transactions_url = 'https://api-m.paypal.com/v1/reporting/transactions'

class PayPalReconciliationSettings(Document):
	pass

@frappe.whitelist()
def sync_transactions(bank_account):
	frappe.logger().info("Synchronizing PayPal transactions for Bank Account " + bank_account)

	start_date = formatdate(add_days(today(), -31), "YYYY-MM-dd") + "T00:00:00.000Z"
	end_date = formatdate(add_days(today(), -1), "YYYY-MM-dd") + "T23:59:59.999Z"

	try:
		transactions = get_transactions(start_date=start_date, end_date=end_date)

		result = []
		for transaction in reversed(transactions):
			result += new_bank_transaction(bank_account, transaction)

		if result:
			last_transaction_date = frappe.db.get_value("Bank Transaction", result.pop(), "date")

			frappe.logger().info("Added PayPal transactions for" + bank_account)

			frappe.db.set_value(
				"Bank Account", bank_account, "last_integration_date", last_transaction_date
			)

	except Exception:
		frappe.log_error(frappe.get_traceback(), _("PayPal Transactions Sync Error"))

def new_bank_transaction(bank_account, transaction):
	result = []
	
	withdrawal_amount = 0
	deposit_amount = 0
	currency_code = transaction['transaction_info']['transaction_amount']['currency_code']
	if float(transaction['transaction_info']['transaction_amount']['value']) < 0.00:
		withdrawal_amount = abs(float(transaction['transaction_info']['transaction_amount']['value']))
	else:
		deposit_amount = abs(float(transaction['transaction_info']['transaction_amount']['value']))

	if not frappe.db.exists("Bank Transaction", dict(transaction_id=transaction['transaction_info']['transaction_id'])):
		try:
			new_transaction = frappe.get_doc(
				{
					"doctype": "Bank Transaction",
					"date": getdate(transaction['transaction_info']['transaction_initiation_date'].split('T')[0]),
					"status": "Settled",
					"bank_account": bank_account,
					"deposit": deposit_amount,
					"withdrawal": withdrawal_amount,
					"currency": currency_code,
					"transaction_id": transaction['transaction_info']['transaction_id'],
					"reference_number": transaction['transaction_info'].get('paypal_reference_id', False) or transaction['transaction_info']['transaction_id'],
					"description": transaction['payer_info'].get('email_address', False) or ''
				}
			)
			new_transaction.insert()
			new_transaction.submit()

			result += new_transaction.name

		except Exception:
			frappe.throw(title=_("Bank transaction creation error"))
		
	return result

def get_transactions(start_date=None, end_date=None):
	transactions = []

	page = 1
	while True:
		result, total_pages = request_transactions(start_date=start_date, end_date=end_date, page=page)
		transactions += result
		if page >= total_pages:
			break
		else:
			page += 1
	
	return transactions

def request_transactions(start_date=None, end_date=None, page=None):
	payload='Content-Type=application/json'
	headers={
		'Content-Type': 'application/json',
		'Authorization': 'Bearer ' + get_token()
	}

	url = transactions_url + '?start_date=' + start_date + '&end_date=' + end_date + '&page_size=500&fields=all&transaction_status=S&transaction_status=V' + '&page=' + str(page)
	response = requests.request('GET', url, headers=headers, data=payload)
	result = json.loads(response.text)

	return result['transaction_details'], result['total_pages']

def get_token():
	settings = frappe.get_doc("PayPal Reconciliation Settings", "PayPal Reconciliation Settings")

	response = requests.request('POST', token_url, data={'grant_type': 'client_credentials'}, auth=(
		settings.client_id, settings.get_password(fieldname="client_secret", raise_exception=False)
	))
	result = json.loads(response.text)
	return result['access_token']

def automatic_synchronization():
	settings = frappe.get_doc("PayPal Reconciliation Settings", "PayPal Reconciliation Settings")
	if settings.client_id and settings.get_password(fieldname="client_secret", raise_exception=False):
		enqueue_synchronization()

@frappe.whitelist()
def enqueue_synchronization():
	bank_accounts = frappe.get_all(
		"Bank Account", filters={"is_paypal_account": ["=", True]}, fields=["name"]
	)

	for bank_account in bank_accounts:
		frappe.enqueue(
			"paypal_reconciliation.paypal_reconciliation.doctype.paypal_reconciliation_settings.paypal_reconciliation_settings.sync_transactions",
			bank_account=bank_account.name
		)
