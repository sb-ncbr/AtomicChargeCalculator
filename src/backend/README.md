# Atomic Charge Calculator III API

You can find additional information in [docs](../../docs/backend/).

## Docker Setup
Simplest way to run the application locally is via Docker. More information is available in the [Setup Using Docker section](../deployment/README.md#setup-using-docker) in the deployment documentation.

## Manual Setup

### Prerequisites
ACC III depends on the [ChargeFW2](https://github.com/sb-ncbr/ChargeFW2) python bindings. 

#### [Building ChargeFW2](https://github.com/sb-ncbr/ChargeFW2/tree/master?tab=readme-ov-file#installation)

*Note:* When running `cmake`, include `-DPYTHON_MODULE=ON` to generete python bindings:

```bash
$ cmake .. -DCMAKE_INSTALL_PREFIX=<WHERE-TO-INSTALL> -DPYTHON_MODULE=ON
```

#### [Using Python Bindings](https://github.com/sb-ncbr/ChargeFW2/blob/master/doc/ChargeFW2%20-%20tutorial.ipynb)

*Note:* `PYTHONPATH` environment variable is set in the [.env file](./app/.env). Overwrite it if you wish to install ChargeFW2 somewhere else.

#### Required environment variables
All required environment variables are located in the [.env file](./app/.env) except `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET` (required for Life Science auth, can be ignored for local setup). All used environment variables are described in [docs](../../docs/backend/README.md). How to obtain the abovementioned environment variables is also mentioned [here](../../docs/backend/life-science/README.md). 

### Installing dependencies
ACC III uses [uv](https://docs.astral.sh/uv/) for dependency management. Docker and CI use uv 0.12.19.

#### Install uv
```bash
$ curl -LsSf https://astral.sh/uv/0.12.19/install.sh | sh
```

#### Install project dependencies
uv creates a `.venv` in the backend directory and installs the versions recorded in `uv.lock`. Use Python 3.13 or newer, matching the Python version used to build your ChargeFW2 bindings. Docker uses Ubuntu's Python and does not download another interpreter.

```bash
$ uv sync --locked --no-python-downloads --python python3
```

### Startup
We firstly need to start the database. Easiest way is by using an official postgresql docker image. Connection string is located in the `.env` file.
```bash
$ docker run -it --rm -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:17-alpine
```

Following commands require being in the `app` directory:
```bash
$ cd app
```

After the database is ready, we need to run migrations:
```bash
$ uv run --no-sync alembic upgrade head
```

API can now be started just by running the main file:

```bash
$ uv run --no-sync gunicorn --workers 4 --worker-class uvicorn.workers.UvicornWorker main:web_app
```

API runs by default on `--bind 127.0.0.1:8000`. Documentation (Swagger) is available on `/docs`. Alternatively you can use Redoc available on `/redoc`.

### Startup script
You can also use the `startup.sh` script:

```bash
$ ./startup.sh
```
