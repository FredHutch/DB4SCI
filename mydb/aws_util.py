import os
import subprocess
import time

import boto3
from botocore.exceptions import ClientError

from . import mydb_config


def create_backup_prefix(Name):
    """Create prefix for aws s3 backup
    Returns: (backup_id, prefix)
    backup_id format: YYYY-MM-DD_HH:MM:SS
    prefix format: /Name/YYYY-MM-DD_HH:MM:SS/
    V1 used '/prod/` for prefix
    V2 use '/mydb/` for prefix
    """
    t = time.localtime()
    backup_id = f"{t[0]}-{t[1]:02d}-{t[2]:02d}_{t[3]:02d}:{t[4]:02d}:{t[5]:02d}"
    prefix = f"/mydb/{Name}/{backup_id}/"

    return backup_id, prefix


def list_s3(Name):
    """return list of backup prefixes for a container.
    Note each prefix is PIT backup date, the backup files are
    in the PIT
    """
    cmd = (
        # TODO FIXME adjust prefix if we are running in dev?
        f"{mydb_config.aws} s3 ls --recursive {mydb_config.AWS_BUCKET_NAME}/{mydb_config.s3_prefix_prod}/{Name}"
    )
    print(f"DEBUG: {__file__}.select list_s3 cmd: {cmd}")
    backups = os.popen(cmd).read().strip()
    return backups


def list_s3_prefixes(Name):
    cmd = f"{mydb_config.aws} s3 ls {mydb_config.AWS_BUCKET_NAME}/prod/{Name}/"
    backups = os.popen(cmd).read().strip()
    lines = backups.split("\n")
    return lines


def lastbackup_s3_prefix(Name, target):
    """Find the latest backup archive file for a container by searching AWS S3.

    AWS output format: "2025-01-15 14:30:00  12345678 prod/container_name/2025-01-15_14:30:00/*"
    """
    s3_cmd = f"{mydb_config.aws} s3 ls --recursive {mydb_config.AWS_BUCKET_NAME}/prod/{Name}/"
    command = s3_cmd.split()
    print(f"DEBUG aws_util.lastbackup_s3_prefix: cmd = {command}")

    # Execute the command
    try:
        p1 = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        p2 = subprocess.Popen(
            ["sort"],
            stdin=p1.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        p1.stdout.close()
        result = p2.communicate()
        if p2.returncode == 0:
            for line in result[0].strip().split("\n"):
                if line.endswith(target):
                    prefix = line.strip().split()[3]
            if not prefix:
                return f"No backup found for {Name} - Looking for {target} in {s3_cmd}"
            return prefix
        else:
            return "Error lastbackup_s3_prefix: "
    except subprocess.CalledProcessError as e:
        return f"s3 error cmd: {command}\n error occurred: {e}"


def list_s3_files(s3_url):
    """
    List all files in an S3 bucket with a given prefix.

    Args:
        s3_url (str): Full S3 URL including bucket and prefix
                     Example: "s3://bucket-name/prefix/path/"

    Returns:
        list: List of full S3 URLs for each file, or empty list if error

    Example:
        >>> files = list_s3_files("s3://my-bucket/backups/2025-01-15/")
        >>> print(files)
        ['s3://my-bucket/backups/2025-01-15/file1.sql',
         's3://my-bucket/backups/2025-01-15/file2.dump']
        response['Contents'] = {
            'Key': 'prod/gecco/gecco_2025-12-09_19-46/dump',
            'LastModified': datetime.datetime(2025, 12, 11, 2, 7, 16, tzinfo=tzutc()),
            'ETag': '"939837938b8c1dfc41bf5133849da7b4-9"',
            'ChecksumAlgorithm': ['CRC64NVME'],
            'ChecksumType': 'FULL_OBJECT',
            'Size': 73889487,
            'StorageClass': 'STANDARD'
        }
    """
    # Parse the S3 URL to extract bucket and prefix
    if not s3_url.startswith("s3://"):
        print(f"Error: Invalid S3 URL format: {s3_url}")
        return []

    # Remove 's3://' prefix
    path = s3_url[5:]

    # Split into bucket and prefix
    parts = path.split("/", 1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""

    s3_client = boto3.client("s3")

    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

        file_list = []
        if "Contents" in response:
            for obj in response["Contents"]:
                # Reconstruct full S3 URL
                file_url = f"s3://{bucket_name}/{obj['Key']}"
                file_list.append(file_url)

        return file_list

    except ClientError as e:
        print(f"Error accessing S3 bucket: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []


def setup_parser():
    parser = argparse.ArgumentParser(
        description="aws_util modue test",
        usage="%(prog)s [options] module_name",
    )
    parser.add_argument(
        "--last_backup", type=str, required=False, help="get last S3 backup object"
    )
    return parser.parse_args()


def main():
    args = setup_parser()
    if args.last_backup:
        print(f"Testing lastbackup_s3_prefix, target: {args.last_backup}")
        last_backup = lastbackup_s3_prefix("gecco_gizmo", args.last_backup)
        print(f"Last backup found: {last_backup}")
    else:
        print("No action specified")


if __name__ == "__main__":
    import argparse

    main()
