import datetime
import os.path
import pytz

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta

# If modifying these scopes, delete the file token.json.
SCOPE = ["https://www.googleapis.com/auth/calendar.readonly"]


def authenticate_google_calendar():
  """Shows basic usage of the Google Calendar API.
  Prints the start and name of the next 10 events on the user's calendar.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPE)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPE
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("calendar", "v3", credentials=creds)
    return service
  except HttpError as error:
    print(f"An error occurred: {error}")


def parse_event_time(event_time, tz):
    """ Function to handle the date-time string properly. 
        We need to accommodate different formats for all-day events, timezones, and events with specific start and end times"""
    if 'dateTime' in event_time:
        # Replace 'Z' with '+00:00' for UTC
        date_str = event_time['dateTime']
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        return datetime.fromisoformat(date_str).astimezone(tz)
    elif 'date' in event_time:
        return tz.localize(datetime.fromisoformat(event_time['date']))
    else:
        raise ValueError("Invalid event time format")


def get_free_time_slots(start_date, end_date, time_pockets, time_zone):
    #Authenticate user access
    service = authenticate_google_calendar()

    #get timezone 
    tz = pytz.timezone(time_zone)
    #parse the dates
    start_date = tz.localize(datetime.strptime(start_date, '%Y-%m-%d'))
    end_date = tz.localize(datetime.strptime(end_date, '%Y-%m-%d'))

    #get a list of events between two dates from calendar
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_date.isoformat(),
        timeMax=end_date.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    #identify and track free time slots
    free_slots = []
    for time_pocket in time_pockets:
        pocket_start = datetime.strptime(time_pocket['start'], '%H:%M').time()
        pocket_end = datetime.strptime(time_pocket['end'], '%H:%M').time()

        day = start_date
        while day < end_date:
            # Make day_start and day_end timezone-aware
            day_start = tz.localize(datetime.combine(day, pocket_start))
            day_end = tz.localize(datetime.combine(day, pocket_end))

            is_free = True
            for event in events:
                event_start = parse_event_time(event['start'], tz)
                event_end = parse_event_time(event['end'], tz)

                if not (event_end <= day_start or event_start >= day_end):
                    is_free = False
                    break

            if is_free:
                free_slots.append({'date': day.strftime('%Y-%m-%d'), 'start': pocket_start.strftime('%H:%M'), 'end': pocket_end.strftime('%H:%M')})

            day += timedelta(days=1)

    return free_slots


if __name__ == "__main__":
  # Authenticate and create a service
    start_date = '2023-11-10'
    end_date = '2023-11-12'
    time_pockets = [{'start': '09:00', 'end': '12:00'}, {'start': '14:00', 'end': '17:00'}]
    time_zone = 'Africa/Lagos'

    free_slots = get_free_time_slots(start_date, end_date, time_pockets, time_zone)
    print("Free Slots:", free_slots)
