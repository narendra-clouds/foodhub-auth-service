# FoodHub Backend — auth-service

This is the first microservice for the FoodHub project: **auth-service**.
It handles signup, login, and issuing JWT tokens for two roles:
`customer` and `owner` (restaurant owner).

## Run it locally

```bash
cd foodhub-backend
docker-compose up --build
```

This starts:
- `auth-db` — a Postgres 16 container (local stand-in for RDS)
- `auth-service` — the Flask API, on http://localhost:5001

The database tables are created automatically on first startup.

## Test it with curl

**1. Sign up a customer**
```bash
curl -X POST http://localhost:5001/signup \
  -H "Content-Type: application/json" \
  -d '{"name":"Narendra","email":"narendra@example.com","password":"secret123","role":"customer"}'
```
Response includes a `token` — save it for the next steps.

**2. Sign up a restaurant owner**
```bash
curl -X POST http://localhost:5001/signup \
  -H "Content-Type: application/json" \
  -d '{"name":"Cafe Owner","email":"owner@example.com","password":"secret123","role":"owner"}'
```

**3. Log in**
```bash
curl -X POST http://localhost:5001/login \
  -H "Content-Type: application/json" \
  -d '{"email":"narendra@example.com","password":"secret123"}'
```

**4. Call a protected route** (replace `<TOKEN>` with the token from signup/login)
```bash
curl http://localhost:5001/me \
  -H "Authorization: Bearer <TOKEN>"
```

**5. Call an owner-only route** (use the owner's token — a customer token gets a 403)
```bash
curl http://localhost:5001/owner-only-ping \
  -H "Authorization: Bearer <OWNER_TOKEN>"
```

## How the other services will use this

`restaurant-service`, `order-service`, and `notification-service` won't call
back into `auth-service` on every request. Instead, they'll each get the same
`JWT_SECRET` and verify the JWT themselves — that's the whole point of using
JWTs in a microservices setup: any service can independently confirm who's
calling and what role they have, without a network round-trip to auth-service
every time.

## Next steps

1. Wire the frontend's login/signup forms to call `/signup` and `/login`,
   store the returned token (e.g. in `localStorage`), and send it as
   `Authorization: Bearer <token>` on every future request.
2. Build `restaurant-service` next — it will use the *same* `JWT_SECRET` to
   verify owner-only routes (like "add a menu item") without asking
   auth-service to check.
3. Once `auth-service` + `restaurant-service` work together locally, that's
   your MVP checkpoint before adding `order-service`.
