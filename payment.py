import csv
from urllib.parse import unquote
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

RATES_DATA_FILE = "rates.csv"
OPERATION_LOG = "records.csv"

# Might be invalid!
TEAMLEADER_AUTH_CODE = None
TEAMLEADER_API_TOKEN = None

TEAMLEADER_CLIENT_ID = "515eaf0ea663dfb3f0731caf03c62c6b"
TEAMLEADER_SECRET = "2fab294aedde5a402c7ef246c6420b52"

# Authorization flow
#
# 1. Authorize plugin to use account data (expires after 10 minutes):
# GET https://app.teamleader.eu/oauth2/authorize?response_type=code&redirect_url=https://localhost&client_id=[ID]
# ->
# REDIRECT https://localhost?code=[CODE]
# [CODE] == Authorization code
#
# 2. Obtain access token (expires after 60 minutes):
# POST https://app.teamleader.eu/oauth2/access_token?grant_type=authorization_code&redirect_url=https://localhost&client_id=[ID]&client_secret=[SECRET]&code=[CODE]
# ->
# RESPONSE JSON dictionary with keys [token_type, expires_in, access_token, refresh_token]
#
# 3. The token type `bearer` must be added to the next API requests (GET):
# `Authorization: Bearer [ACCESS_TOKEN]`

def authorize_teamleader():
	# https://app.teamleader.eu/oauth2/authorize?response_type=code&redirect_url=https%253A%252F%252Flocalhost&client_id=515eaf0ea663dfb3f0731caf03c62c6b
	pass

def access_teamleader():
	headers = {
		'content-type': 'application/json'
	}
	data = {
		'client_id': TEAMLEADER_CLIENT_ID,
		'client_secret': TEAMLEADER_SECRET,
		'code': unquote(TEAMLEADER_AUTH_CODE),
		'grant_type': "authorization_code",
		'redirect_uri': 'https://localhost',
	}
	r = requests.post('https://app.teamleader.eu/oauth2/access_token', data=data)
	print("DEBUG", r.json())

	if r.status_code != requests.codes.ok:
		print("ERROR", "Access code response not OK!")
		return False, None

	return True, r.json()['access_token']

def teamleader_requester(api_token):
	def _api_get(endpoint, body, headers={}):
		url = "https://api.teamleader.eu/{}".format(endpoint)
		auth_code = 'Bearer {}'.format(api_token)
		headers.update({'Authorization': auth_code})

		r = requests.get(url, headers=headers, data=body)
		print("TRACE", "GET status", r.status_code)
		return r.json()['data']
	return _api_get

#################################

def stripe_do_payment(stripe_id, amount):
	# TODO(Bert): Actual implementation of paying through Stripe
	return True

#################################

def main():
	if not TEAMLEADER_API_TOKEN:
		access_status, api_token = access_teamleader()
		if not access_status:
			return
	else:
		api_token = TEAMLEADER_API_TOKEN

	print("INFO", "API token {}".format(api_token))
	api_gateway = teamleader_requester(api_token)
	today = date.today()

	today_timesheets = load_time_sheets_for_day(api_gateway, today)

	rates = load_rates()
	print("DEBUG", rates)

	process_payments(rates, today_timesheets)


def load_rates():
	rates = {}
	with open(RATES_DATA_FILE, newline='', mode='rt') as ratesReader:
		rate_data = csv.DictReader(ratesReader)
		for row in rate_data:
			rates.update({row['teamleader_id']: {'rate': float(row['rate']), 'stripe_id': row['stripe_id']}})
	return rates

def load_time_sheets_for_day(api_gateway, today):
	print("DEBUG", today.isoformat())

	midnight_today = datetime.combine(today, datetime.min.time()).astimezone()
	tomorrow = today + timedelta(days=1)
	midnight_tomorrow = datetime.combine(tomorrow, datetime.min.time()).astimezone()

	print("INFO", "TODAY {} - TOMORROW {}".format(midnight_today.isoformat(), midnight_tomorrow.isoformat()))

	api_body = {
	'filter': {
		'started_after': midnight_today.isoformat(),
		'ended_before': midnight_tomorrow.isoformat(),
	},
	'sort': [{'field': 'started_on', 'order': 'asc'}]
	}
	time_sheets = api_gateway('timeTracking.list', api_body)
	print("DEBUG", "time sheets", time_sheets)
	# TODO(Bert): Manually filter sheets for provided day because
	# TeamLeader filters aren't intersecting!
	return time_sheets

def process_payments(rates, timesheets):
	write_header = not Path(OPERATION_LOG).is_file()
	id_counter = 0

	record_field_names = ['id', 'receiver', 'hours', 'payed']
	with open(OPERATION_LOG, newline='', mode='at') as records:
		record_writer = csv.DictWriter(records, fieldnames=record_field_names)
		if write_header:
			record_writer.writeheader()

		for sheet in timesheets:
			if not must_be_payed(sheet):
				continue

			teamleader_uid = sheet['user']['id']
			payment, hours, stripe_id = calculate_payment(rates, sheet)
			if not stripe_do_payment(stripe_id, payment):
				print("ERROR", "Stripe payment failed for TEAM-UID `{}` and STR-UID `{}`".format(teamleader_uid, stripe_id))
				continue

			record = {
				'id': id_counter,
				'receiver': stripe_id,
				'hours': hours,
				'payed': payment,
			}
			print("DEBUG", "new record", record)
			record_writer.writerow(record)


def must_be_payed(work_sheet):
	# Duration is in seconds
	print("DEBUG", work_sheet)
	print("DEBUG", work_sheet['duration'])
	work_duration = float(work_sheet['duration'])
	return work_duration <= (8*60*60)

def calculate_payment(rates, work_sheet):
	teamleader_uid = work_sheet['user']['id']
	stripe_id = rates[teamleader_uid]['stripe_id']
	rate = rates[teamleader_uid]['rate']
	hours = float(work_sheet['duration'])/(60*60)

	payment = rate*hours
	# Include additional costs here (Taxes)

	return payment, hours, stripe_id



if __name__ == '__main__':
	main()
