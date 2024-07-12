# Datasets Repository

## Overview
This repository is dedicated to hosting datasets for the project. As project member, ou can upload, push, and store datasets of reasonable size directly here. For larger datasets, please refer to the specific links provided in the [Datasets Sheet](https://docs.google.com/spreadsheets/d/1gRhMfJx5t2Sv8BTA5kxxmXGUHibiWPZ9FXys-BSSS2o/edit#gid=530288791).

## Guidelines for Using This Repository
- **Reasonable Size Datasets:** You can directly upload and push datasets that are of reasonable size (e.g., up to 500 MB) to this repository. Examples of dataset types include:
  - CSV files
  - JSON files
  - Excel files
  - Parquet files
  - SQLite databases
  
- **Large Datasets:** For large datasets, refer to the [Datasets Sheet](https://docs.google.com/spreadsheets/d/1gRhMfJx5t2Sv8BTA5kxxmXGUHibiWPZ9FXys-BSSS2o/edit#gid=530288791) where specific links to external storage or other resources are provided.

## Using DagsHub Storage
DagsHub automatically configures a remote object storage for every repository with 10 GB of free space. You can use it without needing a DevOps background or a billing account in a cloud provider. This storage can serve as a general-purpose storage bucket, and you can use DVC for advanced versioning capabilities.

### Connect External Storage Buckets
You can also connect your own storage bucket to get all the benefits of DagsHub Storage. For instructions on how to do this, refer to the [guide for connecting external storage](https://dagshub.com/docs/storage/connect_external_storage).

### What You Get with DagsHub Storage
Every repository comes with two storage options:
1. **An S3 Compatible Storage Bucket**
2. **A DVC Remote**

You can use your access token to interact with either of them. Access control is based on the repository's access settings—only repository writers can modify the data, and if your repository is private, you control who can view and read the files.

Both storages are accessible through the repository's web interface and the Content API. DVC data will appear alongside git repository files whenever DVC pointer files (.dvc) are pushed to git. The bucket can be explored through the "DagsHub Storage" entry in the "Storage Buckets" section on your repository's homepage.

The DVC remote and the bucket operate independently of each other.

## Recommended Information
For more information on how to utilize DagsHub Storage effectively, visit the [DagsHub Storage documentation](https://dagshub.com/docs/storage/).

If you have any questions or need assistance, please reach out to the project maintainers.
