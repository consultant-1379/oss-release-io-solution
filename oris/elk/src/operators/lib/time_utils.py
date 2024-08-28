'''import parse'''
from dateutil.parser import parse
from datetime import datetime, timedelta


class TimeCalculator:

    def parseTimeStamp(self, timeStamp):
        return None if timeStamp is None else parse(timeStamp)

    def _toDateString(self, dateObject, formatStr="%Y-%m-%dT%H:%M:%S.000%z"):
        return dateObject.astimezone().strftime(formatStr)

    def getDuration(self, timeStampStart, timeStampEnd):
        if (timeStampStart is None or timeStampEnd is None):
            return None
        else:
            return int((timeStampEnd - timeStampStart).total_seconds() * 1000)

    def getHoursOpen(self, timeStampStart, timeStampEnd):
        duration_seconds = (timeStampEnd - timeStampStart).total_seconds()
        hours = duration_seconds / 3600
        if hours < 24:
            return round(hours / 24, 3)

    def getDaysOpen(self, timeStampStart, timeStampEnd):
        return ((timeStampEnd - timeStampStart).days)

    def getCurrentDate(self, timeStamp):
        return None if timeStamp is None else self.parseTimeStamp(self._toDateString(timeStamp))

    def _toMiliSeconds(self, timestamp):
        time_obj = datetime.strptime(timestamp, "%H:%M:%S")
        total_seconds = time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
        milliseconds = total_seconds * 1000
        return milliseconds

    def yesterDayDate(self):
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        endTime_day = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        startTime_day = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        startTime = startTime_day.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        endTime = endTime_day.strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-3] + 'Z'
        return startTime, endTime

    def stageTimeInMilliSeconds(self, time):
        dt = parse(time)
        # Convert the datetime object into milliseconds
        milliseconds = int(dt.timestamp() * 1000)
        return milliseconds

    def parseTimeStampToMilis(self, time):
        # Convert timestamp string to a datetime object
        datetimeObj = datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%f")
        # Get the timestamp in seconds (epoch time)
        timeStamp = datetimeObj.timestamp()
        # Convert timestamp to milliseconds and round for microseconds
        milliseconds = int(round(timeStamp * 1000))
        return milliseconds
