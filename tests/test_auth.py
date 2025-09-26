# tests/test_auth.py
def test_register_login_me_refresh_logout(client):
    # register
    r = client.post("/api/v1/auth/register", json={"email": "t1@example.com", "password": "SuperSecret123"})
    assert r.status_code == 201
    data = r.get_json()
    assert "access_token" in data and "refresh_token" in data

    # login
    r = client.post("/api/v1/auth/login", json={"email": "t1@example.com", "password": "SuperSecret123"})
    assert r.status_code == 200
    toks = r.get_json()
    access = toks["access_token"]
    refresh = toks["refresh_token"]

    # me
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    me = r.get_json()
    assert me["email"] == "t1@example.com"
    assert me["role"] == "user"

    # refresh -> nouveau access
    r = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 200
    new_access = r.get_json()["access_token"]
    assert new_access and new_access != access

    # logout access -> doit être révoqué
    r = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200

    # /me avec l’ancien access -> 401 revoked
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 401
    err = r.get_json()["error"]["code"]
    assert err in ("token_revoked", "authorization_required")  # selon ordre des callbacks
