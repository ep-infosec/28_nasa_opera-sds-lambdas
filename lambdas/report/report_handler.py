from __future__ import print_function

import os
import json
import requests

from datetime import datetime, timedelta

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
JOB_NAME_DATETIME_FORMAT = "%Y%m%dT%H%M%S"

print("Loading Lambda function")

if "MOZART_URL" not in os.environ:
    raise RuntimeError("Need to specify MOZART_URL in environment.")
MOZART_URL = os.environ["MOZART_URL"]
JOB_SUBMIT_URL = "%s/api/v0.1/job/submit" % MOZART_URL


def convert_datetime(datetime_obj, strformat=DATETIME_FORMAT):
    """
    Converts from a datetime string to a datetime object or vice versa
    """
    if isinstance(datetime_obj, datetime):
        return datetime_obj.strftime(strformat)
    return datetime.strptime(str(datetime_obj), strformat)


def submit_job(job_name, job_spec, job_params, queue, tags, priority=0):
    """Submit job to mozart via REST API."""

    # setup params
    params = {
        "queue": queue,
        "priority": priority,
        "tags": json.dumps(tags),
        "type": job_spec,
        "params": json.dumps(job_params),
        "name": job_name,
    }

    # submit job
    print("Job params: %s" % json.dumps(params))
    print("Job URL: %s" % JOB_SUBMIT_URL)
    req = requests.post(JOB_SUBMIT_URL, data=params, verify=False)

    print("Request code: %s" % req.status_code)
    print("Request text: %s" % req.text)

    if req.status_code != 200:
        req.raise_for_status()
    result = req.json()
    print("Request Result: %s" % result)

    if "result" in result.keys() and "success" in result.keys():
        if result["success"] is True:
            job_id = result["result"]
            print("submitted job: %s job_id: %s" % (job_spec, job_id))
        else:
            print("job not submitted successfully: %s" % result)
            raise Exception("job not submitted successfully: %s" % result)
    else:
        raise Exception("job not submitted successfully: %s" % result)


def lambda_handler(event, context):
    """
    This lambda handler calls submit_job with the job type info
    and dataset_type set in the environment
    """

    print("Got event of type: %s" % type(event))
    print("Got event: %s" % json.dumps(event))
    print("Got context: %s" % context)
    print("os.environ: %s" % os.environ)

    # Allow us to specify a user given start and end time for testing purposes.
    # Otherwise, we default to the current date time.
    start_time = os.getenv("USER_START_TIME")
    end_time = os.getenv("USER_END_TIME")

    # The end time of the report will be the current time.
    if end_time:
        end_time = convert_datetime(end_time)
    else:
        end_time = datetime.utcnow()
        # This ensures we generate reports with consistent time ranges.
        end_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # The start time of the report can start 24 hours ago with the assumption that
    # the timer kicks this off once per day at the same time each day.
    if start_time:
        start_time = convert_datetime(start_time)
    else:
        start_time = end_time - timedelta(hours=24)

    job_type = os.environ['JOB_TYPE']
    job_release = os.environ['JOB_RELEASE']
    queue = os.environ['JOB_QUEUE']
    report_name = os.environ['REPORT_NAME']
    report_format = os.environ['REPORT_FORMAT']
    osl_bucket_name = os.environ['OSL_BUCKET_NAME']
    osl_staging_area = os.environ['OSL_STAGING_AREA']
    job_spec = "job-%s:%s" % (job_type, job_release)
    job_params = {
        "report_name": report_name,
        "report_format": report_format,
        "osl_bucket_name": osl_bucket_name,
        "osl_staging_area": osl_staging_area,
        "start_time": convert_datetime(start_time),
        "end_time": convert_datetime(end_time)
    }
    tags = ["timer-{}".format(report_name)]
    job_name = "timer-{}-{}_{}".format(report_name,
                                        convert_datetime(start_time, JOB_NAME_DATETIME_FORMAT),
                                        convert_datetime(end_time, JOB_NAME_DATETIME_FORMAT))
    # submit mozart job
    submit_job(job_name, job_spec, job_params, queue, tags)
