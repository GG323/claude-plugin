# Shop API

Create, read, update, and delete items over HTTP. Items live in memory.

- `GET /health` returns `ok`.
- `GET /items`, `GET /items/{id}`, `POST /items`, `PUT /items/{id}`, `DELETE /items/{id}`.

Build the image with `docker build -t shop-api:1.0.0 .`; it listens on port 8080.
