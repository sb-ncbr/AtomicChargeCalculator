# Content

- [api](./api/)
- [database](./db/)
- [examples](./examples/)
- [integrations](./integrations/)
- [life-science](./life-science/)
- [services](./services/)

# Environment variables
- `ACC_DB_URL` - PostgreSQL database connection string.
- `ACC_DATA_DIR` - Directory for storing uploaded files and calculation results.
- `ACC_EXAMPLES_DIR` - Directory for storing precalculated examples.
- `ACC_LOG_DIR` - Directory for storing logs.
- `ACC_USER_STORAGE_QUOTA_BYTES`- Maximum allowed storage used by a single authenticated user in bytes.
- `ACC_GUEST_FILE_STORAGE_QUOTA_BYTES` - Maximum allowed file storage space shared by all guest users.
- `ACC_GUEST_COMPUTE_STORAGE_QUOTA_BYTES` - Maximum allowed calculation storage space shared by all guest users.
- `ACC_MAX_FILE_SIZE_BYTES` - Maximum allowed size of a single file user can upload.
- `ACC_MAX_UPLOAD_SIZE_BYTES` - Maximum allowed sum of sizes of files user can upload in a single request.
- `ACC_MAX_WORKERS` - Maximum threadpool workers.
- `ACC_MAX_CONCURRENT_CALCULATIONS` - Maximum allowed simultaneous calculations.
- `OIDC_BASE_URL` - URL where the application is deployed.
- `OIDC_REDIRECT_URL` - Redirect URL after successful Life Science auth.
- `OIDC_DISCOVERY_URL` - URL for fetching OIDC Life Science infomation (auth endpoint, ...).
- `OIDC_CLIENT_ID` - Client ID of the registered Life Science Application.
- `OIDC_CLIENT_SECRET` - Client secret of the registered Life Science Application.