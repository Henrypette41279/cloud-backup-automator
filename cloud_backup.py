import os
import sys
from datetime import datetime

try:
    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError
except ImportError:
    print("boto3 is required. Install it with: pip install boto3")
    sys.exit(1)


class CloudBackupAutomator:
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.s3 = boto3.client("s3", region_name=region)

    def ensure_bucket_exists(self):
        """Check if bucket exists, create it if it doesn't."""
        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
            print(f"Bucket '{self.bucket_name}' already exists.")
        except ClientError:
            print(f"Creating bucket '{self.bucket_name}'...")
            self.s3.create_bucket(Bucket=self.bucket_name)
            print("Bucket created successfully.")

    def backup_file(self, local_path: str, s3_key: str = None):
        """Upload a single file to S3."""
        if not os.path.isfile(local_path):
            print(f"File not found: {local_path}")
            return False

        if s3_key is None:
            s3_key = os.path.basename(local_path)

        try:
            self.s3.upload_file(local_path, self.bucket_name, s3_key)
            print(f"Uploaded: {local_path} -> s3://{self.bucket_name}/{s3_key}")
            return True
        except NoCredentialsError:
            print("AWS credentials not found. Run 'aws configure' first.")
            return False
        except ClientError as e:
            print(f"Upload failed: {e}")
            return False

    def backup_folder(self, folder_path: str, prefix: str = "backup"):
        """Recursively upload all files in a folder to S3, organized by date."""
        if not os.path.isdir(folder_path):
            print(f"Folder not found: {folder_path}")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d")
        uploaded, failed = 0, 0

        for root, _, files in os.walk(folder_path):
            for filename in files:
                local_path = os.path.join(root, filename)
                relative_path = os.path.relpath(local_path, folder_path)
                s3_key = f"{prefix}/{timestamp}/{relative_path}"

                if self.backup_file(local_path, s3_key):
                    uploaded += 1
                else:
                    failed += 1

        print(f"\nBackup complete. Uploaded: {uploaded}, Failed: {failed}")

    def list_backups(self, prefix: str = "backup"):
        """List all backed-up files under a given prefix."""
        response = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
        objects = response.get("Contents", [])

        if not objects:
            print("No backups found.")
            return

        print(f"\n--- Backups in '{self.bucket_name}' ---")
        for obj in objects:
            size_kb = obj["Size"] / 1024
            print(f"{obj['Key']}  ({size_kb:.1f} KB)  Last modified: {obj['LastModified']}")


def main():
    print("=== Cloud Storage Backup Automator ===\n")
    bucket_name = input("Enter your S3 bucket name: ").strip()
    folder_to_backup = input("Enter the local folder path to back up: ").strip()

    automator = CloudBackupAutomator(bucket_name)
    automator.ensure_bucket_exists()
    automator.backup_folder(folder_to_backup)
    automator.list_backups()


if __name__ == "__main__":
    main()
