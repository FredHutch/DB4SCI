import os
import sys
import subprocess as sp
import datetime
from . import mydb_config
from . import admin_db

"""
audit MyDB backups. Check MyDB Admin backup logs.
verify that each data base in active state has been
backed up.

import mydb.backup_util as backup_util
rpt = backup_util.backup_audit()
print(rpt[1])

"""


def get_backup_log(info, c_id):
    """query backup log for history of error messages"""
    result = admin_db.backup_taillog(c_id, tail=10)
    start_format = "{:5} {}  command: {}\n"
    end_format = "{:5} {}  Error: {}\n\n"
    msg = ""
    for row in result:
        if row.state == "start":
            msg += start_format.format(row.state, row.ts, row.command)
        else:
            msg += end_format.format(row.state, row.ts, row.err_msg)
    return msg


def check_backup_logs(info, c_id):
    """query backup logs
    verify that backup started and ended
    verify that backup was run within policy (Daily or Weekly)
    """
    msg = "%-30s %-10s %-6s " % (info["Name"], info["dbengine"], info["BACKUP_FREQ"])
    policy = info["BACKUP_FREQ"]
    now = datetime.datetime.now()
    if policy == "Daily":
        since = now - datetime.timedelta(days=1)
    elif policy == "Weekly":
        since = now - datetime.timedelta(days=7)
    result = admin_db.backup_lastlog(c_id)
    start_ts = 0
    start_id = end_id = None
    out_of_policy = False
    for row in result:
        if row.state == "start":
            start_ts = row.ts
            start_id = row.backup_id
            if row.ts < since:
                out_of_policy = True
        if row.state == "end":
            end_ts = row.ts
            end_id = row.backup_id
            url = row.url
    if start_id and end_id:
        if start_id == end_id:  # this is good
            duration = end_ts - start_ts
            if out_of_policy:
                msg += "%s Out of Policy (%s)\n" % (start_ts, now - start_ts)
            else:
                msg += "%s Good   (%s)\n" % (start_ts, duration)
        else:
            msg += "%s Backup Running\n" % start_ts
    else:
        if out_of_policy:
            msg += "%s Out of Policy; Started but did not finish!\n" % start_ts
        else:
            msg += "%s Started but did not finish!\n" % start_ts
    return msg

    header = "Backup Logs for {}\n\n".format(data["Info"]["Name"])
    header += "%-26s Error Msg" % ("Start Time (UTC)")
    if "BACKUP_FREQ" in data["Info"]:
        policy = data["Info"]["BACKUP_FREQ"]
    else:
        msg += "Extreme Badness: Backup policy not set for %s.\n" % name
        return (header, msg)
    if policy == "Daily" or policy == "Weekly":
        status = check_backup_logs(data["Info"], c_id)
        msg += status


def backup_report(c_id, name):
    data = admin_db.get_container_data(name, c_id)
    header = "Backup report for {}".format(data["Info"]["Name"])
    if c_id is None:
        state_info = admin_db.get_container_state(name)
        c_id = state_info.c_id
    msg = get_backup_log(data["Info"], c_id)
    return (header, msg)


def backup_audit_all():
    """inspect the backup logs for every container that is running.
    get list of all "running" containers
    inspect backup logs based on backup policy for each container
    """
    check_list = []
    containers = admin_db.list_active_containers()
    header = "%-30s %-10s %-6s %-26s Status (Duration)" % (
        "Container",
        "DB Type",
        "Policy",
        "Start Time (UTC)",
    )
    msg = ""
    for c_id, con_name in containers:
        data = admin_db.get_container_data("", c_id)
        if "BACKUP_FREQ" in data["Info"]:
            policy = data["Info"]["BACKUP_FREQ"]
        else:
            msg += "Extreme Badness: Backup policy not set for %s.\n" % con_name
            continue
        if policy == "Daily" or policy == "Weekly":
            status = check_backup_logs(data["Info"], c_id)
            msg += status
    return (header, msg)


def backup_audit(name=None, c_id=None):
    if name:
        (header, body) = backup_report(None, name)
    if c_id:
        (header, body) = backup_report(c_id, None)
    else:
        (header, body) = backup_audit_all()
    return (header, body)


def backup_to_s3(dump_cmd, s3_uri, env):
    """
    Streams a database dump directly to S3.
    :param dump_cmd: List of strings (e.g., ['pg_dump', 'mydb'])
    :param s3_uri: String (e.g., 's3://bucket/path/file.sql')
    :env the environment to pass to commands
    """
    print(f"--- Starting backup to {s3_uri} ---")
    full_env = os.environ.copy()
    full_env.update(env)

    try:
        # 1. Start the Dump Process
        p1 = sp.Popen(dump_cmd, stdout=sp.PIPE, stderr=sp.PIPE, text=True, env=full_env)
        assert p1.stdout is not None

        # 2. Start the AWS Process (reads from p1.stdout)
        p2 = sp.Popen(
            ['aws', 's3', 'cp', '-', s3_uri],
            stdin=p1.stdout,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
            text=True,
            env=full_env,
        )

        # Allow p1 to receive a SIGPIPE if p2 exits early
        p1.stdout.close()

        # 3. Capture results
        # communicate() waits for the process to finish
        stdout_aws, stderr_aws = p2.communicate()
        _, stderr_dump = p1.communicate()

        # 4. Error Checking
        if p1.returncode != 0:
            print(f"CRITICAL: Dump command failed (Code {p1.returncode})")
            print(f"Dump Error: {stderr_dump}")
            return False, stderr_dump

        if p2.returncode != 0:
            print(f"CRITICAL: AWS Upload failed (Code {p2.returncode})")
            print(f"AWS Error: {stderr_aws}")
            return False, stderr_aws

        print(f"SUCCESS: {stdout_aws.strip()}")
        return True, stdout_aws.strip()

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False, str(e)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        (header, body) = backup_audit(name=sys.argv[1])
    else:
        (header, body) = backup_audit()
    print(header)
    print(body)
